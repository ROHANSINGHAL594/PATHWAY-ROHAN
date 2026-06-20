# backend/lib/tables/ml.py
from typing import Literal, List, Optional
from pydantic import BaseModel, Field
from .base import TableNode


class _StreamingMLNode(TableNode):
    category: Literal["streaming_ml"] = "streaming_ml"
    channel_list: List[str] = Field(description="List of numerical input channels for the model")
    lookback: int = Field(10, description="Number of past time steps to consider")
    horizon: int = Field(1, description="Number of future time steps to predict")
    batch_size: int = Field(32, description="Number of samples per training batch")
    epochs: int = Field(1, description="Number of training epochs per training trigger")
    max_concurrent_training: int = Field(4, description="Maximum number of concurrent training sessions")


class ARFNode(_StreamingMLNode):
    node_id: Literal["arf_ml"] = "arf_ml"
    n_inputs: Literal[1] = 1
    
    n_models: int = Field(10, gt=0)
    max_depth: int = Field(15, gt=0)
    seed: Optional[int] = 42


class TiDENode(_StreamingMLNode):
    node_id: Literal["tide_ml"] = "tide_ml"
    n_inputs: Literal[1] = 1
    
    hidden_dim: int = Field(32, gt=0)
    optimizer: str = Field('adam')
    learning_rate: float = Field(0.001)
    clipnorm: Optional[float] = Field(None)


class MambaNode(_StreamingMLNode):
    node_id: Literal["mamba_ml"] = "mamba_ml"
    n_inputs: Literal[1] = 1
    
    d_model: int = Field(64, gt=0)
    num_layers: int = Field(2, gt=0)
    d_state: int = Field(16, gt=0)
    d_conv: int = Field(4, gt=0)
    expand: int = Field(2, gt=0)
    learning_rate: float = Field(0.001, gt=0)