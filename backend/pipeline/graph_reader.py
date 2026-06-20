import json
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from .validate import validate_nodes, validate_graph_topology
from lib.agents import Agent
from .types import Graph, Flowchart
from lib.utils import get_node_class_map
from lib.node import Node
from .metric_node import identify_metric_nodes_with_descriptions

def id2index(nodes: List[dict]) -> Dict[str, int]:
    """
    Convert node IDs to their indices in the node list.
    
    Args:
        nodes: List of node dictionaries with 'id' field
    
    Returns:
        Mapping of node id to node index
    
    Raises:
        KeyError: If a node is missing the 'id' field
    """
    mapping = {}
    for index, node in enumerate(nodes):
        if 'id' not in node:
            raise KeyError(f"Node at index {index} missing 'id' field")
        mapping[node['id']] = index
    return mapping


def read_flowchart_file(filepath: str) -> Flowchart:
    """
    Read and parse the flowchart JSON file.
    
    Args:
        filepath: Path to the flowchart JSON file
    
    Returns:
        Parsed flowchart data
    """
    with open(filepath, "r") as f:
        return json.load(f)


def parse_agents(data: Flowchart, id2index_map: Dict[str, int] = None) -> List[Agent]:
    """
    Parse agents from flowchart data, converting tool node IDs to indices.
    
    Args:
        data: Flowchart data
        id2index_map: Mapping of node id to node index (for tool mapping)
    
    Returns:
        List of Agent instances with tools mapped to indices
    """
    if data.get("agents", None) is None:
        return []

    agents = []
    for agent_data in data.get("agents", []):
        # Map tool node IDs to indices if id2index_map is provided
        if id2index_map and "tools" in agent_data and agent_data["tools"]:
            mapped_tools = []
            for tool in agent_data["tools"]:
                if isinstance(tool, str) and tool in id2index_map:
                    # Convert node ID string (e.g., "n5") to index
                    mapped_tools.append(id2index_map[tool])
                elif isinstance(tool, int):
                    # Already an index, keep as-is
                    mapped_tools.append(tool)
                else:
                    # Keep other tool identifiers (e.g., tool_map keys)
                    mapped_tools.append(tool)
            agent_data = {**agent_data, "tools": mapped_tools}
        
        agents.append(Agent(**agent_data))
    
    return agents


def read_and_validate_graph(filepath: str) -> Graph:
    """
    Read the flowchart file, validate it, and return the graph structure.
    
    Args:
        filepath: Path to the flowchart JSON file
    
    Returns:
        Validated graph with nodes, dependencies, and parsing order
    """
    # Read flowchart data
    data = read_flowchart_file(filepath)
    
    # Validate and parse nodes
    nodes = validate_nodes(data["nodes"])
    
    # Build id-to-index mapping
    id2index_map = id2index(data["nodes"])
    
    # Parse agents with tool ID to index mapping
    agents = parse_agents(data, id2index_map)
    
    # Validate graph topology and get parsing order and dependencies
    parsing_order, dependencies = validate_graph_topology(
        nodes, data["edges"], id2index_map
    )
    graph = {
        **data,
        "parsing_order": parsing_order,
        "nodes": nodes,
        "dependencies": dependencies,
        "agents": agents,
        "id2index_map": id2index_map
    }
    # Identify metric nodes and generate descriptions
    metric_node_descriptions = identify_metric_nodes_with_descriptions(graph)
    
    graph["metric_node_descriptions"] = metric_node_descriptions
    return graph

