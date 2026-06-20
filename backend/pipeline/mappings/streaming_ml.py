import pathway as pw
import numpy as np
import asyncio
from typing import List, Union, Dict, Any, Optional
from .helpers import MappingValues
from lib.tables.stream_ml import ARFNode, TiDENode, MambaNode, _StreamingMLNode
from ..stream_ml.arf import ArfConfig
from ..stream_ml.wrapper import ModelWrapper
from ..stream_ml.tide import TiDEConfig
from ..stream_ml.mamba import MambaConfig


def _create_arf_config(node: ARFNode) -> ArfConfig:
    n_features = len(node.channel_list)
    return ArfConfig(
        in_features=n_features,
        out_features=n_features,
        horizon=node.horizon,
        lookback=node.lookback,
        batch_size=node.batch_size,
        epochs=node.epochs,
        # ARF-specific params
        n_models=node.n_models,
        max_depth=node.max_depth,
        seed=node.seed,
    )


def _create_tide_config(node: TiDENode) -> TiDEConfig:
    n_features = len(node.channel_list)
    return TiDEConfig(
        in_features=n_features,
        out_features=n_features,
        horizon=node.horizon,
        lookback=node.lookback,
        batch_size=node.batch_size,
        epochs=node.epochs,
        # TiDE-specific params
        hidden_dim=node.hidden_dim,
        optimizer=node.optimizer,
        learning_rate=node.learning_rate,
        clipnorm=node.clipnorm,
    )


def _create_mamba_config(node: MambaNode) -> MambaConfig:
    n_features = len(node.channel_list)
    return MambaConfig(
        in_features=n_features,
        out_features=n_features,
        horizon=node.horizon,
        lookback=node.lookback,
        batch_size=node.batch_size,
        epochs=node.epochs,
        # Mamba-specific params
        d_model=node.d_model,
        num_layers=node.num_layers,
        d_state=node.d_state,
        d_conv=node.d_conv,
        expand=node.expand,
        learning_rate=node.learning_rate,
    )


class StreamingMLOutputSchema(pw.Schema):
    prediction: List[float]
    latency_ms: float
    ram_mb: float
    error: Optional[float]


class StreamingMLTransformer(pw.AsyncTransformer, output_schema=StreamingMLOutputSchema):
    def __init__(self, model_wrapper: ModelWrapper, **kwargs):
        super().__init__(**kwargs)
        self.model_wrapper = model_wrapper
        self.channel_list = model_wrapper.channel_list

    async def invoke(self, **kwargs) -> Dict[str, Any]:
        # Extract args in order
        args = tuple(kwargs[col] for col in self.channel_list)
        result = await asyncio.to_thread(self.model_wrapper.invoke_fast, args)
        
        prediction = result.get("model_prediction", [])
        if hasattr(prediction, 'tolist'):
            prediction = prediction.tolist()
            
        error = result.get("model_error")
        if error is not None and (np.isinf(error) or np.isnan(error)):
            error = None
            
        latency = result.get("model_latency", 0)
        ram = result.get("model_ram_usage", 0)
        
        return {
            "prediction": prediction,
            "latency_ms": float(latency) * 1000 if latency else 0.0,
            "ram_mb": float(ram) if ram else 0.0,
            "error": float(error) if error is not None else None
        }


def _create_model_wrapper(
    node: _StreamingMLNode, 
    model_name: str
) -> ModelWrapper:
    
    if model_name == "arf":
        config = _create_arf_config(node)
    elif model_name == "tide":
        config = _create_tide_config(node)
    elif model_name == "mamba":
        config = _create_mamba_config(node)
    else:
        raise ValueError(f"Unknown model name: {model_name}")
    
    return ModelWrapper(
        channel_list=node.channel_list,
        model_name=model_name,
        config=config,
        max_concurrent_training=node.max_concurrent_training
    )


def _create_training_subscriber(model_wrapper: ModelWrapper):
    channel_list = model_wrapper.channel_list
    def on_change(key, row, time, is_addition):
        if is_addition:
            # Extract args in order
            args = tuple(row.get(col) for col in channel_list)
            model_wrapper.check_train_fast(args)
    
    return on_change


def _apply_streaming_ml(input_table: pw.Table, node: _StreamingMLNode, model_name: str) -> pw.Table:
    """
    1. Create model wrapper
    2. Subscribe to input table for training (calls check_train on each new row)
    3. Apply UDF for predictions
    4. Return table with model outputs
    """
    model_wrapper = _create_model_wrapper(node, model_name)
    training_callback = _create_training_subscriber(model_wrapper)
    pw.io.subscribe(input_table, on_change=training_callback)

     # Subscribe to input table for training (same as UDF approach)
    transformer = StreamingMLTransformer(model_wrapper, input_table=input_table, instance = 0)
    model_results = transformer.successful
    final_result = input_table.join(
        model_results, pw.left.id == pw.right.id
    ).select(
        *input_table,
        model_prediction=model_results.prediction,
        model_latency_ms=model_results.latency_ms,
        model_ram_mb=model_results.ram_mb,
        model_error=model_results.error,
    )
    
    return final_result


def arf_node_fn(inputs: List[pw.Table], node: ARFNode) -> pw.Table:
    return _apply_streaming_ml(inputs[0], node, "arf")


def tide_node_fn(inputs: List[pw.Table], node: TiDENode) -> pw.Table:
    return _apply_streaming_ml(inputs[0], node, "tide")


def mamba_node_fn(inputs: List[pw.Table], node: MambaNode) -> pw.Table:
    return _apply_streaming_ml(inputs[0], node, "mamba")


ml_mappings: dict[str, MappingValues] = {
    "arf_ml": {"node_fn": arf_node_fn},
    "tide_ml": {"node_fn": tide_node_fn},
    "mamba_ml": {"node_fn": mamba_node_fn},
}