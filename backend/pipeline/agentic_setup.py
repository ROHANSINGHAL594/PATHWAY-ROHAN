from typing import Dict, List, Any
import pathway as pw
from lib.node import Node
from .types import Graph


def setup_trigger_tables(
    graph: Graph,
    node_outputs: List[pw.Table],
    supervisor
) -> Dict[str, pw.Table]:
    """
    Set up trigger tables for the agentic graph.
    
    Args:
        graph: The validated graph structure
        node_outputs: List of node output tables
        supervisor: The supervisor agent
    
    Returns:
        Dictionary mapping trigger names to their answer tables
    """
    answer_tables: Dict[str, pw.Table] = {}
    
    if not hasattr(graph, "triggers") or not hasattr(graph, "agents"):
        return answer_tables
    
    for trigger in graph["triggers"]:
        trigger_node = node_outputs[trigger]
        node = graph["nodes"][trigger]
        
        # Validate trigger description
        if not hasattr(node, "trigger_description") or not node.trigger_description:
            raise ValueError(
                f"Trigger node at index {trigger} (node_id: '{node.node_id}') "
                "is missing trigger_description"
            )
        
        trigger_name = f"{node.node_id}_{trigger}"
        trigger_description = node.trigger_description
        
        # Register trigger with supervisor
        answer_tables[trigger_name] = supervisor["trigger"](
            trigger_name,
            trigger_description,
            trigger_node.schema,
            input_table=trigger_node
        ).successful
    
    return answer_tables


def setup_prompt_table(prompts_table: pw.Table, supervisor) -> pw.Table:
    """
    Set up the prompt answer table.
    
    Args:
        prompts_table: Input prompts table
        supervisor: The supervisor agent
    
    Returns:
        Prompt answers table
    """
    return supervisor["prompt"](input_table=prompts_table).successful


def combine_answer_tables(
    prompt_answers: pw.Table,
    trigger_tables: Dict[str, pw.Table]
) -> pw.Table:
    """
    Combine prompt answers with trigger answer tables.
    
    Args:
        prompt_answers: Table of prompt answers
        trigger_tables: Dictionary of trigger answer tables
    
    Returns:
        Combined answers table with row_id
    """
    if len(trigger_tables) > 0:
        all_answers = prompt_answers.concat_reindex(*trigger_tables.values())
    else:
        all_answers = prompt_answers
    
    return all_answers.with_columns(row_id=pw.this.id)


def persist_answers(all_answers: pw.Table, connection_string: dict[str, Any]) -> None:
    """
    Persist all answers to PostgreSQL.
    
    Args:
        all_answers: Combined answers table
        connection_string: PostgreSQL connection string
    """
    pw.io.postgres.write(
        all_answers,
        connection_string,
        "all_answers",
        output_table_type="snapshot",
        primary_key=[all_answers.row_id],
        init_mode="create_if_not_exists"
    )
