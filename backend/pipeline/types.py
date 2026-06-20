from typing import List, Tuple, Dict, Optional, Any
from typing_extensions import TypedDict
from collections import defaultdict
from lib.node import Node
from lib.agents import Agent
import pathway as pw

class Flowchart(TypedDict):
    """Raw flowchart data from JSON file."""
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Node]]
    agents: Optional[List[Agent]]
    triggers: Optional[List[int]]
    name: Optional[str]

class MetricNodeDescription(TypedDict):
    pipeline_description: str
    pipeline_description_indexes_mapping: Dict[int,int]
    special_columns_source_indexes: Dict[str,int]
    description: str

class Graph(Flowchart):
    """Validated and processed graph structure."""
    parsing_order: List[int]
    dependencies: defaultdict[int, List[int]]
    nodes: List[Node]
    metric_node_descriptions: Dict[int,MetricNodeDescription]
    id2index_map: Dict[str,int]
    node_outputs: List[pw.Table]
    
