import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

from anthropic import Anthropic

# Resolve backend root so we can import from lib
BASE_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = BASE_DIR.parent
backend_root_str = str(BACKEND_ROOT)
if backend_root_str not in sys.path:
    sys.path.insert(0, backend_root_str)

from lib.utils import get_node_class_map
from contractparseragent.node_tool import get_node_pydantic_schema
from contractparseragent.agent_prompts import MACRO_PLAN_PROMPT_TEMPLATE, STEP1_PROMPT_TEMPLATE, STEP2_PROMPT_TEMPLATE

NODE_CATALOG_PATH = BASE_DIR / "node_catalog.json"

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

client = Anthropic(api_key=API_KEY)


def load_stringify_catalog() -> Dict[str, Any]:
    """Load the stringified node catalog for concise descriptions."""
    stringify_path = BASE_DIR / "stringify_catalog.json"
    with stringify_path.open("r", encoding="utf-8") as f:
        return json.load(f)
    """Load the stringified node catalog for concise descriptions."""
    stringify_path = BASE_DIR / "stringify_catalog.json"
    with stringify_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def stringify_pipeline(graph: Dict[str, Any]) -> str:
    """Convert current graph to human-readable stringified format.
    
    Args:
        graph: Dictionary with 'nodes' and 'edges' keys
        
    Returns:
        Multi-line string describing the pipeline in natural language
    """
    stringify_catalog = load_stringify_catalog()
    
    # Build a map of node_id -> stringify template
    stringify_map = {}
    for node_info in stringify_catalog.get("nodes", []):
        stringify_map[node_info["id"]] = node_info.get("stringify", "")
    
    lines = []
    lines.append("CURRENT PIPELINE STATE:")
    lines.append("-" * 60)
    
    # Create node id -> node mapping for easy access
    node_map = {node["id"]: node for node in graph.get("nodes", [])}
    
    # Build adjacency for topological understanding
    edges = graph.get("edges", [])
    
    for node in graph.get("nodes", []):
        node_id = node.get("id", "")
        node_type = node.get("node_id", "")
        props = node.get("data", {}).get("properties", {})
        
        # Get stringify template
        template = stringify_map.get(node_type, f"Node type '{node_type}'")
        
        # Replace placeholders in template with actual values
        stringified = template
        for key, value in props.items():
            placeholder = f"<{key}>"
            if placeholder in stringified:
                # Format value appropriately
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)
                stringified = stringified.replace(placeholder, value_str)
        
        # Find incoming edges to show data flow
        inputs = [e["source"] for e in edges if e["target"] == node_id]
        input_str = f" [from: {', '.join(inputs)}]" if inputs else " [source]"
        
        lines.append(f"{node_id}: {stringified}{input_str}")
    
    return "\n".join(lines)


def build_macro_plan(metric_name: str, metric_desc: str, extraction_plan: Dict[str, Any], filter_context: str = "") -> Dict[str, Any]:
    """Use the node stringified catalog to build a high-level macro plan.

    Returns a dict like {"steps": [...], "metric_description": "..."}.
    """
    stringify_catalog = load_stringify_catalog()

    catalog_summaries = []
    for node in stringify_catalog.get("nodes", []):
        # Only include non-input nodes (transformation, aggregation, output, action nodes)
        if node['category'] not in ['io']:
            catalog_summaries.append(f"- id={node['id']} | category={node['category']} | {node['stringify']}")

    # Use stringify_pipeline to show the current extraction plan in readable format
    extraction_block = stringify_pipeline(extraction_plan)
    catalog_block = "\n".join(catalog_summaries)

    prompt = MACRO_PLAN_PROMPT_TEMPLATE.format(
        metric_name=metric_name,
        metric_desc=metric_desc,
        filter_context=filter_context or "(no additional filters were provided)",
        extraction_block=extraction_block,
        catalog_block=catalog_block
    )

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

    try:
        data = json.loads(text)
        if "steps" not in data:
            data["steps"] = []
        return data
    except json.JSONDecodeError:
        return {"metric_description": metric_desc, "steps": []}


def build_next_node(current_graph: Dict[str, Any], macro_plan: List[str], step_index: int, filter_context: str = "", user_feedback: str = "") -> Dict[str, Any]:
    """Ask the LLM for the next node (or tiny subgraph) to add.

    Uses a two-step process:
    1. First, ask LLM which node_id to use
    2. Then provide exact Pydantic schema for that node and ask for properties

    Returns dict with keys:
        - "macro_plan": possibly revised list of steps
        - "next_node": single node dict
        - "next_edges": list of edge dicts (source/target by node ids or stream names)
    """
    stringify_catalog = load_stringify_catalog()

    # Build allowed nodes list from stringify catalog (excluding input connectors)
    allowed_nodes = []
    for node in stringify_catalog.get("nodes", []):
        # Skip input IO nodes, keep only transformation, aggregation, output, and action nodes
        if node['category'] not in ['io'] or node['id'] in ['open_tel_spans_input', 'open_tel_metrics_input', 'open_tel_logs_input']:
            allowed_nodes.append(node)
    
    # Build catalog descriptions using stringify format
    catalog_block_parts = []
    for node in allowed_nodes:
        catalog_block_parts.append(f"- {node['id']} ({node['category']}): {node['stringify']}")
    catalog_block = "\n".join(catalog_block_parts)

    plan_block = "\n".join([f"{i+1}. {s}" for i, s in enumerate(macro_plan)])
    current_step = macro_plan[step_index] if 0 <= step_index < len(macro_plan) else ""

    # Use stringify_pipeline instead of raw JSON for better context
    graph_stringified = stringify_pipeline(current_graph)

    # Before STEP 1, show the human-readable macro-plan step so it
    # appears while the LLM is being queried for this node.
    if current_step:
        print("\n[Metric Builder] Executing macro-plan step:")
        print(f"  → {current_step}")

    # STEP 1: Ask LLM which node type to use
    step1_prompt = STEP1_PROMPT_TEMPLATE.format(
        plan_block=plan_block,
        graph_stringified=graph_stringified,
        current_step=current_step,
        catalog_block=catalog_block,
        filter_context=filter_context or "(use the spans input if no filters exist)",
        user_feedback=user_feedback or "(no previous feedback)"
    )

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": step1_prompt}]
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

    try:
        step1_result = json.loads(text)
    except json.JSONDecodeError:
        return {
            "macro_plan": macro_plan,
            "next_node": None,
            "next_edges": []
        }

    selected_node_id = step1_result.get("selected_node_id")
    if not selected_node_id:
        return {
            "macro_plan": step1_result.get("macro_plan", macro_plan),
            "next_node": None,
            "next_edges": []
        }

    # STEP 2: Get exact Pydantic schema for the selected node
    pydantic_schema_info = get_node_pydantic_schema(selected_node_id)
    if "error" in pydantic_schema_info:
        print(f"Warning: Error getting schema for '{selected_node_id}': {pydantic_schema_info['error']}")
        return {
            "macro_plan": step1_result.get("macro_plan", macro_plan),
            "next_node": None,
            "next_edges": []
        }

    pydantic_schema = pydantic_schema_info["schema"]

    # STEP 2: Ask LLM to fill in the exact properties using Pydantic schema
    step2_prompt = STEP2_PROMPT_TEMPLATE.format(
        selected_node_id=selected_node_id,
        current_step=current_step,
        pydantic_schema=json.dumps(pydantic_schema, indent=2),
        new_node_internal_id=step1_result.get('new_node_internal_id', 'nX'),
        category=pydantic_schema.get('properties', {}).get('category', {}).get('const', 'table'),
        input_connections=step1_result.get('input_connections', [])
    )

    response2 = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": step2_prompt}]
    )
    text2 = response2.content[0].text.strip()
    if text2.startswith("```"):
        start = text2.find("{")
        end = text2.rfind("}") + 1
        if start != -1 and end > start:
            text2 = text2[start:end]

    try:
        step2_result = json.loads(text2)
    except json.JSONDecodeError:
        return {
            "macro_plan": step1_result.get("macro_plan", macro_plan),
            "next_node": None,
            "next_edges": []
        }

    # Build the final node
    category = pydantic_schema.get("properties", {}).get("category", {}).get("const", "table")
    next_node = {
        "id": step1_result.get("new_node_internal_id", "nX"),
        "node_id": selected_node_id,
        "category": category,
        "data": {
            "properties": step2_result.get("properties", {})
        }
    }

    # Build edges
    next_edges = []
    for source_id in step1_result.get("input_connections", []):
        next_edges.append({
            "source": source_id,
            "target": next_node["id"]
        })

    return {
        "macro_plan": step1_result.get("macro_plan", macro_plan),
        "next_node": next_node,
        "next_edges": next_edges
    }
