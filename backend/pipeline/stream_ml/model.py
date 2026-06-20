from abc import ABC, abstractmethod
from typing import Tuple, List, Any
from numpy.typing import NDArray
import numpy as np
from pydantic import Field, BaseModel as PydanticBaseModel

class BaseModelConfig(PydanticBaseModel):
    
    in_features: int = Field(..., gt=0)
    out_features: int = Field(..., gt=0)
    horizon: int = Field(..., gt=0)
    lookback: int = Field(..., gt=0)
    batch_size: int = Field(32, gt=0)
    epochs: int = Field(1)

class BaseModel(ABC):

    @abstractmethod
    def train(
        self,
        inputs: NDArray[np.float32],   # [Batch * Context Size * In Features] # We only get 1 batch which is the entire data provided for training over epochs
        truths:  NDArray[np.float32]    # [Batch * Horizon * Out Features]
    ) -> Tuple[float, float, float]:
        """
        Trains the model on the given batch inputs.
        Returns:
            Avg RAM usage,
            Avg Latency,
            MAE
        Notes:
            - Number of epochs is provided externally (e.g., flowchart.json).
            - Implementations should compute averages across batches.
        """
        pass

    @abstractmethod
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
        Notes:
            - Implementation may internally maintain history, errors, etc.
            - Should update internal context for next-step predictions.
        """
        pass
