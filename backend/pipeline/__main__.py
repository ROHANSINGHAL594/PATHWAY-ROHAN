import os
from dotenv import load_dotenv
import pathway as pw
load_dotenv()
from lib.logger import custom_logger
from .agentic import build_agentic_graph
from .graph_reader import read_and_validate_graph
from pipeline.graph_builder import build_computational_graph, persist_table_to_postgres
from .agentic_setup import (
    setup_trigger_tables,
    setup_prompt_table,
    combine_answer_tables,
    persist_answers
)
from postgres_util import connection_string
from .metric_node import find_special_column_sources
from .mappings import trigger_rca
from .mappings.open_tel.prefix import is_special_column

# TODO: Fix setup tools deprecation warnings
# TODO: Fix numpy v1 vs v2 conflicts warnings 
# TODO: Fix beartype warnings

pw.set_license_key(os.environ["PATHWAY_LICENSE_KEY"])

class Prompt(pw.Schema):
    prompt: str


def main():
    """Main execution function for the pipeline."""
    try:
        custom_logger.critical("Pipeline starting")
        # Get flowchart file path
        flowchart_file = os.getenv("FLOWCHART_FILE", "flowchart.json")

        # Read and validate the graph
        graph = read_and_validate_graph(flowchart_file)

        # Build the computational graph
        node_outputs = build_computational_graph(
            graph["nodes"],
            graph["parsing_order"],
            graph["dependencies"]
        )
        custom_logger.info("Built workflow")
        graph["node_outputs"] = node_outputs
        for metric_node_idx in graph["metric_node_descriptions"].keys():
            graph["metric_node_descriptions"][metric_node_idx]["special_columns_source_indexes"] = {
                col: find_special_column_sources(metric_node_idx,col,graph) for col in node_outputs[metric_node_idx].column_names() if is_special_column(col) and 'trace_id' in col
            }
        trigger_rca_nodes = [ind for ind in range(len(graph["nodes"])) if graph["nodes"][ind].node_id == "trigger_rca"]

        for rca_node_idx in trigger_rca_nodes:
            rca_output_table = trigger_rca(node_outputs[graph["dependencies"][rca_node_idx][0]], graph["nodes"][rca_node_idx], graph)
            persist_table_to_postgres(rca_output_table, graph["nodes"][rca_node_idx], rca_node_idx)
        # Build agentic graph
        graph_name = graph.get("name", "")
        
        supervisor = build_agentic_graph(
            graph["agents"],
            graph_name,
            graph["nodes"],
            node_outputs
        )
        custom_logger.info("Built agents")


        # Setup trigger tables
        answer_tables = setup_trigger_tables(graph, node_outputs, supervisor)

        # Setup prompt input and answers
        prompts = pw.io.csv.read("prompts.csv", schema=Prompt, mode="streaming")
        prompt_answers = setup_prompt_table(prompts, supervisor)

        # Combine all answers
        all_answers = combine_answer_tables(prompt_answers, answer_tables)

        # Persist to database
        persist_answers(all_answers, connection_string)
        
        pw.run()
    except Exception as e:
        custom_logger.error(f"Error running pipeline: {e}")


if __name__ == "__main__":
    main()


