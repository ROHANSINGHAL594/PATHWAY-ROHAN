# **Agentic API Endpoints - Complete Overview**

## **Architecture**
The API is a unified FastAPI application at app.py serving multiple purposes:
1. **Agent-based query system** - Dynamic multi-agent workflow for data analysis
2. **Alert generation** - Structured alert creation from trigger conditions
3. **Telemetry summarization** - Natural language explanations of SLA metric pipelines
4. **Root Cause Analysis (RCA)** - Automated incident investigation for error/latency/uptime issues
5. **Report generation** - Incident reports and weekly summaries

---

## **Endpoints**

### **1. `GET /`**
**Purpose**: Health check  
**Input**: None  
**Output**: 
```json
{
  "status": "ok",
  "message": "Agentic API is running"
}
```
**Semantics**: Simple status verification endpoint

---

### **2. `POST /build`**
**Purpose**: Initialize the multi-agent planner system with custom agents  
**Input**:
```json
{
  "agents": [
    {
      "name": "agent_name",
      "description": "What this agent does",
      "tools": [
        {
          "table_name": "postgres_table",
          "connection_string": "postgresql://...",
          "columns": ["col1", "col2"]
        }
      ]
    }
  ],
  "pipeline_name": "my_pipeline"
}
```
**Output**:
```json
{
  "status": "built"
}
```
**Semantics**: 
- Creates a LangGraph-based "planner-executor" system
- Each agent gets SQL query tools for specified PostgreSQL tables
- Agents can be composed to answer complex queries
- Uses Groq's LLM by default (configurable via `DEFAULT_AGENT_PROVIDER` env var)
- Stores executor in global state for `/infer` endpoint

---

### **3. `POST /infer`**
**Purpose**: Query the multi-agent system with natural language  
**Input**:
```json
{
  "role": "user",
  "content": "What was the average latency for service X last week?"
}
```
**Output**:
```json
{
  "status": "ok",
  "answer": "The average latency for service X last week was 125ms."
}
```
**Semantics**:
- Requires `/build` to be called first (returns 502 if planner not initialized)
- Uses two-stage planning:
  - **Complete strategy**: Plans all steps upfront when query is deterministic
  - **Staged strategy**: Plans incrementally when next steps depend on runtime values
- Agents can reference prior results using `$1, $2` syntax
- Example: "Get revenue $1 and expenses $2, calculate margin"
- Returns human-readable answers (not raw data)

---

### **4. `POST /generate-alert`**
**Purpose**: Generate structured alerts from trigger conditions  
**Input**:
```json
{
  "alert_prompt": "Notify when error rate exceeds threshold",
  "trigger_description": "Error rate above 5% for 10 minutes",
  "trigger_data": {
    "service": "payment-api",
    "error_rate": 8.5,
    "threshold": 5.0,
    "timestamp": "2024-03-15T14:30:00Z"
  }
}
```
**Output**:
```json
{
  "status": "ok",
  "alert": {
    "type": "error",  // or "warning" or "info"
    "message": "payment-api error rate 8.5% exceeded 5% threshold at 14:30 UTC"
  }
}
```
**Semantics**:
- LLM classifies severity: `error` (critical), `warning` (degraded), `info` (routine)
- Generates concise message (<200 chars) for dashboards
- Extracts key values from trigger data

---

### **5. `POST /summarize`**
**Purpose**: Generate natural language descriptions of SLA metric calculations  
**Input**:
```json
{
  "metric_description": "P99 latency between service A and service B",
  "pipeline_description": "1. Ingest spans from OpenTelemetry\n2. Filter by service names\n3. Join on trace_id\n4. Calculate P99 latency",
  "semantic_origins": {
    "_open_tel_trace_id_service_a": [1, 2],
    "_open_tel_trace_id_service_b": [1, 2]
  }
}
```
**Output**:
```json
{
  "status": "ok",
  "summarized": {
    "special_column_descriptions": {
      "_open_tel_trace_id_service_a": "Trace IDs from service A spans representing request initiation",
      "_open_tel_trace_id_service_b": "Trace IDs from service B spans representing request completion"
    },
    "metric_calculation_explanation": "Calculates P99 latency by joining service A and B spans on trace_id and computing the 99th percentile of time differences.",
    "metric_type": "latency",
    "metric_calculation_window": 300
  },
  "cached": false
}
```
**Semantics**:
- Uses Context7 MCP (Model Context Protocol) server for Pathway library documentation
- Explains "special columns" (those with `_open_tel_trace_id` in name)
- Identifies semantic origins (last pipeline node where column meaning stabilizes)
- Caches responses in SQLite to avoid redundant LLM calls
- Metric types: `error`, `uptime`, `latency`

---

### **6. `POST /rca`**
**Purpose**: Perform automated root cause analysis on SLA breaches  
**Input**:
```json
{
  "description": "P99 latency breached 500ms threshold",
  "trace_ids": {
    "_open_tel_trace_id": ["trace-abc", "trace-def"]
  },
  "table_data": {
    "spans": {
      "table_name": "spans",
      "connection_string": "postgresql://...",
      "columns": ["trace_id", "span_id", "start_time", "end_time"]
    },
    "logs": {
      "table_name": "logs",
      "connection_string": "postgresql://...",
      "columns": ["trace_id", "timestamp", "severity", "body"]
    },
    "sla_metric_trigger": {
      "table_name": "sla_trigger",
      "connection_string": "postgresql://...",
      "columns": ["trace_id", "time"]
    }
  },
  "special_column_descriptions": {...},
  "metric_calculation_explanation": "...",
  "metric_type": "latency",
  "metric_calculation_window": 300
}
```
**Output**:
```json
{
  "analysis": {
    "severity": "CRITICAL",
    "affected_services": ["payment-service", "database-service"],
    "narrative": "P99 latency spiked from 100ms to 3500ms due to database connection pool exhaustion...",
    "error_citations": [
      {
        "timestamp": "2024-03-15T14:30:00Z",
        "service": "payment-service",
        "message": "Database connection pool exhausted: 50/50 connections in use"
      }
    ],
    "root_cause": "Database connection pool exhaustion due to long-running queries not releasing connections"
  }
}
```
**Semantics**:
- Three specialized agents based on `metric_type`:

**6a. Error RCA (`metric_type: "error"`)**:
- Fetches logs for failing trace IDs
- Groups logs by trace_id
- LLM analyzes error patterns across traces
- Returns structured `RCAAnalysisOutput`

**6b. Latency RCA (`metric_type: "latency"`)**:
- Uses LangGraph workflow:
  1. **Enrichment node**: Finds top 5 slowest traces
  2. **Parallel analysis**: Runs subgraph per trace
     - Fetches full span tree (topology)
     - Checks for error spans
     - Generates hypothesis about bottleneck
     - Fetches related logs
     - Validates hypothesis
  3. **Synthesis node**: Aggregates findings into final report
- Requires `breach_time_utc` and `breach_value` fields

**6c. Uptime RCA (`metric_type: "uptime"`)**:
- Fetches downtime timestamps from `sla_metric_trigger` table
- Creates `DowntimeIncident` objects
- Analyzes logs in 30-second window around each incident
- Parallel execution for multiple incidents
- Returns aggregated root cause

---

### **🐛 BUG DETECTED #1: Missing Fields in InitRCA**
**File**: analyse.py  
**Issue**: `InitRCA` class inherits from `SummarizeOutput` but the latency branch tries to access `breach_time_utc` and `breach_value` which don't exist in the schema.

**Line 53-54**:
```python
breach_time_utc=init_rca_request.breach_time_utc,  # ❌ Field doesn't exist
breach_value=init_rca_request.breach_value          # ❌ Field doesn't exist
```

**Expected**: `InitRCA` should include these fields for latency analysis:
```python
class InitRCA(SummarizeOutput):
    description: str
    trace_ids: Dict[str, Union[List[str], str]]
    table_data: Dict[Literal["spans", "logs", "sla_metric_trigger"], TablePayload]
    breach_time_utc: Optional[str] = None  # ✅ Add this
    breach_value: Optional[float] = None   # ✅ Add this
```

**Approval to fix?** Should I add these two optional fields to `InitRCA`?

---

### **7. `POST /api/v1/reports/incident`**
**Purpose**: Generate detailed incident report from RCA output  
**Input**:
```json
{
  "rca_output": {
    "severity": "CRITICAL",
    "affected_services": ["payment-service"],
    "narrative": "Payment service experienced critical performance degradation...",
    "error_citations": [
      {
        "timestamp": "2024-03-15T14:30:00Z",
        "service": "payment-service",
        "message": "Database connection pool exhausted"
      }
    ],
    "root_cause": "Database connection pool exhaustion"
  }
}
```
**Output**:
```json
{
  "success": true,
  "report_id": "INC-1710511800-payment-service",
  "report_content": "# Incident Report\n\n## Summary\n...",
  "severity": "CRITICAL",
  "generated_at": "2024-03-15T14:35:00Z",
  "processing_time_seconds": 18.5
}
```
**Semantics**:
- Uses LangGraph multi-agent workflow:
  1. **Planner Agent**: Outlines report structure
  2. **Drafter Agent**: Writes full markdown report
- Saves to file storage:
  - `reports/incident_{timestamp}_{severity}.md` (markdown)
  - `reports/incident_{timestamp}_{severity}.json` (metadata)
- Auto-generates `report_id` as `INC-{timestamp}-{primary_service}`
- Processing time: 15-25 seconds

---

### **8. `POST /api/v1/reports/weekly`**
**Purpose**: Generate weekly summary of all incidents  
**Input**:
```json
{
  "start_date": "2024-03-10T00:00:00Z",
  "end_date": "2024-03-17T00:00:00Z",
  "cleanup_after_report": false
}
```
**Output**:
```json
{
  "success": true,
  "report_content": "# Weekly Summary Report\n\n## Overview\n...",
  "start_date": "2024-03-10T00:00:00Z",
  "end_date": "2024-03-17T00:00:00Z",
  "incident_count": 5,
  "generated_at": "2024-03-17T10:00:00Z",
  "processing_time_seconds": 15.3
}
```
**Semantics**:
- Reads all incident JSON files from `reports/` directory
- Filters by date range (if provided)
- Calculates statistics:
  - Severity breakdown (CRITICAL/HIGH/MEDIUM/LOW counts)
  - Most affected services
  - Common root causes
- LLM generates executive summary
- Saves to `weekly_reports/weekly_{start}_{end}.md`
- Optional cleanup: Deletes incident reports after aggregation
- Processing time: 10-20 seconds

---

## **Type Inconsistencies & Bugs Found**

### **🐛 BUG #1: Missing Fields in InitRCA**
**Status**: ⚠️ **BLOCKING** - Latency RCA will crash  
**Fix Required**: Add `breach_time_utc: Optional[str]` and `breach_value: Optional[float]` to `InitRCA` class  
**Approval needed?** ✅

---

## **Summary**

The Agentic API provides:
1. **Dynamic query system** (`/build` + `/infer`) - Multi-agent SQL analysis
2. **Alert generation** (`/generate-alert`) - Structured alerting
3. **Pipeline summarization** (`/summarize`) - Natural language SLA explanations
4. **Root cause analysis** (`/rca`) - Automated incident investigation
5. **Report generation** (`/api/v1/reports/*`) - Markdown incident/weekly reports

**Critical bug found**: `InitRCA` missing fields for latency analysis. Shall I fix this?