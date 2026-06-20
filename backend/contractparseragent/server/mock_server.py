"""
Server that simulates the agentic pipeline for local testing.

This implementation mirrors the behavior and WebSocket protocol of
`server.py`, but it does not call any external LLMs. Instead, it
returns a fixed, known-good flowchart equivalent to
`downtime_flowchart.json` as the final result of the session.
"""

import json
import os
import sys
import uuid
import shutil
import re
import asyncio
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from contractparseragent.layout_utils import apply_layout
from contractparseragent.agent_builder import (
    auto_assign_filters_to_metrics,
    summarize_filter_context,
)

app = FastAPI()

# Random latency range (in seconds) for simulating agent thinking
MIN_LATENCY = 0.5
MAX_LATENCY = 2.0

async def random_delay():
    """Add a random delay to simulate agent processing time."""
    delay = random.uniform(MIN_LATENCY, MAX_LATENCY)
    await asyncio.sleep(delay)
    return delay

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Default output directory
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "generated_flowcharts"
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Temporary PDF directory
TEMP_PDF_DIR = Path(__file__).parent / "temp_pdfs"
TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Hardcoded agent outputs for each node (keyed by node id)
NODE_AGENT_OUTPUTS: Dict[str, str] = {
    "n1": """**OpenTelSpansNode (n1)** - Span Data Input

I'm configuring the OpenTelemetry Spans input node to collect span data from Kafka.

**Configuration:**
- Bootstrap servers: `34.93.25.61:9092`
- Consumer group: `test_group_spans`
- Topic: `otlp_spans`

This node will ingest all OpenTelemetry span data for processing in the pipeline.""",

    "n2": """**FilterNode (n2)** - Checkout Request Filter

Now I'm adding a filter node to isolate checkout-related spans.

**Filter Configuration:**
- Column: `name`
- Operator: `==`
- Value: `POST /api/checkout`

This filter will select only the spans related to the checkout API endpoint for further analysis.""",

    "n3": """**WindowByNode (n3)** - Tumbling Window Aggregation

Adding a temporal windowing node to aggregate checkout failures.

**Window Configuration:**
- Type: Tumbling window
- Duration: 30 seconds
- Time column: `start_time_unix_nano`

**Aggregation:**
- Counting `_open_tel_trace_id` → `n_failed_checkouts`

This creates 30-second windows to count the number of failed checkout requests.""",

    "n4": """**FilterNode (n4)** - Threshold Alert Filter

Adding a threshold filter to detect high failure rates.

**Filter Configuration:**
- Column: `n_failed_checkouts`
- Operator: `>=`
- Value: `5`

This filter triggers when 5 or more checkout failures occur within a 30-second window.""",

    "n5": """**TriggerRCANode (n5)** - Root Cause Analysis Trigger

Configuring the RCA trigger node to alert on threshold breaches.

**Configuration:**
- Metric description: "Number of failed checkout requests in a window of 30 seconds must be < 5"

When the threshold is exceeded, this node will trigger root cause analysis and alert the user.""",

    "n6": """**OpenTelLogsNode (n6)** - Log Data Input

Adding a separate logs input node for analysis support.

**Configuration:**
- Bootstrap servers: `34.93.25.61:9092`
- Consumer group: `test_group_logs`
- Topic: `otlp_logs`

This node collects log data that can be used for deeper RCA analysis. It's independent of the main pipeline flow.""",
}

# New workflow pipeline JSON (the checkout monitoring pipeline)
NEW_WORKFLOW_PIPELINE: Dict[str, Any] = {
    "nodes": [
        {
            "id": "n1",
            "schema": {
                "$defs": {
                    "RdKafkaSettings": {
                        "description": "TypedDict for rdkafka configuration settings.",
                        "properties": {
                            "bootstrap_servers": {"title": "Bootstrap Servers", "type": "string"},
                            "security_protocol": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Security Protocol"},
                            "sasl_mechanism": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Mechanism"},
                            "sasl_username": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Username"},
                            "sasl_password": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Password"},
                            "group_id": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Group Id"},
                            "auto_offset_reset": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Auto Offset Reset"}
                        },
                        "title": "RdKafkaSettings",
                        "type": "object"
                    }
                },
                "description": "Input node for span data from Kafka.",
                "properties": {
                    "category": {"const": "open_tel", "default": "open_tel", "title": "Category", "type": "string"},
                    "node_id": {"const": "open_tel_spans_input", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "n_inputs": {"const": 0, "default": 0, "title": "N Inputs", "type": "integer"},
                    "rdkafka_settings": {"$ref": "#/$defs/RdKafkaSettings"},
                    "topic": {"default": "otlp_spans", "title": "Topic", "type": "string"}
                },
                "required": ["node_id", "rdkafka_settings"],
                "title": "OpenTelSpansNode",
                "type": "object"
            },
            "type": "open_tel_spans_input",
            "position": {"x": -342.96, "y": 194.50},
            "node_id": "open_tel_spans_input",
            "category": "open_tel",
            "data": {
                "ui": {"label": "OpenTelSpansNode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Collect open telemetry span nodes",
                    "trigger_description": "",
                    "rdkafka_settings": {
                        "bootstrap_servers": "34.93.25.61:9092",
                        "group_id": "test_group_spans"
                    },
                    "topic": "otlp_spans"
                }
            },
            "measured": {"width": 292, "height": 231},
            "selected": False,
            "dragging": False
        },
        {
            "id": "n2",
            "schema": {
                "$defs": {
                    "Filter": {
                        "properties": {
                            "col": {"title": "Col", "type": "string"},
                            "op": {"enum": ["==", "<", "<=", ">=", ">", "!=", "startswith", "endswith", "find"], "title": "Op", "type": "string"},
                            "value": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "string"}], "title": "Value"}
                        },
                        "required": ["col", "op", "value"],
                        "title": "Filter",
                        "type": "object"
                    }
                },
                "properties": {
                    "category": {"const": "table", "title": "Category", "type": "string"},
                    "node_id": {"const": "filter", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "filters": {"items": {"$ref": "#/$defs/Filter"}, "title": "Filters", "type": "array"},
                    "n_inputs": {"const": 1, "default": 1, "title": "N Inputs", "type": "integer"}
                },
                "required": ["category", "node_id", "filters"],
                "title": "FilterNode",
                "type": "object"
            },
            "type": "filter",
            "position": {"x": 136.21, "y": 679.37},
            "node_id": "filter",
            "category": "table",
            "data": {
                "ui": {"label": "FilterNode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Filter out the request on the api/checkout end point",
                    "trigger_description": "",
                    "filters": [{"col": "name", "op": "==", "value": "POST /api/checkout"}]
                }
            },
            "measured": {"width": 350, "height": 231},
            "selected": False,
            "dragging": False
        },
        {
            "id": "n3",
            "schema": {
                "$defs": {
                    "CommonBehaviour": {
                        "properties": {
                            "delay": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"format": "duration", "type": "string"}, {"type": "null"}], "title": "Delay"},
                            "cutoff": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"format": "duration", "type": "string"}, {"type": "null"}], "title": "Cutoff"},
                            "keep_results": {"title": "Keep Results", "type": "boolean"}
                        },
                        "required": ["delay", "cutoff", "keep_results"],
                        "title": "CommonBehaviour",
                        "type": "object"
                    },
                    "ReducerDict": {
                        "properties": {
                            "col": {"title": "Col", "type": "string"},
                            "reducer": {"enum": ["any", "argmax", "argmin", "avg", "count", "count_distinct", "count_distinct_approximate", "earliest", "latest", "max", "min", "ndarray", "sorted_tuple", "stateful_many", "stateful_single", "sum", "tuple", "unique", "p90", "p95", "p99"], "title": "Reducer", "type": "string"},
                            "new_col": {"title": "New Col", "type": "string"}
                        },
                        "required": ["col", "reducer", "new_col"],
                        "title": "ReducerDict",
                        "type": "object"
                    },
                    "Tumbling": {
                        "properties": {
                            "duration": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"format": "duration", "type": "string"}, {"type": "null"}], "title": "Duration"},
                            "origin": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Origin"},
                            "window_type": {"const": "tumbling", "title": "Window Type", "type": "string"}
                        },
                        "required": ["duration", "origin", "window_type"],
                        "title": "Tumbling",
                        "type": "object"
                    }
                },
                "properties": {
                    "category": {"const": "temporal", "title": "Category", "type": "string"},
                    "node_id": {"const": "window_by", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "n_inputs": {"const": 1, "default": 1, "title": "N Inputs", "type": "integer"},
                    "time_col": {"title": "Time Col", "type": "string"},
                    "instance_col": {"title": "Instance Col", "type": "string"},
                    "window": {"title": "Window"},
                    "behaviour": {"$ref": "#/$defs/CommonBehaviour"},
                    "reducers": {"items": {"$ref": "#/$defs/ReducerDict"}, "title": "Reducers", "type": "array"}
                },
                "required": ["category", "node_id", "time_col", "window", "reducers"],
                "title": "WindowByNode",
                "type": "object"
            },
            "type": "window_by",
            "position": {"x": 561.86, "y": 184.27},
            "node_id": "window_by",
            "category": "temporal",
            "data": {
                "ui": {"label": "WindowByNode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Divide a continuous data stream into fixed-size, non-overlapping, contiguous chunks (windows) of time",
                    "trigger_description": "",
                    "time_col": "start_time_unix_nano",
                    "window": {"duration": {"$numberLong": "30000000000"}, "origin": 0, "window_type": "tumbling"},
                    "reducers": [{"col": "_open_tel_trace_id", "reducer": "count", "new_col": "n_failed_checkouts"}]
                }
            },
            "measured": {"width": 350, "height": 233},
            "selected": False,
            "dragging": False
        },
        {
            "id": "n4",
            "schema": {
                "$defs": {
                    "Filter": {
                        "properties": {
                            "col": {"title": "Col", "type": "string"},
                            "op": {"enum": ["==", "<", "<=", ">=", ">", "!=", "startswith", "endswith", "find"], "title": "Op", "type": "string"},
                            "value": {"anyOf": [{"type": "integer"}, {"type": "number"}, {"type": "string"}], "title": "Value"}
                        },
                        "required": ["col", "op", "value"],
                        "title": "Filter",
                        "type": "object"
                    }
                },
                "properties": {
                    "category": {"const": "table", "title": "Category", "type": "string"},
                    "node_id": {"const": "filter", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "filters": {"items": {"$ref": "#/$defs/Filter"}, "title": "Filters", "type": "array"},
                    "n_inputs": {"const": 1, "default": 1, "title": "N Inputs", "type": "integer"}
                },
                "required": ["category", "node_id", "filters"],
                "title": "FilterNode",
                "type": "object"
            },
            "type": "filter",
            "position": {"x": 1046.77, "y": 745.42},
            "node_id": "filter",
            "category": "table",
            "data": {
                "ui": {"label": "FilterNode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Check if the n_failed_checkouts are greater then a threshold of 5",
                    "trigger_description": "",
                    "filters": [{"col": "n_failed_checkouts", "op": ">=", "value": 5}]
                }
            },
            "measured": {"width": 350, "height": 231},
            "selected": False,
            "dragging": False
        },
        {
            "id": "n5",
            "schema": {
                "properties": {
                    "category": {"const": "agent", "title": "Category", "type": "string"},
                    "node_id": {"const": "trigger_rca", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "n_inputs": {"const": 1, "default": 1, "title": "N Inputs", "type": "integer"},
                    "metric_description": {"title": "Metric Description", "type": "string"}
                },
                "required": ["category", "node_id", "metric_description"],
                "title": "TriggerRCANode",
                "type": "object"
            },
            "type": "trigger_rca",
            "position": {"x": 1601.83, "y": 421.13},
            "node_id": "trigger_rca",
            "category": "agent",
            "data": {
                "ui": {"label": "TriggerRCANode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Alert user then such a event is found.",
                    "trigger_description": "",
                    "metric_description": "Number of failed checkout requests in a window of 30 seconds must be < 5"
                }
            },
            "measured": {"width": 350, "height": 231},
            "selected": False,
            "dragging": False
        },
        {
            "id": "n6",
            "schema": {
                "$defs": {
                    "RdKafkaSettings": {
                        "description": "TypedDict for rdkafka configuration settings.",
                        "properties": {
                            "bootstrap_servers": {"title": "Bootstrap Servers", "type": "string"},
                            "security_protocol": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Security Protocol"},
                            "sasl_mechanism": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Mechanism"},
                            "sasl_username": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Username"},
                            "sasl_password": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Sasl Password"},
                            "group_id": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Group Id"},
                            "auto_offset_reset": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Auto Offset Reset"}
                        },
                        "title": "RdKafkaSettings",
                        "type": "object"
                    }
                },
                "description": "Input node for log data from Kafka.",
                "properties": {
                    "category": {"const": "open_tel", "default": "open_tel", "title": "Category", "type": "string"},
                    "node_id": {"const": "open_tel_logs_input", "title": "Node Id", "type": "string"},
                    "tool_description": {"default": "", "title": "Tool Description", "type": "string"},
                    "trigger_description": {"default": "", "title": "Trigger Description", "type": "string"},
                    "n_inputs": {"const": 0, "default": 0, "title": "N Inputs", "type": "integer"},
                    "rdkafka_settings": {"$ref": "#/$defs/RdKafkaSettings"},
                    "topic": {"default": "otlp_logs", "title": "Topic", "type": "string"}
                },
                "required": ["node_id", "rdkafka_settings"],
                "title": "OpenTelLogsNode",
                "type": "object"
            },
            "type": "open_tel_logs_input",
            "position": {"x": -403.95, "y": 600.77},
            "node_id": "open_tel_logs_input",
            "category": "open_tel",
            "data": {
                "ui": {"label": "OpenTelLogsNode Node", "iconUrl": ""},
                "properties": {
                    "tool_description": "Collect the logs for analysis, we do not need to connect it to any node",
                    "trigger_description": "",
                    "rdkafka_settings": {
                        "bootstrap_servers": "34.93.25.61:9092",
                        "group_id": "test_group_logs"
                    },
                    "topic": "otlp_logs"
                }
            },
            "measured": {"width": 350, "height": 231},
            "selected": False,
            "dragging": False
        }
    ],
    "edges": [
        {"source": "n1", "sourceHandle": "out", "target": "n2", "targetHandle": "in_0", "id": "n1-n2", "animated": True, "selected": False, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}},
        {"source": "n2", "sourceHandle": "out", "target": "n3", "targetHandle": "in_0", "id": "n2-n3", "animated": True, "selected": False, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}},
        {"source": "n3", "sourceHandle": "out", "target": "n4", "targetHandle": "in_0", "id": "n3-n4", "animated": True, "selected": False, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}},
        {"source": "n4", "sourceHandle": "out", "target": "n5", "targetHandle": "in_0", "id": "n4-n5", "animated": True, "selected": False, "style": {"stroke": "#b1b1b7", "strokeWidth": 2}}
    ],
    "viewport": {"x": 288.95, "y": -52.76, "zoom": 0.55},
    "agents": [
        {
            "name": "Window by agent",
            "description": "The table has access to the number of failures in a window of 30 sec, and timestamps",
            "tools": ["n3"]
        }
    ]
}

# Load the new workflow JSON - use NEW_WORKFLOW_PIPELINE for mock server
# This is the checkout monitoring pipeline with 6 nodes
DOWNTIME_FLOWCHART: Dict[str, Any] = NEW_WORKFLOW_PIPELINE


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and return the path for use in WebSocket connection."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Create a unique filename to avoid conflicts
        file_id = str(uuid.uuid4())
        file_path = TEMP_PDF_DIR / f"{file_id}_{file.filename}"
        
        # Save the uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"[SERVER] PDF uploaded: {file_path} ({len(content)} bytes)")
        
        return {
            "pdf_path": str(file_path),
            "filename": file.filename,
            "size": len(content),
        }
    except Exception as e:
        print(f"[SERVER] Error uploading PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}")


class MockWSAgenticSession:
    """WebSocket-based session that mocks the behavior of WSAgenticSession."""

    def __init__(self, metrics_list: List[Dict[str, Any]], output_dir: str):
        self.metrics_list = metrics_list
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Use the NEW_WORKFLOW_PIPELINE with 6 nodes
        self.all_nodes = NEW_WORKFLOW_PIPELINE.get("nodes", [])
        self.all_edges = [e for e in NEW_WORKFLOW_PIPELINE.get("edges", [])]
        
        self.phase1_nodes = []
        self.phase2_nodes = []
        
        # For the checkout monitoring pipeline:
        # Phase 1: n1 (spans input), n6 (logs input) - input nodes
        # Phase 2: n2 (filter checkout), n3 (window), n4 (threshold filter), n5 (trigger RCA)
        
        phase1_ids = ["n1", "n6"]  # Input nodes
        phase2_ids = ["n2", "n3", "n4", "n5"]  # Processing nodes in order
        
        for node in self.all_nodes:
            nid = node.get("id", "")
            if nid in phase1_ids:
                self.phase1_nodes.append(node)
        
        # Sort phase1 nodes: n1 first, then n6
        self.phase1_nodes.sort(key=lambda x: phase1_ids.index(x["id"]) if x["id"] in phase1_ids else 999)
        
        for node in self.all_nodes:
            nid = node.get("id", "")
            if nid in phase2_ids:
                self.phase2_nodes.append(node)
        
        # Sort Phase 2 nodes by dependency order
        self.phase2_nodes.sort(key=lambda x: phase2_ids.index(x["id"]) if x["id"] in phase2_ids else 999)

        self.phase1_flowchart = {"nodes": [], "edges": []}
        self.phase2_graph = {"nodes": [], "edges": []}
        
        self.metric_filter_map: Dict[str, List[str]] = {}
        self.filter_index: Dict[str, Dict[str, Any]] = {}
        self.input_node_id: Optional[str] = None

    async def run(self, ws: WebSocket):
        """Run full session."""
        print("\n" + "="*60)
        print("[SERVER] STEP 1: Starting session (MOCK)")
        print(f"[SERVER] → Processing {len(self.metrics_list)} metric(s)")
        print("="*60)

        await ws.send_json({
            "type": "session_start",
            "metrics": self.metrics_list,
            "message": "Session started"
        })

        if not await self.run_phase1_interactive(ws):
            return

        if not await self.run_phase2_iterative(ws):
            return

        await self.save_final_flowchart(ws)

    async def run_phase1_interactive(self, ws: WebSocket) -> bool:
        """Run Phase 1 interactively via WebSocket (Mocked) - Input nodes only."""
        print("\n[SERVER] Phase 1.1: Sending phase announcement")
        await ws.send_json({
            "type": "phase",
            "phase": 1,
            "message": "Starting Phase 1: Input Node Configuration"
        })

        # Add random delay
        delay = await random_delay()
        print(f"[SERVER] Random delay: {delay:.2f}s")

        print("\n[SERVER] Phase 1.2: Sending metrics summary")
        await ws.send_json({
            "type": "metrics_summary",
            "metrics": self.metrics_list,
            "message": f"Loaded {len(self.metrics_list)} metrics for processing"
        })

        # --- Simplified Scripted Conversation for Checkout Monitoring ---

        # Message 1: Initial agent introduction
        msg_1 = """I am the Pipeline Builder agent. I'll help you create a monitoring pipeline for checkout failures.

Based on your requirements, I'll configure:
1. **OpenTelemetry Spans Input** - to collect span data from Kafka
2. **OpenTelemetry Logs Input** - to collect log data for RCA analysis

Let's start by setting up the input nodes. The spans input will read from the `otlp_spans` topic and the logs input from `otlp_logs`.

Do you want to proceed with the default Kafka configuration (bootstrap servers: `34.93.25.61:9092`)?"""
        if not await self._send_and_wait(ws, msg_1): return False

        # Message 2: Confirmation
        msg_2 = """I'll now configure the input nodes with the specified settings.

**Configuration Summary:**
- **Spans Input (n1):** Topic `otlp_spans`, Group ID `test_group_spans`
- **Logs Input (n6):** Topic `otlp_logs`, Group ID `test_group_logs`

I'll propose each node for your approval. You can review the configuration and approve or modify as needed."""
        if not await self._send_and_wait(ws, msg_2): return False

        # --- Scripted Conversation End ---

        try:
            # Send Phase 1 nodes one at a time with hardcoded agent outputs
            print("\n[SERVER] Phase 1.5: Sending Phase 1 nodes one at a time")
            
            for node_index, next_node in enumerate(self.phase1_nodes):
                node_id = next_node.get("id", "")
                print(f"\n[SERVER] Phase 1 - Proposing node {node_index + 1}/{len(self.phase1_nodes)}: {node_id}")
                
                # Send hardcoded agent output for this node
                agent_output = NODE_AGENT_OUTPUTS.get(node_id, f"Configuring node {node_id}...")
                await ws.send_json({
                    "type": "agent_response",
                    "phase": 1,
                    "node_id": node_id,
                    "message": agent_output
                })
                
                # Add random delay to simulate agent thinking
                delay = await random_delay()
                print(f"[SERVER] Random delay after agent output: {delay:.2f}s")
                
                # Calculate edges for this node (edges where target is next_node['id'])
                relevant_edges = [
                    e for e in self.all_edges 
                    if e["target"] == next_node["id"]
                ]
                
                # We need to make sure the source nodes exist in current graph (Phase 1 so far)
                current_node_ids = {n["id"] for n in self.phase1_flowchart.get("nodes", [])}
                
                # Filter edges to only include those whose source nodes exist
                valid_edges = [
                    e for e in relevant_edges 
                    if e["source"] in current_node_ids
                ]

                await ws.send_json({
                    "type": "node_proposed",
                    "metric_index": 0,
                    "step_index": node_index,
                    "node": next_node,
                    "edges": valid_edges,
                })

                # Add random delay
                delay = await random_delay()
                print(f"[SERVER] Random delay after node proposal: {delay:.2f}s")

                await ws.send_json({
                    "type": "await_approval",
                    "metric_index": 0,
                    "step_index": node_index,
                })

                # Wait for approval
                msg = await ws.receive_text()
                approval_data = json.loads(msg)
                action = approval_data.get("action")

                if action == "quit":
                    await ws.send_json({"type": "done", "reason": "quit"})
                    return False
                
                if action == "approve":
                    # Add node to phase1_flowchart
                    self.phase1_flowchart["nodes"].append(next_node)
                    self.phase1_flowchart["edges"].extend(valid_edges)

                    # Send flowchart update with all Phase 1 nodes accepted so far
                    await ws.send_json({
                        "type": "node_approved",
                        "metric_index": 0,
                        "step_index": node_index,
                        "message": f"Phase 1 node {node_index + 1} approved",
                    })
                    
                    # Add random delay
                    delay = await random_delay()
                    print(f"[SERVER] Random delay after approval: {delay:.2f}s")
                    
                    await ws.send_json({
                        "type": "flowchart_update",
                        "flowchart": {
                            "nodes": self.phase1_flowchart.get("nodes", []),
                            "edges": self.phase1_flowchart.get("edges", []),
                        },
                        "message": f"Phase 1 node {node_index + 1} approved and added to flowchart",
                    })
                else:
                    # Reject or other - for mock, we just continue
                    pass

            # All Phase 1 nodes approved - prepare metadata and complete Phase 1
            self._prepare_filter_metadata()
            # Don't apply layout - preserve original positions from JSON
            # apply_layout(self.phase1_flowchart)

            print("\n[SERVER] Phase 1.6: All Phase 1 nodes approved - Sending Phase 1 completion message")
            await ws.send_json({
                "type": "phase1_complete",
                "flowchart": self.phase1_flowchart,
                "message": "Phase 1 completed successfully"
            })
            return True

        except Exception as e:
            print(f"Error in Phase 1: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_and_wait(self, ws: WebSocket, message: str) -> bool:
        """Helper to send an agent message and wait for user input."""
        print(f"\n[SERVER] Sending agent message: {message[:50]}...")
        await ws.send_json({
            "type": "agent_response",
            "phase": 1,
            "message": message
        })

        # Add 1 second delay to show "Generating workflow..." in frontend
        print("[SERVER] Waiting 1 second before enabling input...")
        await asyncio.sleep(1)

        print("[SERVER] Waiting for user input...")
        await ws.send_json({
            "type": "await_input",
            "phase": 1
        })

        try:
            msg = await ws.receive_text()
            user_data = json.loads(msg)
            user_input = user_data.get("message", "").strip()
            print(f"[SERVER] User said: {user_input}")
            
            if user_input.lower() in ('quit', 'exit'):
                await ws.send_json({"type": "done", "reason": "quit"})
                return False
            return True
        except Exception as e:
            print(f"[SERVER] Error receiving input: {e}")
            return False

    async def run_phase2_iterative(self, ws: WebSocket) -> bool:
        """Run Phase 2 iteratively via WebSocket (Mocked) - Processing nodes."""
        print("\n[SERVER] Phase 2.1: Sending Phase 2 announcement")
        await ws.send_json({
            "type": "phase",
            "phase": 2,
            "message": "Starting Phase 2: Pipeline Processing Nodes"
        })

        # Add random delay
        delay = await random_delay()
        print(f"[SERVER] Random delay: {delay:.2f}s")

        print("\n[SERVER] Phase 2.2: Sending filter assignments")
        await ws.send_json({
            "type": "filter_assignments",
            "assignments": self.metric_filter_map,
        })

        # We assume one metric flow for the demo
        for metric_index, metric in enumerate(self.metrics_list):
            metric_name = metric.get("metric_name") or f"metric_{metric_index}"
            filter_ids = self.metric_filter_map.get(metric_name, [])
            filter_context = summarize_filter_context(filter_ids, self.filter_index, self.input_node_id)

            await ws.send_json({
                "type": "metric_start",
                "metric_index": metric_index,
                "metric_name": metric_name,
                "filters": filter_ids,
                "filter_context": filter_context,
            })

            # Macro Plan for the checkout monitoring pipeline
            macro_plan = [
                "Filter checkout requests",           # n2
                "Window aggregation (30s)",           # n3
                "Threshold filter (>= 5 failures)",   # n4
                "Trigger RCA on threshold breach",    # n5
            ]
            
            # The phase2_nodes list: n2, n3, n4, n5

            await ws.send_json({
                "type": "macro_plan",
                "metric_index": metric_index,
                "steps": macro_plan,
                "metric_description": metric.get("description", ""),
                "total_steps": len(macro_plan),
            })

            step_index = 0
            while step_index < len(macro_plan) and step_index < len(self.phase2_nodes):
                step_desc = macro_plan[step_index]
                next_node = self.phase2_nodes[step_index]
                node_id = next_node.get("id", "")
                
                await ws.send_json({
                    "type": "step_start",
                    "metric_index": metric_index,
                    "step_index": step_index,
                    "total_steps": len(macro_plan),
                    "step": step_desc,
                })

                # Send hardcoded agent output for this node
                agent_output = NODE_AGENT_OUTPUTS.get(node_id, f"Configuring node {node_id}...")
                await ws.send_json({
                    "type": "agent_response",
                    "phase": 2,
                    "node_id": node_id,
                    "message": agent_output
                })
                
                # Add random delay to simulate agent thinking
                delay = await random_delay()
                print(f"[SERVER] Random delay after agent output: {delay:.2f}s")

                # Calculate edges for this node
                # Edges where target is next_node['id']
                relevant_edges = [
                    e for e in self.all_edges 
                    if e["target"] == next_node["id"]
                ]
                
                # We need to make sure the source nodes exist in current graph (Phase 1 + Phase 2 so far)
                current_node_ids = {n["id"] for n in self.phase1_flowchart.get("nodes", [])}
                current_node_ids.update({n["id"] for n in self.phase2_graph.get("nodes", [])})
                
                # Filter edges to only include those whose source nodes exist
                valid_edges = [
                    e for e in relevant_edges 
                    if e["source"] in current_node_ids
                ]
                
                await ws.send_json({
                    "type": "node_proposed",
                    "metric_index": metric_index,
                    "step_index": step_index,
                    "node": next_node,
                    "edges": valid_edges,
                })

                # Add random delay
                delay = await random_delay()
                print(f"[SERVER] Random delay after node proposal: {delay:.2f}s")

                await ws.send_json({
                    "type": "await_approval",
                    "metric_index": metric_index,
                    "step_index": step_index,
                })

                # Wait for approval
                msg = await ws.receive_text()
                approval_data = json.loads(msg)
                action = approval_data.get("action")

                if action == "quit":
                    await ws.send_json({"type": "done", "reason": "quit"})
                    return False
                
                if action == "approve":
                    self._finalize_node(next_node, valid_edges, step_index)
                    
                    # Send flowchart update with all nodes (Phase 1 + Phase 2 so far)
                    merged_flowchart = {
                        "nodes": self.phase1_flowchart.get("nodes", []) + self.phase2_graph.get("nodes", []),
                        "edges": self.phase1_flowchart.get("edges", []) + self.phase2_graph.get("edges", []),
                    }
                    
                    phase1_nodes = self.phase1_flowchart.get("nodes", [])
                    phase2_nodes = self.phase2_graph.get("nodes", [])
                    
                    print(f"[SERVER] Sending flowchart_update after step {step_index + 1}:")
                    print(f"  - Phase 1 nodes: {len(phase1_nodes)} (IDs: {[n.get('id', '?') for n in phase1_nodes]})")
                    print(f"  - Phase 2 nodes so far: {len(phase2_nodes)} (IDs: {[n.get('id', '?') for n in phase2_nodes]})")
                    print(f"  - Total nodes: {len(merged_flowchart['nodes'])}")
                    print(f"  - All Node IDs: {[n.get('id', '?') for n in merged_flowchart['nodes']]}")
                    print(f"  - Newly approved node: {next_node.get('id', '?')} at position: {next_node.get('position', {})}")
                    
                    # Send node_approved first, then flowchart_update
                    await ws.send_json({
                        "type": "node_approved",
                        "metric_index": metric_index,
                        "step_index": step_index,
                        "message": f"Step {step_index + 1} approved",
                    })
                    
                    # Add random delay
                    delay = await random_delay()
                    print(f"[SERVER] Random delay after approval: {delay:.2f}s")
                    
                    # Then send flowchart_update with all nodes
                    await ws.send_json({
                        "type": "flowchart_update",
                        "flowchart": merged_flowchart,
                        "message": f"Step {step_index + 1} approved and added to flowchart",
                    })
                    step_index += 1
                else:
                    # Reject or other - for mock, we just loop or error
                    # But let's assume happy path for demo
                    pass

        await ws.send_json({
            "type": "phase2_complete",
            "message": "Phase 2 completed successfully for all metrics",
        })
        return True

    def _prepare_filter_metadata(self) -> None:
        filter_nodes: List[Dict[str, Any]] = []
        self.input_node_id = None

        for node in self.phase1_flowchart.get("nodes", []):
            node_type = node.get("node_id") or node.get("type")
            if node_type == "open_tel_spans_input":
                self.input_node_id = node.get("id")
            elif node_type == "filter":
                filter_nodes.append(node)

        self.filter_index = {node.get("id"): node for node in filter_nodes}

        # Auto assign (mocked or real logic)
        # Since we have one metric and some filters, we can just assign all filters to the metric
        # or use the real logic if imported.
        
        # For the mock, let's just assign all filters to the first metric
        if self.metrics_list:
            metric_name = self.metrics_list[0].get("metric_name")
            self.metric_filter_map = {
                metric_name: [n["id"] for n in filter_nodes]
            }
            # If there are no filters, assign input node
            if not self.metric_filter_map[metric_name]:
                self.metric_filter_map[metric_name] = [self.input_node_id] if self.input_node_id else []

    def _finalize_node(self, node: Dict[str, Any], edges: List[Dict[str, Any]], step_index: int):
        self.phase2_graph["nodes"].append(node)
        self.phase2_graph["edges"].extend(edges)
        self._save_flowchart(step_index)

    def _save_flowchart(self, step_index: Optional[int] = None):
        # Merge Phase 1 and Phase 2 nodes/edges, keeping all previous nodes
        merged = {
            "nodes": self.phase1_flowchart.get("nodes", []) + self.phase2_graph.get("nodes", []),
            "edges": self.phase1_flowchart.get("edges", []) + self.phase2_graph.get("edges", []),
            "agents": []
        }
        apply_layout(merged)
        
        # Save to session directory
        out_file = self.output_dir / "flowchart.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
            
        # Also save to default directory so frontend can pick it up immediately
        default_out_file = DEFAULT_OUTPUT_DIR / "flowchart.json"
        with default_out_file.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
            
        if step_index is not None:
            step_file = self.output_dir / f"flowchart_node_{step_index:02d}.json"
            with step_file.open("w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2)
            
            # Also save step file to default directory
            default_step_file = DEFAULT_OUTPUT_DIR / f"flowchart_node_{step_index:02d}.json"
            with default_step_file.open("w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2)

    async def save_final_flowchart(self, ws: WebSocket):
        self._save_flowchart()
        merged = {
            "nodes": self.phase1_flowchart.get("nodes", []) + self.phase2_graph.get("nodes", []),
            "edges": self.phase1_flowchart.get("edges", []) + self.phase2_graph.get("edges", []),
            "agents": []
        }
        apply_layout(merged)
        
        await ws.send_json({
            "type": "final",
            "flowchart": merged,
            "path": str(self.output_dir / "flowchart.json"),
            "message": "Final flowchart saved successfully"
        })


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_output_dir = None

    try:
        init_msg = await ws.receive_text()
        init_data = json.loads(init_msg)

        output_dir = str(DEFAULT_OUTPUT_DIR)
        session_id = str(uuid.uuid4())
        session_output_dir = str(Path(output_dir) / session_id)

        metrics_list = init_data.get("metrics")
        
        # Handle PDF upload case
        if init_data.get("pdf_path"):
            pdf_path = init_data["pdf_path"]
            additional_description = init_data.get("description", "").strip() if init_data.get("description") else None
            print(f"\n[SERVER] Processing PDF: {pdf_path}")
            if additional_description:
                print(f"[SERVER] → Combining PDF with description for metric extraction")
                print(f"[SERVER] → Description provided: {additional_description[:100]}...")
            else:
                print(f"[SERVER] → Extracting metrics from PDF only")
            
            # For mock server, just create a default metric from PDF
            # In real server, this would use LLM to extract metrics
            if not metrics_list:
                metrics_list = [{
                    "metric_name": "Downtime",
                    "description": additional_description or "Downtime percentage of payment service over 30 seconds must be < 1%",
                    "category": "availability",
                }]
                print(f"[SERVER] ✓ Created default metric from PDF")
                await ws.send_json({
                    "type": "metrics_loaded",
                    "message": f"Extracted metrics from PDF. Using default downtime metric.",
                })
        
        if not metrics_list:
            metrics_list = [{
                "metric_name": init_data.get("metric", "Payment Latency"),
                "description": init_data.get("description", "Latency between charge and webhook"),
                "category": init_data.get("category", "unspecified"),
            }]

        print(f"[SERVER] New mock session: {session_id}")
        await ws.send_json({"type": "session_id", "session_id": session_id})

        session = MockWSAgenticSession(metrics_list, output_dir=session_output_dir)
        try:
            await session.run(ws)
        finally:
            if session_output_dir and Path(session_output_dir).exists():
                # shutil.rmtree(session_output_dir) # Keep for debugging if needed
                pass

    except WebSocketDisconnect:
        print("[SERVER] Client disconnected")
    except Exception as e:
        print(f"[SERVER] WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except:
            pass

if __name__ == "__main__":
    import argparse
    
    print("=" * 60)
    print(" AGENTIC SERVER (Mock, deterministic flowchart) ")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(description="Mock Agentic Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("CONTRACT_PARSER_PORT", "8001")), 
                        help="Port to run the server on (default: 8001 or CONTRACT_PARSER_PORT env)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print(f"Starting server on {args.host}:{args.port}")

    uvicorn.run(
        "mock_server:app",
        host=args.host,
        port=args.port,
        reload=True,
        ws_ping_interval=None,
        ws_ping_timeout=None,
    )