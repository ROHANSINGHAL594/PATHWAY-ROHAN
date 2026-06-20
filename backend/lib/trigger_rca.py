from .node import Node
from typing import Literal

class TriggerRCANode(Node):
    node_id : Literal["trigger_rca"]
    category: Literal["agent"]
    n_inputs: Literal[1] = 1
    metric_description: str