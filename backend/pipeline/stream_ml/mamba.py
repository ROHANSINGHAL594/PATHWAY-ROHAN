import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
import math
from .model import BaseModel as StreamBaseModel, BaseModelConfig
from numpy.typing import NDArray
import psutil
import os
import torch.nn.functional as F
from typing import Tuple, Any, List, Optional
from pydantic import BaseModel as PydanticBaseModel, Field


class MambaConfig(BaseModelConfig):
    d_model: int = Field(64, gt=0)
    num_layers: int = Field(2, gt=0)
    d_state: int = Field(16, gt=0)
    d_conv: int = Field(4, gt=0)
    expand: int = Field(2, gt=0)
    learning_rate: float = Field(0.001, gt=0)


class MambaBlock(nn.Module):
    def __init__(self, d_model, d_state=16, d_conv=4, expand=2):
        super().__init__()
        self.d_model = d_model
        self.d_inner = int(expand * d_model)
        self.dt_rank = math.ceil(d_model / d_state)
        self.in_proj = nn.Linear(d_model, self.d_inner * 2)
        self.conv1d = nn.Conv1d(self.d_inner, self.d_inner, d_conv, groups=self.d_inner, padding=d_conv - 1)
        self.x_proj = nn.Linear(self.d_inner, self.dt_rank + d_state * 2, bias=False)
        self.dt_proj = nn.Linear(self.dt_rank, self.d_inner, bias=True)
        A = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        self.log_A = nn.Parameter(torch.log(A))
        self.D = nn.Parameter(torch.ones(self.d_inner))
        self.out_proj = nn.Linear(self.d_inner, d_model)
        self.act = nn.SiLU()
        self.d_state = d_state

    def forward(self, x):
        batch, seq_len, _ = x.shape
        x_and_res = self.in_proj(x)
        (x_val, res) = x_and_res.split(split_size=[self.d_inner, self.d_inner], dim=-1)
        x_val = x_val.contiguous().transpose(1, 2)
        x_val = self.conv1d(x_val)[:, :, :seq_len].transpose(1, 2)
        x_val = self.act(x_val).contiguous()
        x_dbl = self.x_proj(x_val)
        (dt, B, C) = x_dbl.split(split_size=[self.dt_rank, self.d_state, self.d_state], dim=-1)
        dt, B, C = dt.contiguous(), B.contiguous(), C.contiguous()
        dt = F.softplus(self.dt_proj(dt))
        A = -torch.exp(self.log_A)
        y = []
        h = torch.zeros(batch, self.d_inner, self.d_state).to(x.device)
        for t in range(seq_len):
            dt_t = dt[:, t, :].unsqueeze(-1)
            A_t, B_t, C_t = A, B[:, t, :].unsqueeze(1), C[:, t, :].unsqueeze(1)
            x_t = x_val[:, t, :].unsqueeze(-1)
            h = torch.exp(dt_t * A_t) * h + dt_t * B_t * x_t
            y.append(torch.sum(h * C_t, dim=-1))
        y = torch.stack(y, dim=1)
        y = y + x_val * self.D
        return self.out_proj(y * self.act(res))


class MultivariateMamba(nn.Module):
    def __init__(self, input_dim, d_model=64, num_layers=2, output_dim=5, d_state=16, d_conv=4, expand=2):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        self.layers = nn.ModuleList([MambaBlock(d_model=d_model, d_state=d_state, d_conv=d_conv, expand=expand) for _ in range(num_layers)])
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, output_dim)

    def forward(self, x):
        x = self.embedding(x)
        for layer in self.layers: x = layer(x) + x
        return self.head(self.norm(x)[:, -1, :])
    

class MambaModel(StreamBaseModel):
    def __init__(
        self, 
        in_features: int, 
        out_features: int, 
        lookback : int = 20, 
        horizon: int = 1, 
        learning_rate: float = 0.001, 
        epochs: int = 1, 
        batch_size: int = 32,
        d_model: int = 64,
        num_layers: int = 2,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
    ):
        super().__init__()
        self.model = MultivariateMamba(input_dim=in_features, output_dim=out_features, d_model=d_model, num_layers=num_layers, d_state=d_state, d_conv=d_conv, expand=expand)
        self.in_features = in_features
        self.out_features = out_features
        self.lookback = lookback
        self.horizon = horizon
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.criterion = nn.MSELoss()
        self.context_history = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
    def train(
        self, 
        inputs: NDArray[np.float32],   # [Batch * Context Size * In Features]
        truths: NDArray[np.float32]   # [Batch * Horizon * Out Features]
    ) -> Tuple[float, float, float]:
        self.model.train()
        batch_size = inputs.shape[0]
        x_tensor = torch.tensor(inputs, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(truths, dtype=torch.float32).to(self.device)
        
        # Instance Normalization (RevIN style)
        # Calculate mean and std per instance over the time dimension (dim=1)
        # x_tensor: [Batch, Lookback, Features]
        seq_mean = torch.mean(x_tensor, dim=1, keepdim=True)
        seq_std = torch.std(x_tensor, dim=1, keepdim=True) + 1e-5
        
        x_norm = (x_tensor - seq_mean) / seq_std
        y_norm = (y_tensor - seq_mean) / seq_std
        
        mem_before = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
        start_time = time.time()

        with torch.no_grad():
            predictions = self.model(x_norm)
            # Check for NaNs in predictions
            if torch.isnan(predictions).any():
                 mae = float('nan')
            else:
                 pred_denorm = predictions * seq_std[:, 0, :] + seq_mean[:, 0, :] # predictions is [Batch, Features] (horizon step 1)
                 mae = torch.mean(torch.abs(pred_denorm - y_tensor[:, 0, :])).item()
            
            self.optimizer.zero_grad()
        for epoch in range(self.epochs):
            self.optimizer.zero_grad()
            current_input = x_norm.clone()  # [batch, lookback, input_dim]
            total_loss = torch.tensor(0.0).to(self.device)
            
            # Train autoregressively over the horizon
            for h in range(self.horizon):
                preds = self.model(current_input)  # [batch, output_dim]
                # Calculate loss against h-th horizon ground truth (normalized)
                loss = self.criterion(preds, y_norm[:, h, :])
                if torch.isnan(loss):
                     continue
                total_loss += loss
                pred_expanded = preds.unsqueeze(1)  # [batch, 1, output_dim]
                current_input = torch.cat([current_input[:, 1:, :], pred_expanded], dim=1)
                
            # Backpropagate accumulated loss
            total_loss = total_loss / self.horizon
            if not torch.isnan(total_loss) and total_loss.item() != 0.0:
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()

        end_time = time.time()
        mem_after = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
        
        avg_memory = (mem_before + mem_after) / 2
        latency = (end_time - start_time) / batch_size
        return avg_memory, latency, mae
    
    def predict(
        self, 
        input: NDArray[np.float32], 
    ) -> Tuple[float, float, float, NDArray[np.float32]]:
        self.model.eval()
        
        if len(self.context_history) < self.lookback:
            self.context_history.append(input)
            return (0.0, 0.0, float('inf'), np.zeros((self.horizon, self.out_features), dtype=np.float32))
        
        input_sequence = np.array(self.context_history[-self.lookback:], dtype=np.float32)
        x_tensor = torch.tensor(input_sequence, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        # Instance Normalization
        seq_mean = torch.mean(x_tensor, dim=1, keepdim=True)
        seq_std = torch.std(x_tensor, dim=1, keepdim=True) + 1e-5
        x_norm = (x_tensor - seq_mean) / seq_std
        
        mem_usage = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
        start_time = time.time()
        
        predictions_list = []
        current_input = x_norm.clone()

        with torch.no_grad():
            for _ in range(self.horizon):
                prediction_norm = self.model(current_input)
                predictions_list.append(prediction_norm)
                
                # Autoregressive step
                pred_expanded = prediction_norm.unsqueeze(1)
                current_input = torch.cat([current_input[:, 1:, :], pred_expanded], dim=1)

        latency = time.time() - start_time
        
        # Stack predictions along time dimension
        prediction_norm_all = torch.stack(predictions_list, dim=1) # [1, horizon, out_features]
        
        # Denormalize prediction
        prediction = prediction_norm_all * seq_std + seq_mean
        
        y_pred = prediction[0].cpu().numpy() # [horizon, out_features]
        
        if np.isnan(y_pred).any():
             error = float('nan')
        else:
             error = np.mean(np.abs(input - y_pred[0])) 

        self.context_history.append(input)
        if len(self.context_history) > self.lookback:
            self.context_history.pop(0)

        return mem_usage, latency, float(error), y_pred
