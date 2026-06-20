import json
import os
from dotenv import load_dotenv
from typing import List, Annotated, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from .tools import get_top_latency_traces, get_full_span_tree, get_logs_for_trace_ids, get_error_spans_for_trace_ids, TablePayload
from .output import RCAAnalysisOutput
from datetime import datetime, timedelta
import asyncio
from ..llm_factory import create_analyser_model
from ..llm_config import LLMProvider

load_dotenv()

# Create the analyzer model instance
analyser_model = create_analyser_model()


# We will run one subgraph per each trace id for the top 5 slowest traces which will take this state
class SLAAlert(TypedDict):
    trace_id: str
    parent_span: Optional[Dict]
    has_error: bool
    error_span: Optional[str]
    error_message: Optional[str]
    hypothesis: Optional[str]
    logs: Optional[List[Dict]]
    error_spans: Optional[List[Dict]]
    topology: Optional[List[Dict]]
    validation_result: Optional[str]
    retries: int
    messages: Annotated[list, add_messages]


class MetricAlert(BaseModel):
    metric_description: str = Field(description="The description of the metric that breached the threshold")
    breach_time_utc: str = Field(description="The UTC timestamp when the breach occurred.")
    breach_value: float = Field(description="The value of the metric that caused the breach.")


class RCAState(TypedDict):
    metric_alert: MetricAlert
    sla_alerts: List[SLAAlert]
    messages: Annotated[list, add_messages]
    final_reports: Optional[List[Dict]]
    analysis_summary: Optional[Dict]
    rca_output: Optional[RCAAnalysisOutput]
    table_data: Optional[Dict]  # Contains spans and logs table info




def format_logs(logs: List[Dict]) -> str:
    """Format logs into a readable string for LLM context."""
    if not logs:
        return "No logs available."
    
    formatted = []
    for log in logs:
        timestamp = log.get('observed_time_unix_nano', 'N/A')
        service = log.get('_open_tel_service_name', 'Unknown')
        severity = log.get('severity_text', log.get('severity_number', 'INFO'))
        body = log.get('body', '')
        
        formatted.append(
            f"[{timestamp}] [{service}] [{severity}] {body}"
        )
    
    return "\n".join(formatted)


def format_topology(topology: List[Dict]) -> str:
    """Format span tree topology into a readable hierarchical structure."""
    if not topology:
        return "No topology available."
    
    formatted = []
    for span in topology:
        indent = "  " * span.get('depth', 0)
        name = span.get('name', 'Unknown')
        duration_ns = span.get('end_time_unix_nano', 0) - span.get('start_time_unix_nano', 0)
        duration_ms = duration_ns / 1_000_000
        status = span.get('status_code', 'OK')
        service = span.get('_open_tel_service_name', 'Unknown')
        
        formatted.append(
            f"{indent}├─ {name} ({service}) - {duration_ms:.2f}ms [{status}]"
        )
    
    return "\n".join(formatted)


def format_error_spans(error_spans: List[Dict]) -> str:
    """Format error spans with status messages for analysis."""
    if not error_spans:
        return "No error spans available."
    
    formatted = []
    for span in error_spans:
        timestamp = span.get('start_time_unix_nano', 0)
        service = span.get('_open_tel_service_name', 'Unknown')
        span_name = span.get('name', 'Unknown')
        status_code = span.get('status_code', 'unknown')
        status_message = span.get('status_message', '')
        
        # Convert timestamp to readable format
        if timestamp > 0:
            dt = datetime.fromtimestamp(timestamp / 1_000_000_000)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        else:
            timestamp_str = "unknown"
        
        formatted.append(
            f"[{timestamp_str}] ({service}) Span: {span_name} | "
            f"Status Code: {status_code} | Status Message: {status_message}"
        )
    
    return "\n".join(formatted)


async def enrichment_node(state: RCAState) -> Dict:
    """
    Takes a metric alert, finds the top N slowest traces associated with it,
    and creates the initial SLAAlerts for the parallel analysis.
    """
    metric_alert = state["metric_alert"]
    
    breach_time = datetime.fromisoformat(metric_alert.breach_time_utc.replace('Z', '+00:00'))
    start_time = (breach_time - timedelta(minutes=5)).isoformat()
    end_time = (breach_time + timedelta(minutes=5)).isoformat()

    # Get table information from state
    table_data = state.get("table_data", {})
    spans_table = table_data.get("spans", TablePayload(table_name=state["table_data"]["spans"]))
    logs_table = table_data.get("logs", TablePayload(table_name=state["table_data"]["logs"]))

    top_traces = await get_top_latency_traces(
        start_time_utc=start_time,
        end_time_utc=end_time,
        spans_table=spans_table,
        limit=5
    )

    if not top_traces:
        return {"sla_alerts": []}
    
    sla_alerts = []
    for trace in top_traces:
        trace_id = trace['trace_id']
        
        # Extract full span tree for trace
        full_span_tree = await get_full_span_tree(trace_id, spans_table)
        
        # Extract parent span (root span with no parent)
        parent_span = None
        if full_span_tree:
            parent_span = next(
                (span for span in full_span_tree 
                 if not span.get('_open_tel_parent_span_id') or 
                 span.get('_open_tel_parent_span_id') == ''),
                None
            )
        
        # Get error logs for the trace
        error_logs = await get_logs_for_trace_ids(
            trace_ids=[trace_id],
            logs_table=logs_table,
            severity_number=13  # ERROR level
        )
        
        # Get error spans with status_code >= 2
        error_spans = await get_error_spans_for_trace_ids(
            trace_ids=[trace_id],
            spans_table=spans_table,
            min_status_code=2
        )
        
        alert: SLAAlert = {
            "parent_span": parent_span,
            "trace_id": trace_id,
            "has_error": bool(trace.get('has_error')),
            "error_span": trace.get('error_span'),
            "error_message": trace.get('error_message'),
            "topology": full_span_tree,
            "logs": error_logs,
            "error_spans": error_spans,
            "hypothesis": None,
            "validation_result": None,
            "retries": 0,
            "messages": []
        }
        sla_alerts.append(alert)

    return {"sla_alerts": sla_alerts}

async def analysis_agent_node(state: SLAAlert) -> Dict:
    """
    Analyzes a single trace to form a hypothesis about the root cause.
    """
    log_context = format_logs(state.get("logs", []))
    topology_context = format_topology(state.get("topology", []))
    error_spans_context = format_error_spans(state.get("error_spans", []))

    error_context = ""
    if state.get("has_error"):
        error_msg = state.get('error_message', 'No message')

        error_context = f"""
    **Error Information:**
    - Error Span: {state.get('error_span', 'Unknown')}
    - Error Message: {error_msg}
        """

    prompt = f"""
You are an expert SRE debugging a slow or failed workflow on a low-code platform.
Your task is to identify the root cause of an SLA breach.

**Workflow Context:**
- Trace ID: {state["trace_id"]}
- Has Error: {state.get("has_error", False)}

{error_context}

**Topology (Span Tree):**
{topology_context}

**Error Span Status Messages:**
{error_spans_context}

**Error Logs:**
{log_context}

**Previous Analysis:**
{state.get('validation_result', 'This is the first analysis attempt.')}

**Your Goal:**
1. Analyze the topology to identify which span(s) contributed most to latency
2. Review error span status messages for structured error information
3. Review error logs and error information if present
4. Form a `hypothesis` about the root cause. Consider:
   - System Latency (slow service/infrastructure)
   - Data Volume (large data processing causing slowness)
   - Error Condition (specific errors causing failures from span status messages)
   - External Dependencies (third-party services, databases)
   - Resource Contention (CPU, memory, network issues)

Note: Error span status messages provide structured error information that is often more precise than logs.

If your previous hypothesis was wrong, formulate a NEW hypothesis based on the evidence.

**IMPORTANT - INSUFFICIENT EVIDENCE:**
If you do NOT have sufficient evidence (e.g., empty topology, no logs, no clear latency patterns), output:
{{
    "hypothesis": "Can't analyse - insufficient data to determine root cause"
}}
DO NOT fabricate or speculate without clear evidence.

**Response Format (MUST be a single JSON object):**
{{
    "hypothesis": "Your concise hypothesis here. Be specific about which component/span and why."
}}
"""
    
    messages = state.get("messages", []) + [{"role": "user", "content": prompt}]
    
    response = await analyser_model.ainvoke(messages)
    content = response.content
    
    try:
        llm_response = json.loads(content)
    except json.JSONDecodeError:
        # If response is not valid JSON, wrap it
        llm_response = {"hypothesis": content}
    
    new_messages = messages + [{"role": "assistant", "content": content}]
    
    return {
        "hypothesis": llm_response.get("hypothesis"),
        "messages": new_messages,
        "retries": state.get("retries", 0)
    }


async def validate_hypothesis_with_llm(state: SLAAlert) -> Dict:
    """
    Uses an LLM to determine if the hypothesis is well-supported by evidence.
    """
    logs_text = format_logs(state.get("logs", []))
    topology_text = format_topology(state.get("topology", []))
    error_spans_text = format_error_spans(state.get("error_spans", []))

    prompt = f"""
You are a validation agent. Determine if the hypothesis is well-supported by the evidence.

**Hypothesis:**
{state["hypothesis"]}

**Evidence:**
- Trace ID: {state["trace_id"]}
- Has Error: {state.get("has_error", False)}
- Error Span: {state.get("error_span", "None")}
- Error Message: {state.get("error_message", "None")}

**Topology:**
{topology_text}

**Error Span Status Messages:**
{error_spans_text}

**Logs:**
{logs_text}

**Question:**
Does the evidence clearly support and confirm the hypothesis? Consider:
- Does the hypothesis match the observed latency patterns in the topology?
- If there's an error, does the hypothesis explain it based on span status messages or logs?
- Is the hypothesis specific enough to be actionable?
- Does the hypothesis reference information that's actually present in the evidence?

**Your Answer (MUST be a single JSON object):**
{{
    "confirmed": true,
    "reasoning": "Brief explanation"
}}
OR
{{
    "confirmed": false,
    "reasoning": "Brief explanation of what's missing or incorrect"
}}
"""
    
    try:
        response = await analyser_model.ainvoke([{"role": "user", "content": prompt}])
        content = response.content
        llm_response = json.loads(content)
        
        validation_result = llm_response.get("reasoning", "")
        confirmed = llm_response.get("confirmed", False)
        
        return {
            "validation_result": validation_result,
            "confirmed": confirmed,
            "retries": state.get("retries", 0) + 1
        }
    except Exception as e:
        return {
            "validation_result": f"Validation failed: {str(e)}",
            "confirmed": False,
            "retries": state.get("retries", 0) + 1
        }


async def analyze_single_trace(alert: SLAAlert) -> SLAAlert:
    """
    Runs the analysis loop for a single trace with retry logic.
    """
    max_retries = 2
    current_state = alert
    
    for retry in range(max_retries + 1):
        # Analysis step
        analysis_result = await analysis_agent_node(current_state)
        current_state.update(analysis_result)
        
        # Validation step
        validation_result = await validate_hypothesis_with_llm(current_state)
        current_state.update(validation_result)
        
        # Check if hypothesis is confirmed
        if validation_result.get("confirmed"):
            break
    
    return current_state


async def parallel_analysis_node(state: RCAState) -> Dict:
    """
    Runs analysis for all SLA alerts in parallel using asyncio.gather.
    """
    sla_alerts = state.get("sla_alerts", [])
    
    if not sla_alerts:
        return {"final_reports": []}
    
    # Run all trace analyses in parallel
    analyzed_alerts = await asyncio.gather(
        *[analyze_single_trace(alert) for alert in sla_alerts],
        return_exceptions=True
    )
    
    # Filter out any exceptions and collect results
    final_reports = []
    for result in analyzed_alerts:
        if isinstance(result, Exception):
            print(f"Error analyzing trace: {result}")
            continue
        final_reports.append({
            "trace_id": result.get("trace_id"),
            "hypothesis": result.get("hypothesis"),
            "has_error": result.get("has_error"),
            "error_span": result.get("error_span"),
            "validation_result": result.get("validation_result")
        })
    
    return {"final_reports": final_reports}


def build_graph() -> StateGraph:
    """
    Builds the main RCA workflow graph with parallel trace analysis.
    """
    workflow = StateGraph(RCAState)
    
    workflow.add_node("enrichment", enrichment_node)
    workflow.add_node("parallel_analysis", parallel_analysis_node)
    workflow.add_node("gather", gather_node)
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("enrichment")
    workflow.add_edge("enrichment", "parallel_analysis")
    workflow.add_edge("parallel_analysis", "gather")
    workflow.add_edge("gather", "synthesis")
    workflow.add_edge("synthesis", END)

    return workflow.compile()


def gather_node(state: RCAState) -> Dict:
    """
    Gathers and summarizes the results from parallel trace analyses.
    """
    final_reports = state.get("final_reports", [])
    
    summary = {
        "total_traces_analyzed": len(final_reports),
        "traces_with_errors": sum(1 for r in final_reports if r.get("has_error")),
        "reports": final_reports,
        "metric_alert": state.get("metric_alert")
    }
    
    return {"analysis_summary": summary}


async def synthesis_node(state: RCAState) -> Dict:
    """
    Synthesizes all findings using LLM to produce final RCA output.
    """
    analysis_summary = state.get("analysis_summary", {})
    final_reports = analysis_summary.get("reports", [])
    metric_alert = analysis_summary.get("metric_alert")
    sla_alerts = state.get("sla_alerts", [])
    
    # Prepare context for LLM with detailed trace information
    reports_text = "\n\n".join([
        f"**Trace {i+1} (ID: {r.get('trace_id')}):**\n"
        f"- Has Error: {r.get('has_error')}\n"
        f"- Error Span: {r.get('error_span', 'N/A')}\n"
        f"- Hypothesis: {r.get('hypothesis')}\n"
        f"- Validation: {r.get('validation_result')}"
        for i, r in enumerate(final_reports)
    ])
    
    # Collect error logs from all SLA alerts for citations
    all_error_logs = []
    for alert in sla_alerts:
        logs = alert.get("logs", [])
        if logs:
            all_error_logs.extend(logs[:3])  # Take first 3 from each trace
    
    error_logs_context = format_logs(all_error_logs[:10])  # Limit to 10 total
    
    prompt = f"""
You are a senior SRE synthesizing root cause analysis findings.

**Metric Alert Context:**
- Metric: {metric_alert.metric_description if metric_alert else 'Unknown'}
- Breach Time: {metric_alert.breach_time_utc if metric_alert else 'Unknown'}
- Breach Value: {metric_alert.breach_value if metric_alert else 'Unknown'}

**Individual Trace Analyses:**
{reports_text}

**Available Error Logs for Citations:**
{error_logs_context}

**Your Task:**
Correlate and synthesize these findings to produce a comprehensive root cause analysis:

1. Determine severity (CRITICAL/HIGH/MEDIUM/LOW) based on impact
2. List affected services (primary service first)
3. Write a clear narrative explaining what happened (max 5 sentences)
4. Select 2-5 specific error log entries as citations
5. Provide a technical root cause that is specific and actionable

**IMPORTANT - INSUFFICIENT EVIDENCE:**
If the individual trace analyses indicate "Can't analyse" or there is insufficient evidence across traces, you MUST output:
{{
    "severity": "MEDIUM",
    "affected_services": [],
    "narrative": "Can't analyse - insufficient data across all traces to determine root cause",
    "error_citations": [],
    "root_cause": "Can't analyse"
}}
DO NOT fabricate or speculate when evidence is insufficient.

**Response Format (MUST be valid JSON matching this structure exactly):**
{{
    "severity": "CRITICAL",
    "affected_services": ["primary-service", "secondary-service"],
    "narrative": "Clear explanation of what happened and why in 3-5 sentences.",
    "error_citations": [
        {{
            "timestamp": "2024-01-15T10:30:00Z",
            "service": "service-name",
            "message": "Relevant error message from logs"
        }},
        {{
            "timestamp": "2024-01-15T10:30:05Z",
            "service": "another-service",
            "message": "Another relevant error message"
        }}
    ],
    "root_cause": "Specific technical root cause with actionable details"
}}
"""
    
    try:
        response = await analyser_model.ainvoke([{"role": "user", "content": prompt}])
        content = response.content
        
        # Parse LLM response
        llm_response = json.loads(content)
        
        # Extract error citations
        error_citations = []
        for citation in llm_response.get("error_citations", [])[:5]:
            error_citations.append({
                "timestamp": citation.get("timestamp", ""),
                "service": citation.get("service", "Unknown"),
                "message": citation.get("message", "")
            })
        
        # Ensure we have at least 2 citations
        if len(error_citations) < 2 and all_error_logs:
            # Fallback: create citations from actual logs
            for log in all_error_logs[:2]:
                error_citations.append({
                    "timestamp": str(log.get("observed_time_unix_nano", "")),
                    "service": log.get("_open_tel_service_name", "Unknown"),
                    "message": log.get("body", "No message available")
                })
        
        # Create RCAAnalysisOutput
        rca_output = RCAAnalysisOutput(
            severity=llm_response.get("severity", "MEDIUM"),
            affected_services=llm_response.get("affected_services", ["Unknown"]),
            narrative=llm_response.get("narrative", "Unable to determine detailed narrative."),
            error_citations=error_citations,
            root_cause=llm_response.get("root_cause", "Root cause could not be determined from available evidence.")
        )
        
        return {"rca_output": rca_output}
        
    except Exception as e:
        # Fallback output in case of error
        fallback_citations = []
        for log in all_error_logs[:2]:
            fallback_citations.append({
                "timestamp": str(log.get("observed_time_unix_nano", "N/A")),
                "service": log.get("_open_tel_service_name", "Unknown"),
                "message": log.get("body", "Error log not available")
            })
        
        if len(fallback_citations) < 2:
            fallback_citations.extend([
                {"timestamp": "N/A", "service": "Unknown", "message": "Insufficient error data"},
                {"timestamp": "N/A", "service": "Unknown", "message": "Analysis incomplete"}
            ])
        
        rca_output = RCAAnalysisOutput(
            severity="HIGH",
            affected_services=["Unknown"],
            narrative=f"Analysis failed due to error: {str(e)}. Manual investigation required.",
            error_citations=fallback_citations,
            root_cause=f"Unable to complete automated analysis: {str(e)}"
        )
        return {"rca_output": rca_output}
