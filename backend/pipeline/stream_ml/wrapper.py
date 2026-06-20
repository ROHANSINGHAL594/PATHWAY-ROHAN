from .model import BaseModel, BaseModelConfig
from .arf import ArfRegressor
from .tide import TiDEModel
from .mamba import MambaModel
from numpy.typing import NDArray
from typing import Tuple, Dict, Any, List, Optional, Union
import numpy as np
import threading
import copy
from concurrent.futures import ThreadPoolExecutor, Future
import logging
from numpy.lib.stride_tricks import sliding_window_view

logger = logging.getLogger(__name__)


class ModelWrapper:
    MODEL_REGISTRY = {
        'arf': ArfRegressor,
        'tide': TiDEModel,
        'mamba': MambaModel,
    }
    
    def __init__(
        self,
        channel_list : List[str],
        model_name: str,
        config: BaseModelConfig,
        max_concurrent_training: int = 4,
    ):
        self.channel_list = channel_list
        self.model_name = model_name.lower()
        self.config = config
        self.max_concurrent_training = max_concurrent_training
        self.indices = None
        self.model = self._create_model()
        self.buffered_rows = [] # only 'channel list' columns
        
        # Async training infrastructure
        self._model_lock = threading.Lock()
        self._buffer_lock = threading.Lock()
        self._training_executor = ThreadPoolExecutor(max_workers=max_concurrent_training)
        self._active_training_count = 0
        self._training_count_lock = threading.Lock()
        self._pending_futures: List[Future] = []

    def _create_model(self) -> BaseModel:
        if self.model_name not in self.MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model '{self.model_name}'. "
                f"Available models: {list(self.MODEL_REGISTRY.keys())}"
            )
        
        model_class = self.MODEL_REGISTRY[self.model_name]
        return model_class(**self.config.model_dump())
    
    def _extract_streams(self, **kwargs) -> NDArray[np.float32]:
        arr = []
        for ch in self.channel_list:
            val = kwargs.get(ch)
            if val is None:
                 raise ValueError(f"Input data missing channel '{ch}'.")
            if not isinstance(val, (int, float, np.number)):
                raise ValueError(f"Value for channel '{ch}' must be numerical.")
            arr.append(float(val))
        
        return np.array(arr, dtype=np.float32)
    
    def _copy_model(self) -> BaseModel:
        with self._model_lock:
            return copy.deepcopy(self.model)
    
    def _prepare_training_data(self, buffered_rows: List[NDArray]) -> Tuple[NDArray, NDArray]:
        full_data = np.array(buffered_rows, dtype=np.float32)
        
        # Use sliding_window_view for efficient windowing
        n_samples = len(buffered_rows)
        lookback = self.config.lookback
        horizon = self.config.horizon
        if n_samples < lookback + horizon:
             return np.array([], dtype=np.float32), np.array([], dtype=np.float32)
        window_size = lookback + horizon
        
        # shape: (n_windows, n_channels, window_size) because axis=0 is windowed
        windows = sliding_window_view(full_data, window_shape=window_size, axis=0)
        # Transpose to (n_windows, window_size, n_channels)
        windows = np.moveaxis(windows, -1, 1)
        
        X_input = windows[:, :lookback, :]
        y_output = windows[:, lookback:, :]
        
        return X_input, y_output
    
    def _async_train_task(self, model_copy: BaseModel, buffered_rows: List[NDArray]) -> Tuple[float, float, float]:
        try:
            X_input, y_output = self._prepare_training_data(buffered_rows)
            ram_usage, latency, mae = model_copy.train(X_input, y_output)
            
            # Swap the trained model with the current model
            with self._model_lock:
                self.model = model_copy
            
            logger.info(f"Async training complete. RAM: {ram_usage:.2f}MB, Latency: {latency:.2f}s, MAE: {mae:.4f}")
            return ram_usage, latency, mae
        except Exception as e:
            logger.error(f"Async training failed: {e}")
            raise
        finally:
            with self._training_count_lock:
                self._active_training_count -= 1
    
    def _process_row(self, row_vals: Union[List[float], NDArray]) -> bool:
        with self._buffer_lock:
            self.buffered_rows.append(row_vals)
            
            required_len = self.config.batch_size + self.config.horizon + self.config.lookback - 1
            if len(self.buffered_rows) < required_len:
                return False

            # Check if we can spawn a new training session
            with self._training_count_lock:
                if self._active_training_count >= self.max_concurrent_training:
                    logger.warning(f"Max concurrent training limit ({self.max_concurrent_training}) reached. Dropping training batch.")
                    self.buffered_rows = self.buffered_rows[self.config.batch_size:]
                    return False
                self._active_training_count += 1
            
            # Copy model and buffer for async training
            model_copy = self._copy_model()
            buffered_rows_copy = list(self.buffered_rows)  # Shallow copy of the list
            self.buffered_rows = self.buffered_rows[self.config.batch_size:]
            
            # Submit async training task
            future = self._training_executor.submit(
                self._async_train_task,
                model_copy,
                buffered_rows_copy
            )
            self._pending_futures.append(future)
            
            # Cleanup completed futures
            self._pending_futures = [f for f in self._pending_futures if not f.done()]
            logger.info(f"Async training triggered. Active sessions: {self._active_training_count}")
            return True

    def check_train(self, **kwargs) -> bool: 
        row = self._extract_streams(**kwargs)
        return self._process_row(row.tolist())

    def check_train_fast(self, args: Tuple[Any, ...]) -> bool:
        if len(args) != len(self.channel_list):
             raise ValueError(f"Expected {len(self.channel_list)} channels, got {len(args)}")
        
        row_vals = []
        for i, val in enumerate(args):
            if not isinstance(val, (int, float, np.number)):
                 raise TypeError(f"Channel {self.channel_list[i]} expects number, got {type(val)}")
            row_vals.append(float(val))
            
        return self._process_row(row_vals)

    def invoke(self, **kwargs) -> Dict[str, Any]: 
        data_array = self._extract_streams(**kwargs)
        # Use lock to safely access model reference
        with self._model_lock:
            model = self.model
            
        # Predict without lock to allow parallelism
        ram_usage, latency, error, predictions = model.predict(data_array)
        
        # Convert numpy types to Python native types for JSON serialization
        kwargs['model_ram_usage'] = float(ram_usage) if isinstance(ram_usage, np.number) else ram_usage
        kwargs['model_latency'] = float(latency) if isinstance(latency, np.number) else latency
        kwargs['model_error'] = float(error) if isinstance(error, np.number) else error
        kwargs['model_prediction'] = predictions[-1, :].tolist()  # Return only the last horizon step predictions
        
        return kwargs

    def invoke_fast(self, args: Tuple[Any, ...]) -> Dict[str, Any]:
        # args are values in order of self.channel_list
        if len(args) != len(self.channel_list):
             raise ValueError(f"Expected {len(self.channel_list)} channels, got {len(args)}")
        
        # Validate types
        for i, val in enumerate(args):
            if not isinstance(val, (int, float, np.number)):
                 raise TypeError(f"Channel {self.channel_list[i]} expects number, got {type(val)}")

        data_array = np.array(args, dtype=np.float32)
        
        with self._model_lock:
            model = self.model
            
        ram_usage, latency, error, predictions = model.predict(data_array)
        
        return {
            "model_ram_usage": float(ram_usage) if isinstance(ram_usage, np.number) else ram_usage,
            "model_latency": float(latency) if isinstance(latency, np.number) else latency,
            "model_error": float(error) if isinstance(error, np.number) else error,
            "model_prediction": predictions[-1, :].tolist()
        }
    
    def shutdown(self, wait: bool = True) -> None: #unsused
        self._training_executor.shutdown(wait=wait)
        logger.info("Training executor shutdown complete.")
    
    def get_training_status(self) -> Dict[str, Any]: #unsused
        with self._training_count_lock:
            return {
                "active_training_sessions": self._active_training_count,
                "max_concurrent_training": self.max_concurrent_training,
                "pending_futures": len(self._pending_futures),
            }
            