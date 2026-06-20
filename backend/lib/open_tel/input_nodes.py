from ..node import Node
from ..types import RdKafkaSettings
from typing import Literal


class OpenTelInputNode(Node):
    category: Literal["open_tel"] = "open_tel"
    n_inputs: Literal[0] = 0
    rdkafka_settings: RdKafkaSettings

class OpenTelSpansNode(OpenTelInputNode):
    """Input node for span data from Kafka."""
    node_id: Literal["open_tel_spans_input"]
    topic: str = "otlp_spans"



class OpenTelMetricsNode(OpenTelInputNode):
    """Input node for metric data from Kafka."""
    node_id: Literal["open_tel_metrics_input"]
    topic: str = "otlp_metrics"


class OpenTelLogsNode(OpenTelInputNode):
    """Input node for log data from Kafka."""
    node_id: Literal["open_tel_logs_input"]
    topic: str = "otlp_logs"