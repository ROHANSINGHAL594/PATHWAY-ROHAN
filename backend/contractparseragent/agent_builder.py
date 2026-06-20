"""
Two-Phase Agentic Pipeline Builder
Phase 1: Input Builder (Interactive Chat) 
Phase 2: Metric Builder (Graph Generation)
"""

import os
import json
import sys
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Import layout utility for x/y assignment
from contractparseragent.layout_utils import apply_layout
from contractparseragent.node_tool import get_node_pydantic_schema
from anthropic import Anthropic
from dotenv import load_dotenv

# Path setup
BASE_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = BASE_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

from contractparseragent.agent_prompts import get_input_builder_prompt
from contractparseragent.graph_builder import build_macro_plan, build_next_node
from contractparseragent.ingestion import generate_metrics_from_pdf, gather_metrics_via_cli, load_metrics_from_file
from lib.utils import get_node_class_map

DEFAULT_NODE_SIZE = {"width": 200, "height": 261}
DEFAULT_VIEWPORT = {"x": 0, "y": 0, "zoom": 1}

class AgenticPipelineBuilder:
    def __init__(self, api_key: Optional[str] = None):
       
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable is required (or pass api_key)")
        self.client = Anthropic(api_key=self.api_key)
        self.model_name = "claude-sonnet-4-5-20250929"
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self.feedback_history: List[str] = []  # List of feedback strings from rejections

    def validate_output_structure(self, data: List[Dict[str, Any]]) -> bool:
        """
        Validate that the output matches the structure of sample_flowchart1.json.
        Expected: List containing one object with keys: _id, user, path, pipeline, etc.
        """
        if not isinstance(data, list) or len(data) != 1:
            print("Validation Error: Output must be a list of length 1.")
            return False
        
        item = data[0]
        required_keys = ["_id", "user", "path", "pipeline", "container_id", "host_port", "host_ip", "status"]
        for key in required_keys:
            if key not in item:
                print(f"Validation Error: Missing key '{key}' in output object.")
                return False
        
        if not isinstance(item["pipeline"], dict):
            print("Validation Error: 'pipeline' must be a dictionary.")
            return False
            
        if "nodes" not in item["pipeline"] or "edges" not in item["pipeline"]:
            print("Validation Error: 'pipeline' must contain 'nodes' and 'edges'.")
            return False
            
        if not isinstance(item["pipeline"]["nodes"], list):
            print("Validation Error: 'pipeline.nodes' must be a list.")
            return False
            
        if not isinstance(item["pipeline"]["edges"], list):
            print("Validation Error: 'pipeline.edges' must be a list.")
            return False
            
        return True

    def run_phase_1_input_builder(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 1: interactive chat to build input+filter flowchart for multiple SLA metrics.

        Returns a partial flowchart JSON with:
          - open_tel_spans_input node
          - multiple filter nodes (one per metric usually)
          - edges wiring spans input -> filters
        """
        print("\n" + "=" * 70)
        print("PHASE 1: INPUT BUILDER AGENT")
        print("=" * 70)
        print(f"Found {len(metrics_list)} metrics to configure.")
        for m in metrics_list:
            print(f"- {m.get('metric_name')}: {m.get('description')}")
        print("-" * 70)

        # Initialize conversation history for Claude
        conversation_history = []
        
        # Format metrics for the prompt
        metrics_text = json.dumps(metrics_list, indent=2)
        
        # Build prompt with Pydantic schemas injected
        input_builder_prompt = get_input_builder_prompt()
        
        # Initial message to kick off the multi-metric context
        initial_msg = f"""{input_builder_prompt}

        Here is the LIST OF METRICS I need to build filters for:
        {metrics_text}

        Let's start finding out the appropriate filters for these metrics."""
                
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            messages=[{"role": "user", "content": initial_msg}]
        )
        response_text = response.content[0].text
        print(f"\nAgent: {response_text}")
        
        # Add to conversation history
        conversation_history.append({"role": "user", "content": initial_msg})
        conversation_history.append({"role": "assistant", "content": response_text})

        flowchart: Optional[Dict[str, Any]] = None

        while True:
            text = response_text
            
            flowchart_data = None
            mapping_data = None
            
            # Extract all JSON blocks
            json_blocks = re.findall(r"```json(.*?)```", text, re.DOTALL)
            
            # Also try to parse the whole text if it's raw JSON
            if not json_blocks:
                try:
                    json.loads(text)
                    json_blocks = [text]
                except:
                    pass

            for block in json_blocks:
                try:
                    data = json.loads(block.strip())
                    if "nodes" in data and "edges" in data:
                        flowchart_data = data
                        if "metric_mapping" in data:
                            mapping_data = {"metric_mapping": data["metric_mapping"]}
                    elif "metric_mapping" in data:
                        mapping_data = data
                except Exception:
                    pass

            if flowchart_data:
                # Post-process: ensure open_tel_spans_input has required fields
                for node in flowchart_data.get("nodes", []):
                    if node.get("node_id") == "open_tel_spans_input":
                        props = node.get("data", {}).get("properties", {})
                        # Add default rdkafka_settings if missing
                        if "rdkafka_settings" not in props:
                            props["rdkafka_settings"] = {
                                "bootstrap_servers": "localhost:9092",
                                "group_id": "pathway-consumer",
                                "auto_offset_reset": "earliest"
                            }
                        # Add default topic if missing
                        if "topic" not in props:
                            props["topic"] = "otlp_spans"
                        node["data"]["properties"] = props
                
                if mapping_data and "metric_mapping" in mapping_data:
                    flowchart_data["metric_mapping"] = mapping_data["metric_mapping"]
                    
                flowchart = flowchart_data
                print("\nPhase 1 Complete: Input+Filter flowchart generated.")
                break

            # Get user input
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ('quit', 'exit'):
                print("Exiting...")
                sys.exit(0)

            conversation_history.append({"role": "user", "content": user_input})
            
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                messages=conversation_history
            )
            response_text = response.content[0].text
            print(f"Agent: {response_text}")
       
            conversation_history.append({"role": "assistant", "content": response_text})

        return flowchart

    def validate_flowchart_nodes(self, flowchart: Dict[str, Any]) -> bool:
        """Validate flowchart-style nodes (with node_id/category/data.properties) via Pydantic.

        Returns True if all nodes are valid, False otherwise.
        """
        node_map = get_node_class_map()

        for node in flowchart.get("nodes", []):
            node_id = node.get("node_id") or node.get("type")
            if not node_id:
                print(f"Validation Error: Node missing 'node_id': {node}")
                return False

            if node_id not in node_map:
                print(f"Validation Error: Unknown node_id '{node_id}'")
                return False

            node_class = node_map[node_id]
            props = node.get("data", {}).get("properties", {})
            validation_data = dict(props)

            # Ensure node_id and category are present
            validation_data.setdefault("node_id", node_id)
            if "category" not in validation_data and "category" in node_class.model_fields:
                field = node_class.model_fields["category"]
                if hasattr(field.annotation, "__args__"):
                    validation_data["category"] = field.annotation.__args__[0]

            try:
                node_class(**validation_data)
            except Exception as e:
                print(f"Validation Error for node '{node_id}' (id: {node.get('id')}): {e}")
                return False

        return True

    def run_phase_2_metric_builder(self, metric_name: str, metric_desc: str, extraction_plan: Dict[str, Any], filter_context: str = "") -> Dict[str, Any]:
        """Phase 2: build macro plan then iteratively construct calculation graph.

        This uses build_macro_plan + build_next_node and does
        user-in-the-loop confirmation for each incremental addition.
        """
        print("" + "=" * 70)
        print(f"PHASE 2: METRIC CALCULATION AGENT - {metric_name}")
        print("=" * 70)

        if filter_context:
            print("Filter context for this metric:")
            print(filter_context)

        print("Generating macro plan from current input+filter pipeline...")
        plan_data = build_macro_plan(metric_name, metric_desc, extraction_plan, filter_context)
        macro_plan = plan_data.get("steps", [])
        metric_desc_refined = plan_data.get("metric_description", metric_desc)

        print(f"Refined Metric Description: {metric_desc_refined}")
        print(f"Macro plan has {len(macro_plan)} steps:")
        for i, s in enumerate(macro_plan):
            print(f"  {i+1}. {s}")

        # Internal graph representation used only for the LLM conversation
        # Start with the extraction plan (input + filter)
        current_graph = {
            "nodes": list(extraction_plan.get("nodes", [])),
            "edges": list(extraction_plan.get("edges", []))
        }

        step_index = 0
        new_nodes = []
        new_edges = []
        retry_count = 0

        while step_index < len(macro_plan):
            print(f"Building node(s) for step {step_index + 1}: {macro_plan[step_index]}")

            # Save original macro_plan for potential retry
            original_macro_plan = macro_plan.copy() if isinstance(macro_plan, list) else macro_plan

            # Prepare user feedback
            user_feedback = ""
            if self.feedback_history:
                user_feedback = "\n".join(f"- {f}" for f in self.feedback_history)

            llm_result = build_next_node(current_graph, macro_plan, step_index, filter_context, user_feedback)
            macro_plan = llm_result.get("macro_plan", macro_plan)
            next_node = llm_result.get("next_node")
            next_edges_step = llm_result.get("next_edges", [])

            # Validate the returned node immediately
            if next_node:
                temp_flowchart = {"nodes": [next_node]}
                if not self.validate_flowchart_nodes(temp_flowchart):
                    print(" LLM returned invalid node. Treating as no node returned.")
                    next_node = None

            if not next_node:
                if retry_count < 1:
                    print(" LLM did not return a node for this step. Retrying once...")
                    retry_count += 1
                    # Use original macro_plan for retry to ensure identical conditions
                    macro_plan = original_macro_plan
                    continue
                else:
                    print(" LLM did not return a node for this step after retry. Aborting.")
                    break

            # Preview proposed change
            print("Proposed new nodes:")
            print(json.dumps(next_node, indent=2))
            print("Proposed new edges:")
            print(json.dumps(next_edges_step, indent=2))

            # Ask user for confirmation
            while True:
                choice = input("Accept these changes? [y/n/q]: ").strip().lower()
                if choice in ("y", "yes"):
                    # Apply to current_graph
                    current_graph["nodes"].append(next_node)
                    current_graph["edges"].extend(next_edges_step)
                    
                    # Keep track of new stuff to return
                    new_nodes.append(next_node)
                    new_edges.extend(next_edges_step)
                    
                    print(" Changes accepted.")
                    retry_count = 0  # Reset retry count on success
                    step_index += 1
                    break
                elif choice in ("n", "no"):
                    feedback = input("Why do you want to reject this node? (optional feedback): ").strip()
                    if feedback:
                        self.feedback_history.append(feedback)
                        print(f"Feedback recorded: {feedback}")
                    
                    print("Re-asking LLM to propose a different node for this step...")
                    
                    # Prepare user feedback
                    user_feedback = ""
                    if self.feedback_history:
                        user_feedback = "\n".join(f"- {f}" for f in self.feedback_history)
                    
                    llm_result = build_next_node(current_graph, original_macro_plan, step_index, filter_context, user_feedback)
                    macro_plan = llm_result.get("macro_plan", macro_plan)
                    next_node = llm_result.get("next_node")
                    next_edges_step = llm_result.get("next_edges", [])

                    # Validate the re-proposed node
                    if next_node:
                        temp_flowchart = {"nodes": [next_node]}
                        if not self.validate_flowchart_nodes(temp_flowchart):
                            print(" LLM returned invalid node on retry. Treating as no node returned.")
                            next_node = None

                    if not next_node:
                        if retry_count < 1:
                            print(" LLM did not return a node for this step. Retrying once...")
                            retry_count += 1
                            # Use original macro_plan for retry to ensure identical conditions
                            macro_plan = original_macro_plan
                            continue
                        else:
                            print(" LLM did not return a node for this step after retry. Aborting.")
                        break

                    print("New proposed nodes:")
                    print(json.dumps(next_node, indent=2))
                    print("New proposed edges:")
                    print(json.dumps(next_edges_step, indent=2))
                    retry_count = 0
                    continue
                elif choice in ("q", "quit", "exit"):
                    print("Exiting metric builder loop early by user request.")
                    step_index = len(macro_plan)
                    break
                else:
                    print("Please answer with 'y', 'n', or 'q'.")

        # Return only the NEW part of the graph for this metric
        return {"nodes": new_nodes, "edges": new_edges}

    def merge_and_save(self, phase1_flowchart: Dict[str, Any], calc_graph: Dict[str, Any], output_dir: str = "./generated_flowcharts") -> Dict[str, Any]:
        """Merge Phase1 (input+filters) and Phase2 (calculation graph) into a final flowchart, assigning x/y positions."""
        final_nodes: List[Dict[str, Any]] = []
        final_edges: List[Dict[str, Any]] = []
        id_map: Dict[str, str] = {}

        # Copy Phase1 nodes/edges as-is
        for node in phase1_flowchart.get("nodes", []):
            nid = node.get("id")
            if nid in id_map:
                new_id = f"{nid}_0"
                id_map[nid] = new_id
                node = dict(node)
                node["id"] = new_id
            else:
                id_map[nid] = nid
            final_nodes.append(dict(node))

        for edge in phase1_flowchart.get("edges", []):
            final_edges.append(dict(edge))

        # Determine next numeric suffix for new node ids if they follow nX pattern
        max_idx = 0
        for node in final_nodes:
            nid = node.get("id", "")
            if nid.startswith("n") and nid[1:].isdigit():
                max_idx = max(max_idx, int(nid[1:]))

        def next_node_id() -> str:
            nonlocal max_idx
            max_idx += 1
            return f"n{max_idx}"

        # Append Phase2 nodes with fresh ids
        for node in calc_graph.get("nodes", []):
            old_id = node.get("id") or ""
            new_id = next_node_id()
            id_map[old_id] = new_id
            new_node = dict(node)
            new_node["id"] = new_id
            final_nodes.append(new_node)

        # Append Phase2 edges, remapping ids
        for edge in calc_graph.get("edges", []):
            src = edge.get("source")
            tgt = edge.get("target")
            if src in id_map and tgt in id_map:
                new_edge = dict(edge)
                new_edge["source"] = id_map[src]
                new_edge["target"] = id_map[tgt]
                final_edges.append(new_edge)

        merged_flowchart = {"nodes": final_nodes, "edges": final_edges}
        apply_layout(merged_flowchart)

        normalized_nodes = [self._normalize_node_structure(node) for node in merged_flowchart["nodes"]]
        normalized_edges = self._normalize_edges(merged_flowchart["edges"])

        merged = {
            "nodes": normalized_nodes,
            "edges": normalized_edges,
            "agents": [],
            "viewport": dict(DEFAULT_VIEWPORT),
        }

        # Final validation
        if not self.validate_flowchart_nodes(merged):
            print("Final flowchart has validation errors; saving anyway for inspection.")

        # Wrap the output to match the format of tests/pipeline/sample_flowchart1.json
        try:
            from bson import ObjectId
            oid = str(ObjectId())
            user_id = str(ObjectId()) 
            path_id = str(ObjectId())
        except ImportError:
            import uuid
            oid = uuid.uuid4().hex[:24]
            user_id = uuid.uuid4().hex[:24]
            path_id = uuid.uuid4().hex[:24]

        full_doc = {
            "_id": { "$oid": oid },
            "user": user_id,
            "path": path_id,
            "pipeline": merged,
            "container_id": "",
            "host_port": "",
            "host_ip": "",
            "status": False
        }
        
        wrapped_output = [full_doc]

        if not self.validate_output_structure(wrapped_output):
            print("WARNING: Wrapped output structure validation failed!")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        out_file = output_path / "flowchart.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(wrapped_output, f, indent=2)
        print(f"Flowchart saved to {out_file}")

        return merged

    def _coerce_properties(self, raw_props: Any) -> Dict[str, Any]:
        if isinstance(raw_props, dict):
            return dict(raw_props)
        if isinstance(raw_props, list):
            props: Dict[str, Any] = {}
            for item in raw_props:
                if not isinstance(item, dict):
                    continue
                label = item.get("label")
                if label is None:
                    continue
                props[label] = item.get("value")
            return props
        return {}

    def _get_node_schema(self, node_id: Optional[str]) -> Dict[str, Any]:
        if not node_id:
            return {}
        cache_key = node_id.lower()
        if cache_key not in self._schema_cache:
            schema_info = get_node_pydantic_schema(node_id)
            self._schema_cache[cache_key] = schema_info.get("schema", {})
        return self._schema_cache[cache_key]

    def _apply_schema_defaults(self, props: Dict[str, Any], schema_props: Dict[str, Any], category: str, node_id: str) -> Dict[str, Any]:
        normalized = dict(props)
        normalized.setdefault("node_id", node_id)
        normalized.setdefault("category", category)
        n_inputs_const = schema_props.get("n_inputs", {}).get("const")
        if n_inputs_const is not None:
            normalized.setdefault("n_inputs", n_inputs_const)
        for field, field_schema in schema_props.items():
            if field in normalized:
                continue
            if "default" in field_schema:
                normalized[field] = field_schema["default"]
        normalized.setdefault("tool_description", "")
        normalized.setdefault("trigger_description", "")
        return normalized

    def _normalize_node_structure(self, node: Dict[str, Any]) -> Dict[str, Any]:
        node_id = node.get("node_id") or node.get("type") or node.get("id", "")
        schema = self._get_node_schema(node_id)
        schema_props = schema.get("properties", {})
        category = node.get("category") or schema_props.get("category", {}).get("const", "table")
        raw_props = node.get("data", {}).get("properties") or node.get("properties")
        normalized_props = self._coerce_properties(raw_props)
        normalized_props = self._apply_schema_defaults(normalized_props, schema_props, category, node_id)
        ui = node.get("data", {}).get("ui", {})
        label = ui.get("label") or normalized_props.get("name") or f"{node_id} Node"
        icon_url = ui.get("iconUrl", "")
        position = node.get("position") or {"x": 0, "y": 0}
        measured = node.get("measured") or dict(DEFAULT_NODE_SIZE)
        return {
            "id": node.get("id"),
            "type": node_id,
            "position": position,
            "node_id": node_id,
            "category": category,
            "schema": schema,
            "data": {
                "ui": {
                    "label": label,
                    "iconUrl": icon_url,
                },
                "properties": normalized_props,
            },
            "measured": measured,
            "selected": node.get("selected", False),
            "dragging": node.get("dragging", False),
        }

    def _normalize_edges(self, edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        target_handle_counters: Dict[str, int] = defaultdict(int)
        normalized: List[Dict[str, Any]] = []
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if not source or not target:
                continue
            source_handle = edge.get("sourceHandle") or "out"
            target_handle = edge.get("targetHandle")
            if not target_handle:
                idx = target_handle_counters[target]
                target_handle = f"in_{idx}"
                target_handle_counters[target] += 1
            normalized.append({
                "source": source,
                "sourceHandle": source_handle,
                "target": target,
                "targetHandle": target_handle,
                "animated": edge.get("animated", True),
                "id": edge.get("id") or f"xy-edge__{source}{source_handle}-{target}{target_handle}",
            })
        return normalized

def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def auto_assign_filters_to_metrics(metrics_list: List[Dict[str, Any]], filter_nodes: List[Dict[str, Any]], input_node_id: Optional[str], explicit_mapping: Optional[Dict[str, List[str]]] = None) -> Dict[str, List[str]]:
    """Automatically map each metric to one or more filters based on explicit mapping returned by Phase-I LLM or a text-similarity fallback."""

    if explicit_mapping:
        print("\nUsing explicit metric-to-filter mapping from Phase 1.")
        return explicit_mapping

    if not metrics_list:
        return {}

    # Precompute normalized descriptions for each filter node.
    filter_meta = []
    for node in filter_nodes:
        props = node.get("data", {}).get("properties", {})
        name = props.get("name") or ""
        filters = props.get("filters") or []
        filter_text_parts = [name]
        for f in filters:
            col = f.get("col") or f.get("column") or "col"
            op = f.get("op") or f.get("operator") or "=="
            val = f.get("value") or ""
            filter_text_parts.append(f"{col} {op} {val}")
        combined = " ".join(filter_text_parts)
        filter_meta.append((node, _normalize_text(combined)))

    metric_filter_map: Dict[str, List[str]] = {}

    for idx, metric in enumerate(metrics_list):
        metric_name = metric.get("metric_name") or f"metric_{idx}"
        norm_metric = _normalize_text(metric_name)

        matched_ids: List[str] = []
        if norm_metric:
            for node, normalized_desc in filter_meta:
                if norm_metric and norm_metric in normalized_desc:
                    matched_ids.append(node.get("id"))

        if not matched_ids:
            # Fallback to positional mapping
            if idx < len(filter_nodes):
                matched_ids = [filter_nodes[idx].get("id")]
            elif input_node_id:
                matched_ids = [input_node_id]
            else:
                matched_ids = []

        metric_filter_map[metric_name] = [fid for fid in matched_ids if fid]

    if metric_filter_map:
        print("\nMetric to filter assignment (auto-detected):")
        for metric_name, filters in metric_filter_map.items():
            friendly = ", ".join(filters) if filters else (input_node_id or "<none>")
            print(f"  - {metric_name}: {friendly}")

    return metric_filter_map


def summarize_filter_context(filter_ids: List[str], filter_index: Dict[str, Dict[str, Any]], input_node_id: Optional[str]) -> str:
    """Create a human-readable summary of the filter nodes for prompt context."""

    if filter_ids:
        lines = []
        for fid in filter_ids:
            node = filter_index.get(fid)
            if not node:
                lines.append(f"- {fid}: (missing filter definition)")
                continue
            props = node.get("data", {}).get("properties", {})
            name = props.get("name") or props.get("node_id") or "Filter"
            filters = props.get("filters") or []
            if not isinstance(filters, list):
                filters = []
            conds = []
            for condition in filters:
                col = condition.get("col") or condition.get("column") or "col"
                op = condition.get("op") or condition.get("operator") or "=="
                val = condition.get("value")
                conds.append(f"{col} {op} {val}")
            cond_str = "; ".join(conds) if conds else "(no explicit conditions provided)"
            lines.append(f"- {fid}: {name} — {cond_str}")
        return "\n".join(lines)

    if input_node_id:
        return f"- {input_node_id}: raw open_tel_spans_input (no additional filters)"

    return "(no filter context available)"

def resolve_metrics_source(args) -> Tuple[List[Dict[str, Any]], Path]:
    """Resolve SLA metrics from JSON, PDF extraction, or manual chat input."""

    output_dir = Path(args.metrics_output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    def _load_from_file(path_str: str) -> Tuple[List[Dict[str, Any]], Path]:
        path = Path(path_str).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Metrics file not found: {path}")
        metrics = load_metrics_from_file(path)
        return metrics, path

    if args.metrics_file:
        return _load_from_file(args.metrics_file)

    if args.pdf_path:
        metrics, saved_path = generate_metrics_from_pdf(
            args.pdf_path,
            output_dir,
            api_key=args.anthropic_api_key,
        )
        print(f"Extracted metrics saved to {saved_path}")
        return metrics, saved_path

    if getattr(args, "interactive", False):
        return gather_metrics_via_cli(output_dir)

    while True:
        print("\nChoose SLA metrics source:")
        print("  1) Existing JSON file")
        print("  2) Extract from SLA PDF (Claude)")
        print("  3) Enter manually via chat")
        choice = input("Selection [1/2/3]: ").strip()

        if choice == "1":
            path = input("Path to metrics JSON: ").strip()
            try:
                return _load_from_file(path)
            except Exception as exc:  # noqa: BLE001
                print(f"  Error loading file: {exc}")
                continue
        if choice == "2":
            pdf_path = input("Path to SLA PDF: ").strip()
            try:
                metrics, saved_path = generate_metrics_from_pdf(
                    pdf_path,
                    output_dir,
                    api_key=args.anthropic_api_key,
                )
                print(f"Extracted metrics saved to {saved_path}")
                return metrics, saved_path
            except Exception as exc:  # noqa: BLE001
                print(f"  Error extracting PDF: {exc}")
                continue
        if choice == "3":
            return gather_metrics_via_cli(output_dir)

        print("  Invalid selection. Please choose 1, 2, or 3.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-metric SLA pipeline builder")
    parser.add_argument("--metrics_file", help="Path to pre-defined SLA metrics JSON")
    parser.add_argument("--pdf_path", help="Path to an SLA PDF to auto-extract metrics from")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for SLA metrics via chat instead of supplying a file",
    )
    parser.add_argument(
        "--metrics_output_dir",
        default="./generated_flowcharts",
        help="Directory where generated metrics JSON files are stored",
    )
    parser.add_argument(
        "--anthropic_api_key",
        help="Override ANTHROPIC_API_KEY when extracting metrics from a PDF",
    )
    args = parser.parse_args()

    explicit_sources = sum(
        bool(flag) for flag in (args.metrics_file, args.pdf_path, args.interactive)
    )
    if explicit_sources > 1:
        parser.error("Specify only one of --metrics_file, --pdf_path, or --interactive")

    builder = AgenticPipelineBuilder()

    metrics_list, metrics_path = resolve_metrics_source(args)

    if not metrics_list:
        print("No SLA metrics were provided. Exiting.")
        sys.exit(1)

    print(f"Loaded {len(metrics_list)} SLA metrics from {metrics_path}")

    # Phase 1: Build Input + Filters for ALL metrics interactively
    phase1_graph = builder.run_phase_1_input_builder(metrics_list)
    
    if phase1_graph:
        # Identify the shared input node and collect filters for mapping.
        input_node_id: Optional[str] = None
        filter_nodes: List[Dict[str, Any]] = []
        for node in phase1_graph.get("nodes", []):
            node_type = node.get("node_id") or node.get("type")
            if node_type == "open_tel_spans_input":
                input_node_id = node.get("id")
            elif node_type == "filter":
                filter_nodes.append(node)

        def _node_sort_key(node: Dict[str, Any]) -> int:
            node_id = str(node.get("id", ""))
            if node_id.startswith("n") and node_id[1:].isdigit():
                return int(node_id[1:])
            return sys.maxsize

        filter_nodes.sort(key=_node_sort_key)
        filter_index = {node.get("id"): node for node in filter_nodes}
        
        explicit_mapping = phase1_graph.get("metric_mapping")
        metric_filter_map = auto_assign_filters_to_metrics(
            metrics_list, 
            filter_nodes, 
            input_node_id, 
            explicit_mapping=explicit_mapping
        )

        final_graph = {
            "nodes": list(phase1_graph.get("nodes", [])),
            "edges": list(phase1_graph.get("edges", []))
        }
        
        # Phase 2: Build logic for EACH metric one by one
        for idx, metric in enumerate(metrics_list):
            metric_name = metric.get("metric_name") or f"metric_{idx}"
            metric_desc = metric.get("description")
            metric_filter_ids = metric_filter_map.get(metric_name, [])
            filter_context_text = summarize_filter_context(metric_filter_ids, filter_index, input_node_id)
            
            # We need to identify which filter node belongs to this metric
            # This is tricky because the LLM generated them.
            # We will pass the ENTIRE phase1 graph as context, and let the LLM figure out which filter to use
            # based on the metric name/description.
            
            metric_graph_fragment = builder.run_phase_2_metric_builder(
                metric_name,
                metric_desc,
                phase1_graph,
                filter_context=filter_context_text
            )
            
            # Accumulate results
            # Note: merge_and_save handles ID remapping, but here we are doing it manually in a loop.
            # We should probably use a helper to merge fragments into the final_graph.
            
            # Simple merge for now (assuming IDs don't clash or are remapped inside run_phase_2 if we were careful, 
            # but run_phase_2 returns raw LLM IDs like "nX").
            # We need to remap them to be unique in final_graph.
            
            # Let's use the logic from merge_and_save but applied incrementally
            
            branch_sources = metric_filter_ids or ([input_node_id] if input_node_id else [])
            primary_filter_id = branch_sources[0] if branch_sources else None

            # Determine max ID in final_graph
            max_idx = 0
            for node in final_graph["nodes"]:
                nid = node.get("id", "")
                if nid.startswith("n") and nid[1:].isdigit():
                    max_idx = max(max_idx, int(nid[1:]))
            
            id_map: Dict[str, str] = {}
            new_node_ids: List[str] = []
            
            # Remap and add nodes
            for node in metric_graph_fragment.get("nodes", []):
                old_id = node.get("id")
                max_idx += 1
                new_id = f"n{max_idx}"
                id_map[old_id] = new_id
                node["id"] = new_id
                final_graph["nodes"].append(node)
                new_node_ids.append(new_id)
                
            # Remap and add edges
            connected_to_filter = False
            for edge in metric_graph_fragment.get("edges", []):
                # Source might be in id_map (new node) or in phase1_graph (existing node)
                src = edge.get("source")
                tgt = edge.get("target")

                new_edge = dict(edge)

                if src in id_map:
                    new_edge["source"] = id_map[src]
                elif primary_filter_id and src == input_node_id:
                    # Redirect any raw input references to the metric's chosen filter branch
                    new_edge["source"] = primary_filter_id

                if tgt in id_map:
                    new_edge["target"] = id_map[tgt]

                if (
                    primary_filter_id
                    and new_node_ids
                    and new_edge.get("source") == primary_filter_id
                    and new_edge.get("target") == new_node_ids[0]
                ):
                    connected_to_filter = True
                
                final_graph["edges"].append(new_edge)

            # Guarantee the metric branch starts from its filter node even if the LLM
            # attempted to connect directly to the root spans input.
            if primary_filter_id and new_node_ids and not connected_to_filter:
                final_graph["edges"].append({"source": primary_filter_id, "target": new_node_ids[0]})

        # Save final result
        output_path = Path("./generated_flowcharts")
        output_path.mkdir(parents=True, exist_ok=True)
        out_file = output_path / "flowchart.json"

        # Wrap the output to match the format of tests/pipeline/sample_flowchart1.json
        try:
            from bson import ObjectId
            oid = str(ObjectId())
            user_id = str(ObjectId()) 
            path_id = str(ObjectId())
        except ImportError:
            import uuid
            oid = uuid.uuid4().hex[:24]
            user_id = uuid.uuid4().hex[:24]
            path_id = uuid.uuid4().hex[:24]

        full_doc = {
            "_id": { "$oid": oid },
            "user": user_id,
            "path": path_id,
            "pipeline": final_graph,
            "container_id": "",
            "host_port": "",
            "host_ip": "",
            "status": False
        }
        
        wrapped_output = [full_doc]

        if not builder.validate_output_structure(wrapped_output):
             print("WARNING: Wrapped output structure validation failed!")

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(wrapped_output, f, indent=2)
        print(f"Final Multi-Metric Flowchart saved to {out_file}")
