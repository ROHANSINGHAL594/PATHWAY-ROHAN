from typing import List, Dict, Union
import pathway as pw
from lib.node import Node
from .mappings import mappings
from .mappings.helpers import get_col
from postgres_util import connection_string


def build_node_table(
    node: Node,
    node_index: int,
    dependencies: List[int],
    node_outputs: List[pw.Table],
    nodes: List[Node]
) -> pw.Table:
    """
    Build a single node's table output.
    
    Args:
        node: The node to build
        node_index: Index of the node in the graph
        dependencies: List of dependency node indices
        node_outputs: List of all node outputs
        nodes: List of all nodes
    
    Returns:
        The table output for this node, or None if node doesn't produce output
    """
    mapping = mappings[node.node_id]
    
    # Collect input tables from dependencies
    args = [node_outputs[input_node_ind] for input_node_ind in dependencies]
    
    # Execute node function
    table = mapping["node_fn"](args, node)
    
    return table


def persist_table_to_postgres(table: pw.Table, node: Node, node_index: int) -> None:
    """
    Persist a table to PostgreSQL.
    
    Args:
        table: The table to persist
        node: The node that produced the table
        node_index: Index of the node in the graph
    """
    if table is None or not isinstance(table,pw.Table):
        return
    
    # Get primary key columns
    cols = table.schema.primary_key_columns() or []
    primary_keys = [get_col(table, col) for col in cols]
    
    # Add row_id if no primary keys exist
    if len(cols) == 0:
        table = table.with_columns(__row_id=pw.this.id)
        primary_keys = [table.__row_id]
    
    # Write to PostgreSQL
    table_name = f"{node.node_id}__{node_index}"
    pw.io.postgres.write(
        table,
        connection_string,
        table_name,
        output_table_type="snapshot",
        primary_key=primary_keys,
        init_mode="create_if_not_exists"
    )


def build_computational_graph(
    nodes: List[Node],
    parsing_order: List[int],
    dependencies: Dict[int, List[int]]
) -> List[pw.Table]:
    """
    Build the entire Pathway computational graph in topological order.
    
    Args:
        nodes: List of all nodes in the graph
        parsing_order: Topologically sorted list of node indices
        dependencies: Mapping of node index to its dependency indices
    
    Returns:
        List of table outputs for each node
    """
    node_outputs: List[Union[pw.Table]] = [None] * len(nodes)
    
    for node_index in parsing_order:
        node = nodes[node_index]
        if node.node_id == "trigger_rca":
            continue
        node_deps = dependencies.get(node_index, [])
        
        # Build the node's table
        table = build_node_table(node, node_index, node_deps, node_outputs, nodes)
        
        if table is not None:
            node_outputs[node_index] = table
            
            # Persist to PostgreSQL
            persist_table_to_postgres(table, node, node_index)
    
    return node_outputs
