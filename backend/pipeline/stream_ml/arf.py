import numpy as np
from river import forest
from typing import List, Tuple, Optional, Dict, Any
import warnings
import time
import psutil
import os
from .model import BaseModel as StreamBaseModel, BaseModelConfig
from numpy.typing import NDArray
from abc import ABC, abstractmethod
from pydantic import BaseModel as PydanticBaseModel, Field
warnings.filterwarnings('ignore')


class ArfConfig(BaseModelConfig):
    n_models: int = Field(10, gt=0)
    max_depth: int = Field(15, gt=0)
    seed: Optional[int] = 42


class ArfRegressor(StreamBaseModel):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        horizon: int = 1,
        lookback: int = 5,
        n_models: int = 10,
        max_depth: int = 15,
        epochs: int = 1, # for compatibility
        batch_size: int = 32, # for compatibility
        seed: Optional[int] = 42
    ):
        self.horizon = horizon
        self.in_features = in_features
        self.out_features = out_features
        self.lookback = lookback
        self.n_models = n_models
        self.max_depth = max_depth
        self.seed = seed
        self.context_history = []
        self.models = []
        for _ in range(out_features):
            model = forest.ARFRegressor(
                n_models=self.n_models,
                max_depth=self.max_depth,
                seed=self.seed
            )
            self.models.append(model)
        
    def _predict_one( 
            self, 
            input: NDArray[np.float32]
            ) -> NDArray[np.float32]:
        """
        Args:
            input: [Context Size * In Features]
        Returns:
            predictions: [Horizon * Out Features]
        """
        predictions = []
        for w in range(self.horizon):
            prediction = []
            for j in range(self.out_features):
                x_dict = {}
                for i in range(self.lookback):
                    for k in range(self.in_features):
                        x_dict[f'feature_{k}_t-{self.lookback - i}'] = input[i, k]
                y_pred = self.models[j].predict_one(x_dict)
                prediction.append(y_pred)
            predictions.append(prediction)
            # Update input with prediction for next horizon step
            new_input = np.zeros((self.lookback, self.in_features), dtype=np.float32)
            new_input[:-1, :] = input[1:, :]
            new_input[-1, :] = prediction
            input = new_input
        return np.array(predictions, dtype=np.float32)
    
    def _train_one( 
            self, 
            input: NDArray[np.float32], 
            truth: NDArray[np.float32]
            ) -> float:
        """
        Args:
            input: [Context Size * In Features]
            truth: [Horizon * Out Features]
        Returns:
            mae: float
        """
        mae = 0.0
        for w in range(self.horizon):
            prediction = []
            for j in range(self.out_features):
                x_dict = {}
                for i in range(self.lookback):
                    for k in range(self.in_features):
                        x_dict[f'feature_{k}_t-{self.lookback - i}'] = input[i, k]
                y_pred = self.models[j].predict_one(x_dict)
                mae += abs(truth[w, j] - y_pred)
                self.models[j].learn_one(x_dict, truth[w, j])
                prediction.append(y_pred)
            # Update input with prediction for next horizon step
            new_input = np.zeros((self.lookback, self.in_features), dtype=np.float32)
            new_input[:-1, :] = input[1:, :]
            new_input[-1, :] = prediction
            input = new_input
        return mae / (self.horizon * self.out_features)

    def train(
        self,
        inputs: NDArray[np.float32],   
        truths:  NDArray[np.float32] 
    ) -> Tuple[float, float, float]:
        """
        Trains the ARF model on the given batch inputs.
        Returns:
            Avg RAM usage,
            Avg Latency,
            MAE
        """
        total_ram = 0.0
        total_latency = 0.0
        total_mae = 0.0
        batch_size = inputs.shape[0]

        for i in range(batch_size):
            start_time = time.time()
            ram_before = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # in MB

            mae = self._train_one(inputs[i], truths[i])

            ram_after = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # in MB
            latency = time.time() - start_time

            total_ram += (ram_before + ram_after) / 2
            total_latency += latency
            total_mae += mae

        avg_ram = total_ram / batch_size
        avg_latency = total_latency / batch_size
        avg_mae = total_mae / batch_size

        return avg_ram, avg_latency, avg_mae

    def predict(
        self,
        input: NDArray[np.float32],     # [In Features]
    ) -> Tuple[float, float, float, NDArray[np.float32]]:
        """
        Predicts the next horizon using stored context (past inputs + truths).
        Returns:
            RAM usage,
            Latency,
            Error (based on provided single truth),
            Predictions for full horizon: [Horizon * Out Features]
        """
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
        
        # Prepare input for prediction
        context_array = np.array(self.context_history, dtype=np.float32)
        start_time = time.time()
        ram_before = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # in MB
        predictions = self._predict_one(context_array)
        ram_after = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)  # in MB
        latency = time.time() - start_time  
        error = np.mean(np.abs(input - predictions[0]))  # Error based on first horizon step

        # Update context history
        self.context_history.append(input)
        if len(self.context_history) > self.lookback:
            self.context_history.pop(0)
        
        return (
            (ram_before + ram_after) / 2,
            latency,
            error,
            predictions  # [Horizon * Out Features]
        )