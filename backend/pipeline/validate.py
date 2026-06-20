from typing import List, Dict, Any
from collections import defaultdict
from pydantic import ValidationError
from toposort import toposort_flatten
from lib.node import Node
from lib.io_nodes import ColumnType
from lib.utils import get_node_class_map
from lib.agents.rag import RAGNode
from pipeline.mappings.helpers import parse_table_schema


def validate_nodes(node_data_list: List[Dict[str, Any]]) -> List[Node]:
    """
    Validate an array of node objects using dynamically loaded Pydantic models.

    Each dict in node_data_list must have a 'node_id', 'category' key.
    The function looks up the corresponding class from node_class_map[node_id],
    instantiates it to trigger validation, which require the 'data'.'properties' key
    and returns the list of validated instances.

    Raises:
        KeyError: if node_id or category or data is not found in class map.
        ValidationError: if node JSON fails model validation.
    """
    node_class_map = get_node_class_map()
    validated_nodes = []

    for node_data in node_data_list:
        if "node_id" not in node_data:
            raise ValueError(f"Node missing 'node_id': {node_data}")

        if "category" not in node_data:
            raise ValueError(f"Node missing 'category': {node_data}")

        node_id = node_data["node_id"]
        if node_id not in node_class_map:
            raise KeyError(f"Unknown node_id '{node_id}'")

        node_class = node_class_map[node_id]

        if "data" not in node_data or "properties" not in node_data["data"] or len(node_data["data"]["properties"]) == 0:
            raise ValueError(f"Error parsing 'properties': {node_data}")

        parsed_node_data = {}
        parsed_node_data["node_id"] = node_id
        parsed_node_data["category"] = node_data["category"]
        for key, value in node_data["data"]["properties"].items():
            parsed_node_data[key] = value

        # Convert the input_schema received from frontend (as a list of ColumnType)
        # in to table_schema (dist of str) for assigning into the scheme parameter of nodes for pathway.
        if "input_schema" in parsed_node_data:
            parsed_node_data["table_schema"] = parse_table_schema(parsed_node_data["input_schema"])
        
        try:
            validated = node_class(**parsed_node_data)
            validated_nodes.append(validated)
        except ValidationError as e:
            raise ValueError(f"Validation failed for node_id='{node_id}': {e}") from e

    return validated_nodes


def is_input_node(node: Node) -> bool:
    """
    Check if a node is an input node by verifying it has a table_schema property.

    Args:
        node: A validated node instance (Pydantic model)

    Returns:
        bool: True if the node has table_schema property, False otherwise
    """
    return hasattr(node, 'table_schema')




def validate_graph_topology(
    nodes: List[Node],
    edges: List[Dict[str, Any]],
    node_id_to_index: Dict[str, int]
) -> tuple[List[int], defaultdict[int, list[int]]]:
    """
    Validate graph topology rules and return topological sort order and dependencies:
    1. Only input nodes (with table_schema) can be source nodes (no incoming edges)
    2. Each node must have the correct number of inputs based on n_inputs
    3. Alert nodes must have input nodes with trigger_description

    Args:
        nodes: List of validated node instances
        edges: List of edge dictionaries with 'source' and 'target' keys
        node_id_to_index: Mapping from node id to node index in the nodes list

    Returns:
        tuple: (parsing_order, dependencies) where parsing_order is topologically sorted list of node indices
               and dependencies is a mapping of target node index to list of source node indices

    Raises:
        ValueError: If validation rules are violated
    """
    # Build dependencies for toposort
    dependencies: Dict[int,List[str]] = {}
    for i,node in enumerate(nodes):
        dependencies[i] = []
    for edge in edges:
        if 'source' not in edge or 'target' not in edge:
            raise ValueError(f"Edge missing 'source' or 'target': {edge}")

        source_idx = node_id_to_index.get(edge['source'])
        target_idx = node_id_to_index.get(edge['target'])

        if source_idx is None:
            raise ValueError(f"Edge source '{edge['source']}' not found in nodes")
        if target_idx is None:
            raise ValueError(f"Edge target '{edge['target']}' not found in nodes")

        if nodes[source_idx].node_id == "rag_node":
            raise ValueError(f"The RAG node cannot be an input to another node")
        # Build dependencies for toposort (target depends on source)
        dependencies[target_idx].append(source_idx)


    # Rule 2: Validate that each node has the correct number of inputs
    for node_idx, dep_list in dependencies.items():
        node = nodes[node_idx]
        if len(dep_list) != node.n_inputs:
            raise ValueError(
                f"Node at index {node_idx} (node_id: '{node.node_id}') expects {node.n_inputs} input(s) "
                f"but has {len(dep_list)} incoming edge(s)"
            )

    # Get topological sort order
    parsing_order = [0] if len(nodes) == 1 else toposort_flatten(dependencies, nodes)



    # Rule: Validate alert nodes have input nodes with trigger_description
    for node_idx, node in enumerate(nodes):
        if node.node_id == "alert":
            dep_list = dependencies.get(node_idx, [])
            if len(dep_list) == 0:
                raise ValueError(f"Alert node at index {node_idx} has no dependencies")

            input_node = nodes[dep_list[0]]
            if not hasattr(input_node, "trigger_description"):
                raise ValueError(
                    f"Alert node at index {node_idx} requires input node at index {dep_list[0]} "
                    f"(node_id: '{input_node.node_id}') to have 'trigger_description' property"
                )

            # Set the trigger description on the alert node for later use
            node.input_trigger_description = input_node.trigger_description

    return parsing_order, dependencies
