from .logs import read_logs
from .metrics import read_metrics
from .spans import read_spans
from ..helpers import MappingValues

open_tel_mappings : dict[str, MappingValues] = {
    "open_tel_spans_input": {
        "node_fn": read_spans,
        "stringify": lambda node, inputs: "Input stream of open telemetry spans"
    },
    "open_tel_metrics_input":{
        "node_fn": read_metrics,
        "stringify": lambda node, inputs: "Input stream of open telemetry resource metrics"
    },
    "open_tel_logs_input": {
        "node_fn": read_logs,
        "stringify": lambda node, inputs: "Input stream of open telemetry logs"
    }
}