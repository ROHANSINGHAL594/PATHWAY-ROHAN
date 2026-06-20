import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import time
import psutil
import os
from typing import List, Optional, Tuple
from numpy.typing import NDArray
from .model import BaseModel as StreamBaseModel, BaseModelConfig
from pydantic import BaseModel as PydanticBaseModel, Field


class TiDEConfig(BaseModelConfig):
    hidden_dim: int = Field(32, gt=0)
    optimizer: str = Field('adam')
    learning_rate: float = Field(0.001)
    clipnorm: Optional[float] = Field(None)


class TiDENetwork(nn.Module):
    """
    Architecture:
    - Flattens multivariate input
    - Dense encoder layers
    - Dense decoder layers
    - Residual connection from input to output
    """
    
    def __init__(
        self,
        lookback: int,
        horizon: int,
        in_features: int,
        out_features: int,
        hidden_dim: int = 64
    ):
        super().__init__()
        self.lookback = lookback
        self.horizon = horizon
        self.in_features = in_features
        self.out_features = out_features
        self.hidden_dim = hidden_dim
        
        flat_input_dim = lookback * in_features
        flat_output_dim = horizon * out_features
        
        # Encoder layers
        self.encoder = nn.Sequential(
            nn.Linear(flat_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
        )
        
        self.decoder = nn.Linear(hidden_dim * 2, flat_output_dim)
        self.residual = nn.Linear(flat_input_dim, flat_output_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.shape[0]
        x_flat = x.view(batch_size, -1)
        encoded = self.encoder(x_flat)
        decoded = self.decoder(encoded)
        residual = self.residual(x_flat)
        out = decoded + residual
        out = out.view(batch_size, self.horizon, self.out_features)
        return out


class TiDEModel(StreamBaseModel):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        horizon: int = 1,
        lookback: int = 200,
        hidden_dim: int = 64,
        batch_size: int = 32,
        epochs: int = 1,
        optimizer: str = 'adam',
        learning_rate: float = 0.001,
        clipnorm: Optional[float] = None
    ):
        self.lookback = lookback
        self.horizon = horizon
        self.hidden_dim = hidden_dim
        self.in_features = in_features
        self.out_features = out_features
        self.batch_size = batch_size
        self.epochs = epochs
        self.optimizer_name = optimizer
        self.learning_rate = learning_rate
        self.clipnorm = clipnorm
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.model = TiDENetwork(
            lookback=lookback,
            horizon=horizon,
            in_features=in_features,
            out_features=out_features,
            hidden_dim=hidden_dim
        ).to(self.device)
        
        self.optimizer = self._get_optimizer()
        self.criterion = nn.MSELoss()
        self.context_history = []
        
    def _get_optimizer(self) -> optim.Optimizer:
        optimizer_map = {
            'adam': optim.Adam,
            'sgd': optim.SGD,
            'rmsprop': optim.RMSprop,
            'adagrad': optim.Adagrad,
            'adadelta': optim.Adadelta,
        }
        optimizer_class = optimizer_map.get(self.optimizer_name.lower(), optim.Adam)
        return optimizer_class(self.model.parameters(), lr=self.learning_rate)
    
    def _get_memory_usage(self) -> float:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 ** 2)
    
    def train(
        self,
        inputs: NDArray[np.float32],   # [Batch * Context Size * In Features]
        truths: NDArray[np.float32]    # [Batch * Horizon * Out Features]
    ) -> Tuple[float, float, float]:
        """
        Args:
            inputs: Input sequences of shape [batch, lookback, in_features]
            truths: Ground truth of shape [batch, horizon, out_features]
            
        Returns:
            Tuple of (Avg RAM usage in MB, Avg Latency in seconds, MAE)
        """
        self.model.train()
        batch_size = inputs.shape[0]
        
        # Convert to tensors
        x_tensor = torch.tensor(inputs, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(truths, dtype=torch.float32).to(self.device)
        
        # Track memory and time
        mem_before = self._get_memory_usage()
        start_time = time.time()
        
        # Training loop
        for epoch in range(self.epochs):
            # Process in mini-batches
            for i in range(0, batch_size, self.batch_size):
                batch_x = x_tensor[i:i + self.batch_size]
                batch_y = y_tensor[i:i + self.batch_size]
                
                self.optimizer.zero_grad()
                predictions = self.model(batch_x)
                loss = self.criterion(predictions, batch_y)
                loss.backward()
                
                # Gradient clipping if specified
                if self.clipnorm is not None:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clipnorm)
                
                self.optimizer.step()
        
        end_time = time.time()
        mem_after = self._get_memory_usage()
        
        # Calculate MAE on full batch
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(x_tensor)
            mae = torch.mean(torch.abs(y_tensor - predictions)).item()
        
        avg_memory = (mem_before + mem_after) / 2
        latency = (end_time - start_time) / batch_size
        
        return avg_memory, latency, mae
    
    def predict(
        self,
        input: NDArray[np.float32],     # [In Features]
    ) -> Tuple[float, float, float, NDArray[np.float32]]:
        """
        Args:
            input: Current input of shape [in_features]
            
        Returns:
            Tuple of (RAM usage in MB, Latency in seconds, Error, Predictions [Horizon, Out Features])
        """
        self.model.eval()
        
        # If we don't have enough context yet, return zeros
        if len(self.context_history) < self.lookback:
            # Update context history even during warmup
            self.context_history.append(input)
            return (
                0.0,
                0.0,
                float('inf'),
                np.zeros((self.horizon, self.out_features), dtype=np.float32)
            )
        
        # Prepare input sequence [1, lookback, num_features]
        input_sequence = np.array(self.context_history[-self.lookback:], dtype=np.float32)
        x_tensor = torch.tensor(input_sequence, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        mem_usage = self._get_memory_usage()
        start_time = time.time()
        
        with torch.no_grad():
            prediction = self.model(x_tensor)  # [1, horizon, out_features]
        
        latency = time.time() - start_time
        
        y_pred = prediction[0].cpu().numpy()  # [horizon, out_features]
        
        # Calculate error (for the first step if horizon > 1)
        error = float(np.mean(np.abs(input - y_pred[0])))

        # Update context history
        self.context_history.append(input)
        if len(self.context_history) > self.lookback:
            self.context_history.pop(0)
        
        return mem_usage, latency, error, y_pred