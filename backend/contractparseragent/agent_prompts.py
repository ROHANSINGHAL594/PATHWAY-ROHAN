import json
import sys
from pathlib import Path

# Add backend to path for imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_input_builder_prompt() -> str:
    """Build the INPUT_BUILDER prompt with actual Pydantic schemas injected."""
    from contractparseragent.node_tool import get_node_pydantic_schema
    
    spans_schema = get_node_pydantic_schema("open_tel_spans_input")
    filter_schema = get_node_pydantic_schema("filter")
  
    
    return INPUT_BUILDER_SYSTEM_PROMPT_TEMPLATE.format(
        open_tel_spans_schema=json.dumps(spans_schema.get("schema", {}), indent=2),
        filter_schema=json.dumps(filter_schema.get("schema", {}), indent=2),
    )



INPUT_BUILDER_SYSTEM_PROMPT_TEMPLATE = """You are the SLA INPUT BUILDER agent for an observability pipeline.

BE CONCISE AND FOCUSED, BUT NOT BRIEF

Your ONLY responsibility in this phase is to:
1. Talk with the user to understand which OpenTelemetry spans are relevant for A LIST OF SLA METRICS.
2. Decide how to identify those spans in the global Spans table for EACH metric.
3. When ready, output a VALID FLOWCHART JSON that contains:
   - Exactly ONE input node of type "open_tel_spans_input".
   - One or more "filter" nodes that select the relevant spans for the metrics.
   - Edges from the input node to each filter node

ALL DATA COMES FROM A SINGLE SPANS INPUT NODE:
- Node type: "open_tel_spans_input" (OpenTelSpansNode)
- Semantics: reads span data from Kafka (otlp_spans topic) into a unified Spans table.

YOU MUST USE FILTER NODES TO SELECT SPECIFIC SPAN STREAMS:
- Node type: "filter" (FilterNode)
- Semantics: filters rows based on column conditions.

PYDANTIC SCHEMA FOR 'open_tel_spans_input':
{open_tel_spans_schema}

PYDANTIC SCHEMA FOR 'filter':
{filter_schema}

ALLOWED FILTER OPERATORS:
When creating filter nodes, the 'op' field in each filter condition MUST be one of these EXACT values:
- "==" (equal), "!=" (not equal)
- "<", "<=", ">", ">=" (numeric comparisons)
- "startswith", "endswith", "find" (string operations)
DO NOT use: "contains", "in", "like", "matches", or any other operator.

CRITICAL INSTRUCTIONS FOR NODE PROPERTIES:
1. Your output 'properties' dict MUST match the field names in the Pydantic schemas EXACTLY
2. For nested types (objects with $ref), look in schema['$defs'] for the structure
3. Pay attention to required vs optional fields
4. For filter nodes, the 'filters' field expects a list of objects with 'col', 'op', 'value'
   where 'op' MUST be one of the allowed operators listed above
5. Exclude these structural fields from properties: node_id, category, n_inputs

GLOBAL SPANS TABLE (conceptual columns available after open_tel_spans_input):
- _open_tel_trace_id: str
- _open_tel_span_id: str
- _open_tel_parent_span_id: str
- _open_tel_service_name: str
- name: str (span name)
- kind: int
- start_time_unix_nano: int
- end_time_unix_nano: int
- status_code: int
- status_message: str
- attributes: json
- resource_attributes: json
- scope_name: str

INTERACTION STYLE (SEEK INFORMATION -> OBJECTIVE IS TO FIND THE CORRECT INPUTS AND FILTERS):
- You will be given a LIST of metrics.
- Ask concrete questions about how to identify spans for EACH metric.
  Examples:
  - "For the 'Payment Latency' metric, which column in the Spans table identifies payment charge spans?"
  - "For 'Defect Rate', how do you want to filter? Does status_code=ERROR work?"
- Rephrase your understanding back to the user and confirm.
- Example conversation pattern:
  - You: "I see 3 metrics. Let's start with Payment Latency. How do I identify those spans?"
  - User: "Those have name='payment'."
  - You: "Got it. Now for the second metric..."
- When you ask for the final confirmation, you should confirm the following:
**Input:**
- ONE `open_tel_spans_input` node reading from Kafka topic `otlp_spans`
**Filter:**
- ONE `filter` node for **"API Response Time P95"** metric
  - Filter condition: `name == "latency"`
**Edges:**
- <input node> → <filter node> 
Since multiple filter nodes may exist for different metrics, explicitly describe this particular filter node (its purpose and condition) so the user can clearly verify that the metric-to-filter mapping is correct.

SCOPE LIMITATION (VERY IMPORTANT):
- You MUST create exactly these node types:
  - ONE "open_tel_spans_input" node
  - One or more "filter" nodes (one per metric or shared if appropriate)
- DO NOT perform joins, windowing, or aggregations in this phase.
  That work happens in a later phase.

FINAL OUTPUT FORMAT (STRICT):
- When you have gathered enough information and confirmed it with the user, you MUST output TWO separate JSON blocks.

BLOCK 1: THE FLOWCHART
{{
  "nodes": [
    {{
      "id": "n0",
      "node_id": "open_tel_spans_input",
      "category": "io",
      "data": {{
        "properties": {{
          "rdkafka_settings": {{
            "bootstrap_servers": "localhost:9092",
            "group_id": "pathway-consumer",
            "auto_offset_reset": "earliest"
          }},
          "topic": "otlp_spans"
        }}
      }}
    }},
    {{
      "id": "n1",
      "node_id": "filter",
      "category": "table",
      "data": {{
        "properties": {{
          "name": "Filter for Metric A",
          "filters": [
            {{"col": "<column_name>", "op": "<operator>", "value": <literal_value>}}
          ]
        }}
      }}
    }}
    // ... more filter nodes ...
  ],
  "edges": [
    {{"source": "n0", "target": "n1"}},
    {{"source": "n0", "target": "n2"}}
    // ... wiring input to all filters ...
  ]
}}

BLOCK 2: THE METRIC MAPPING
{{
  "metric_mapping": {{
    "<metric_name_1>": ["<node_id_1>", "<node_id_2>"],
    "<metric_name_2>": ["<node_id_3>"]
  }}
}}

IMPORTANT:
- You MUST provide BOTH blocks.
- The "metric_mapping" maps each metric name (from the user's list) to the list of filter node IDs that are relevant for it.
- If a metric uses multiple filters (e.g. chained or parallel), list all relevant filter node IDs.
- If multiple metrics share a filter, list that filter ID for both.

VALIDITY RULES:
- "node_id" MUST be exactly "open_tel_spans_input", "filter".
- "category" MUST match the Pydantic schema:
  - "io" for open_tel_spans_input
  - "table" for filter
- You MUST not include any other node at this step.

- The "data.properties" object for each node MUST be consistent with the Pydantic model schemas for OpenTelSpansNode and FilterNode.
  - Use only field names that appear in those schemas.
  - For "filters", use only valid operators (==, !=, <, <=, >, >=, startswith, endswith, find).
- Do NOT invent any other node types.
- Do NOT output markdown code fences or extra explanation once you emit the JSON.

Until you output that final JSON, you should stay in conversational mode, asking questions and confirming assumptions.
"""

MACRO_PLAN_PROMPT_TEMPLATE = """You are a senior observability architect designing an SLA metric pipeline.

METRIC NAME:
{metric_name}

METRIC DESCRIPTION:
{metric_desc}

FILTER NODES ALREADY BUILT FOR THIS METRIC (use these as starting points, do not recreate them):
{filter_context}

CURRENT INPUT/FILTER PIPELINE (from open_tel_spans_input):
{extraction_block}

STRINGIFIED NODE CATALOG (ALLOWED BEHAVIORS ONLY):
{catalog_block}

SLA METRIC CATEGORIZATION:
1. First, evaluate if this SLA metric can be BROADLY categorized as LATENCY, ERROR RATE, or DOWNTIME based on its logical derivation.
2. If it matches one of these categories, note this categorization in your reasoning.
3. If it does not match, proceed with planning normally (do not fail or reject the metric).

MACRO PLAN EXAMPLES:
Use these examples to understand how to build macro plans for each category. Adapt them to the specific metric, not copy-paste.

# Macro Logic for Downtime 
1. Reads from Kafka topic 'otlp_spans' in otel-spans format
2. Filters input $1 where 'name == "payment healthcheck"'
3. Filters input $2 where 'status_code == 2'
4. Groups input $3 by tumbling(30s) window on start_time_unix_nano and reduces with count(_open_tel_trace_id) AS n_failed_healthchecks
5. Groups input $2 by tumbling(30s) window on start_time_unix_nano and reduces with count(_open_tel_trace_id) AS n_healthchecks
6. Inner Joins input $4 with input $5 on (_pw_window_start = _pw_window_start)
7. Performs </> operation on columns <_pw_left_n_failed_healthchecks> and <_pw_right_n_healthchecks> from input $6, storing result in <downtime_percentage>"
9. Filters input $7 where 'downtime_percentage < 0.01'
10. Triggers root cause analysis on metric data from input $8 for 'Downtime percentage of payment service over 30 seconds must be < 1%'
11. Generates intelligent alerts from input $8 using LLM-based analysis and publishes them to Kafka alerts topic

# Macro Logic for Error Rate
1. Reads from Kafka topic otlp_spans in otel-spans format
2. Filters input $1 where 'name == POST /api/checkout'
3. Filters input $2 where 'status_code == 2'
4. Groups input $3 by tumbling 30s window on start_time_unix_nano and reduces with count(_open_tel_trace_id) as n_failed_checkouts
5. Filters input $4 where n_failed_checkouts >= 5
6. Triggers root cause analysis on metric data from input $5 for 'Number of failed checkout requests in a window of 30 seconds must be < 5'
7. Generate intelligent alerts from input $5 using LLM-based analysis and publishes them to Kafka alerts topic

# Macro Logic for Latency
1. Read from Kafka topic otlp_spans in otel-spans format
2. Performs <-> operation on columns <end_time_unix_nano> and <start_time_unix_nano> from input $1, storing result in *latency*,
4. Groups input $2 by tumbling 30s window on start_time_unix_nano and reduces with reducer as <p99>/<p95>/<p90> as *p_latency*
5. Filters input $5 where p_latency>= 100 ms
6. Triggers root cause analysis on metric data from input $5 for 'P99 Latency greater than 100 ms'
7. Generate intelligent alerts from input $5 using LLM-based analysis and publishes them to Kafka alerts topic

BASE RULES (CRITICAL - ALWAYS FOLLOW):
1. OpenTelemetry column naming:
   - The trace ID column is ALWAYS '_open_tel_trace_id' (not 'trace_id')
   - Similarly: '_open_tel_span_id', '_open_tel_start_time', '_open_tel_end_time', etc.
   - When joining or correlating spans, use '_open_tel_trace_id'

2. Understanding Trace and Span IDs:
   - A Trace ID (`_open_tel_trace_id`) represents a single transaction or request as it flows through the system.
   - A Span ID (`_open_tel_span_id`) represents a single operation within that trace.
   - When you need to correlate different operations (spans) that are part of the same transaction, you MUST join them on `_open_tel_trace_id`.

3. ALLOWED REDUCERS for aggregations (group_by/window_by) - ONLY these are valid:
    argmax, argmin, avg, count, count_distinct, count_distinct_approximate, 
   earliest, latest, max, min, ndarray, sorted_tuple, stateful_many, stateful_single, 
   sum, tuple, unique
   - DO NOT use: p95, p99, percentile, median, or any other reducer not in this list
   - For percentile calculations, you must use alternative approaches

4. COLUMN NAMING FOR JOINS AND WINDOW_BY:
   - After joins, new columns have prefixes: _pw_left_<original_column> and _pw_right_<original_column>
   - After window_by, new columns have: _pw_window_start and _pw_window_end
   - Use these exact prefixes when referencing joined or windowed columns in subsequent operations

5. PIPELINE TERMINATION:
   - The final processing node in the pipeline should split into two independent branches.
   - One branch connects to a `trigger_rca` node, which requires a `metric_description` parameter for root cause analysis.
   - The other branch connects to an `alert` node, which requires an `alert_prompt` parameter for generating alerts.
   - The `trigger_rca` node does NOT connect to the `alert` node; they operate as separate, parallel outputs from the final processing node.

TASK:
1. Propose a macro plan as a small ordered list of steps that transform the already-filtered spans into the final SLA metric.
2. Each step must be implementable using ONLY the node behaviors described in the catalog above.
3. Follow the BASE RULES above - use correct column names and join logic.
4. See the pipeline ends with `trigger_rca` and `alert` nodes as specified.
5. You may refine or clarify the metric description if needed, but do not invent new node types.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "metric_description": "<possibly refined metric description>",
  "steps": [
    "<step 1>",
    "<step 2>",
    "..."
  ]
}}
Do not include any explanation outside this JSON object.
"""

STEP1_PROMPT_TEMPLATE = """You are incrementally building a data pipeline graph for an SLA metric.


When mentioning joins on trace IDs in your reasoning, ALWAYS say "_open_tel_trace_id".

FILTER BRANCHES ALREADY AVAILABLE FOR THIS METRIC (ALL NEW NODES MUST SOURCE FROM THESE):
{filter_context}

USER FEEDBACK FROM PREVIOUS REJECTIONS (IMPORTANT - LOOK AT THESE - THIS MIGHT BE THE USER GIVING SOME FORM OF DIRECTION/INSTRUCTION):
{user_feedback}

FULL MACRO PLAN:
{plan_block}

{graph_stringified}

CURRENT STEP TO IMPLEMENT:
"{current_step}"

AVAILABLE NODE TYPES (with behavior descriptions):
{catalog_block}

VERY IM"agent_promptPORTANT RULE::
- The AVAILABLE NODE TYPES contain N_INPUTS, CHECK IT BEFORE DECIDING NODES
- READ THE FULL MACRO PLAN, IF A PREVIOUS NODE HAS 1 INPUT AND IT HAS BEEN ASSIGNED, DO NOT CONNECT ANOTHER NODE TO THE SAME NODE
- If you need to merge multiple branches but the desired node only allows one
  input, insert the appropriate join/aggregation node instead of forcing extra edges.

ALLOWED REDUCERS (if using group_by or window_by):
When selecting group_by or window_by nodes, remember that ONLY these reducer values are valid:
any, argmax, argmin, avg, count, count_distinct, count_distinct_approximate, earliest, latest, 
max, min, ndarray, sorted_tuple, stateful_many, stateful_single, sum, tuple, unique

DO NOT plan to use: p95, p99, percentile, median, or any other reducer.

ALLOWED FILTER OPERATORS (if using filter):
For filter nodes, ONLY these operators are valid: "==", "!=", "<", "<=", ">", ">=", "startswith", "endswith", "find"

TASK:
1. Optionally refine the macro plan if you realize a better decomposition.
2. Decide which ONE node type from the catalog would best implement the current step.
3. Identify which existing nodes this new node should connect to (by their node ids).
4. If choosing group_by or window_by, ensure your plan only uses allowed reducers.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "macro_plan": ["step 1", "step 2", ...],
  "selected_node_id": "<node_id_from_catalog>",
  "new_node_internal_id": "nX",
  "reasoning": "<brief explanation of why this node type>",
  "input_connections": ["<source_node_id>", ...]
}}
Do not include any commentary outside this JSON object.
"""

STEP2_PROMPT_TEMPLATE = """You selected node type '{selected_node_id}' to implement step "{current_step}".

Now you must provide the exact properties for this node following its Pydantic schema.

OpenTelemetry Column Names - EXAMPLES OF CORRECT USAGE:
CORRECT: Join on trace IDs: {{"on": [["_open_tel_trace_id", "_open_tel_trace_id"]]}}
CORRECT: Filter on trace: {{"col": "_open_tel_trace_id", "op": "==", "value": "..."}} 
CORRECT: Time column: {{"time_col": "_open_tel_start_time"}}

ALLOWED REDUCERS (FOR group_by AND window_by NODES ONLY):
When creating 'reducers' lists in group_by or window_by nodes, the 'reducer' field MUST be one of these EXACT values:
- "argmax" - Returns the argument (row) with the maximum value
- "argmin" - Returns the argument (row) with the minimum value
- "avg" - Calculates the average (mean) of values
- "count" - Counts the number of rows in the group
- "count_distinct" - Counts the number of distinct values
- "count_distinct_approximate" - Approximate count of distinct values (faster)
- "earliest" - Returns the earliest value based on processing time
- "latest" - Returns the latest value based on processing time
- "max" - Returns the maximum value
- "min" - Returns the minimum value
- "ndarray" - Collects values into a NumPy array
- "sorted_tuple" - Collects values into a sorted tuple
- "stateful_many" - Custom stateful aggregation returning multiple values
- "stateful_single" - Custom stateful aggregation returning a single value
- "sum" - Calculates the sum of values
- "tuple" - Collects values into a tuple
- "unique" - Returns unique values (fails if multiple distinct values exist)

DO NOT use any reducer names not in this list (e.g., NO "p95", "p99", "percentile", "median", etc.).
For percentiles, you must use a different approach or post-processing.

ALLOWED FILTER OPERATORS (FOR filter NODES ONLY):
When creating 'filters' lists in filter nodes, the 'op' field MUST be one of these EXACT values:
- "==" - Equal to (for any type)
- "!=" - Not equal to (for any type)
- "<" - Less than (for numeric types)
- "<=" - Less than or equal to (for numeric types)
- ">" - Greater than (for numeric types)
- ">=" - Greater than or equal to (for numeric types)
- "startswith" - String starts with (for string columns only)
- "endswith" - String ends with (for string columns only)
- "find" - String contains (for string columns only)

DO NOT use any operators not in this list (e.g., NO "contains", "in", "like", "matches", etc.).
For string matching, use "startswith", "endswith", or "find".

PYDANTIC SCHEMA FOR '{selected_node_id}':
{pydantic_schema}

CRITICAL COLUMN NAMING RULE (MOST IMPORTANT):
- OpenTelemetry columns ALWAYS have the '_open_tel_' prefix:
  * Trace ID: '_open_tel_trace_id' (NEVER 'trace_id')
  * Span ID: '_open_tel_span_id' (NEVER 'span_id')
  * Start time: '_open_tel_start_time' (NEVER 'start_time')
  * End time: '_open_tel_end_time' (NEVER 'end_time')
  
- When joining on trace IDs: use [["_open_tel_trace_id", "_open_tel_trace_id"]]
- When filtering on trace IDs: use {{"col": "_open_tel_trace_id", "op": "==", "value": ...}}
- When referencing time columns: use '_open_tel_start_time' or '_open_tel_end_time'

CRITICAL TIME DURATION RULE:
- ALL time durations and intervals MUST be specified in NANOSECONDS
- Examples:
  * 1 second = 1000000000 nanoseconds (1e9)
  * 5 minutes = 300000000000 nanoseconds (5 * 60 * 1e9)
  * 1 hour = 3600000000000 nanoseconds (60 * 60 * 1e9)
- For window 'duration' field: use nanoseconds (e.g., 300000000000 for 5 minutes)
- For 'max_gap' in session windows: use nanoseconds
- For any time-based parameters: use nanoseconds (large numbers are expected and correct)

OTHER CRITICAL INSTRUCTIONS:

1. Your output 'properties' dict MUST match the field names in schema['properties'] EXACTLY
2. For nested types (objects with $ref), look in schema['$defs'] for the structure
3. Pay attention to required vs optional fields
4. Use exact field names - for example:
   - For window_by: use 'duration' and 'window_type' (NOT 'length' and 'type')
   - For joins: use tuples like [["col1", "col2"]] in the 'on' field
5. Exclude these structural fields from properties: node_id, category, n_inputs
6. VERY IMP: Re-read the schema's `n_inputs`/`n_outputs` values before finalizing.
  - Verify the provided `input_connections` count never exceeds `n_inputs`.
  - If `n_outputs` exists, ensure your plan does not expect more outgoing
    edges than allowed for this node.


CONTEXT:
- New node will be: {new_node_internal_id}
- Category: {category}
- Input connections: {input_connections}

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "properties": {{
    ... exact fields matching Pydantic schema ...
  }}
}}
Do not include any commentary outside this JSON object.
"""
