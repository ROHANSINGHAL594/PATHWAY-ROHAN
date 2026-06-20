from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional, Annotated
from typing_extensions import TypedDict
from langchain.agents import create_agent
from datetime import datetime
from .tools import get_logs_in_time_window, get_error_spans_in_time_window
from ..sql_tool import TablePayload
from .output import RCAAnalysisOutput
from langgraph.graph import StateGraph, END
import operator
from ..llm_factory import create_analyser_model
from ..llm_config import LLMProvider

# Create the analyzer model instance
analyser_model = create_analyser_model()

# Downtime incident model
class DowntimeIncident(BaseModel):
    """Represents a single downtime incident"""
    trace_id: str = Field(description="Trace ID of the downtime incident")
    timestamp: int = Field(description="Unix timestamp in nanoseconds when downtime occurred")
    duration_ms: Optional[int] = Field(default=None, description="Duration of the downtime in milliseconds")

# Individual incident analysis prompt
individual_incident_prompt = """
You are an expert Site Reliability Engineer (SRE) analyzing a single downtime incident. Your task is to examine critical logs (severity >= 20) and error span status messages around one specific downtime event to identify what caused that particular service unavailability.

You will be provided with:
1. A single downtime incident with timestamp and trace_id
2. Critical logs from a time window around the incident (before and after)
3. Error span status messages with status_code >= 2 from the same time window

Log Format:
Each log entry follows:
(timestamp) (service_name or scope_name) [SEVERITY_LEVEL] Log body

Span Format:
Each span entry follows:
(timestamp) (service_name) Span: span_name | Status Code: status_code | Status Message: status_message

SEVERITY LEVELS (>= 20):
- 20: FATAL - System is unusable
- 21-24: FATAL+ - Critical system failures

Your Analysis Must Include:

1. ROOT_CAUSE: A concise summary of what caused this specific downtime incident (1-2 sentences)

2. SEVERITY: Assess the severity for this incident
   - "CRITICAL": Complete service unavailability, crash, or data loss
   - "HIGH": Significant degradation or partial unavailability
   - "MEDIUM": Brief or intermittent unavailability

3. AFFECTED_SERVICES: List of services that became unavailable in this incident

4. ROOT_CAUSE_SERVICE: The service where the problem originated (may be same as affected or a dependency)

6. NARRATIVE: Technical explanation of this incident (2-3 sentences) covering:
   - Sequence of events leading to unavailability
   - How the failure manifested
   - Whether it cascaded from dependencies

7. ERROR CITATIONS: Provide 2-3 critical log entries with:
   - timestamp: Human-readable timestamp from the log
   - service: Service name from the log entry
   - message: The actual log message text


ANALYSIS GUIDELINES:
- Focus on FATAL severity logs (severity >= 20) AND error span status messages
- Error span status messages often provide more structured error information than logs
- Look for: "service unavailable", "connection refused", "timeout", "crash", "panic", "failed"
- Distinguish between cause and effect in cascading failures
- Be specific to THIS incident only
- Cite actual log messages and span status messages as evidence
- Prioritize span status messages when available as they contain precise error conditions

IMPORTANT - INSUFFICIENT EVIDENCE HANDLING:
If you do NOT have sufficient evidence to analyze this incident (e.g., no critical logs, no error spans, no clear failure patterns), you MUST output an RCAAnalysisOutput with:
- severity: "LOW"
- affected_services: [] (empty list)
- narrative: "Insufficient evidence to perform root cause analysis for this downtime incident. No critical logs or error patterns found."
- error_citations: [] (empty list)
- root_cause: "Can't analyse - insufficient data"

DO NOT fabricate or speculate on the root cause when evidence is lacking. It is better to acknowledge insufficient data.
"""

aggregation_prompt = """
You are an expert Site Reliability Engineer (SRE) performing aggregated root cause analysis. You will receive individual RCA analyses of multiple downtime incidents that triggered an SLO breach.

Your task is to synthesize these individual analyses into a comprehensive root cause analysis following the RCAAnalysisOutput schema exactly.

Your Aggregated Analysis Must Include ALL Required Fields:

1. ROOT_CAUSE: A clear, concise summary of the systemic underlying issue causing the downtime (2-3 sentences)
   - Identify common patterns across incidents
   - Distinguish between systemic issues vs independent failures

2. SEVERITY: Overall severity assessment across all incidents
   - "CRITICAL": Complete service unavailability, data loss, major business impact
   - "HIGH": Significant degradation, partial unavailability affecting many users
   - "MEDIUM": Intermittent issues, some requests succeeded

3. AFFECTED_SERVICES: Array of ALL services impacted across all incidents
   - Include the top-level service that breached SLO
   - Include all intermediate services affected

4. NARRATIVE: A comprehensive technical explanation (4-6 sentences) that:
   - Explains the overall story of why the service experienced downtime
   - Connects related incidents showing progression or pattern
   - Describes cascading failures if applicable
   - Provides systemic context (infrastructure, application, or dependency issues)
   - Explains the impact on service availability

5. ERROR CITATIONS: Consolidate 2-5 most critical log citations from ALL incidents:
   - Ensure coverage across different incidents when possible
   - Prioritize evidence that supports the root cause
   - Include diverse evidence (initial trigger, cascading effects, final state)
   - Each citation must have: timestamp, service, message


ANALYSIS APPROACH:
- Synthesize patterns across incidents
- Be evidence-based using log citations
- Focus on systemic issues, not individual incidents
- Distinguish between related cascading failures and independent issues
- Provide actionable insights for prevention

IMPORTANT - INSUFFICIENT EVIDENCE HANDLING:
If the individual analyses do NOT provide sufficient evidence (e.g., most/all say "Can't analyse", no clear patterns, insufficient data), you MUST output an RCAAnalysisOutput with:
- severity: "LOW"
- affected_services: [] (empty list)
- narrative: "Insufficient evidence across incidents to perform meaningful root cause analysis. Individual incident analyses lacked clear error patterns or actionable data."
- error_citations: [] (empty list)
- root_cause: "Can't analyse - insufficient data across incidents"

DO NOT fabricate or speculate on systemic issues when the underlying data is insufficient. Acknowledge the limitation.
"""


# State for LangGraph
class DowntimeAnalysisState(TypedDict):
    incidents: List[DowntimeIncident]
    logs_table: TablePayload
    spans_table: TablePayload
    window_seconds: int
    individual_analyses: Annotated[List[RCAAnalysisOutput], operator.add]
    final_output: Optional[RCAAnalysisOutput]

individual_agent = None
aggregation_agent = None

def format_timestamp(unix_nano: int) -> str:
    """Convert Unix nanoseconds to readable timestamp"""
    if unix_nano == 0:
        return "unknown"
    timestamp_seconds = unix_nano / 1_000_000_000
    dt = datetime.fromtimestamp(timestamp_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def get_severity_text(severity_number: int) -> str:
    """Convert severity number to text"""
    if severity_number >= 21:
        return "FATAL+"
    elif severity_number == 20:
        return "FATAL"
    else:
        return f"SEVERITY_{severity_number}"

def format_incident_logs(incident: DowntimeIncident, logs: List[Dict]) -> str:
    """Format a single incident and its logs for analysis"""
    formatted_output = []
    
    formatted_output.append(
        f"DOWNTIME INCIDENT\n"
        f"Trace ID: {incident.trace_id}\n"
        f"Timestamp: {format_timestamp(incident.timestamp)}\n"
    )
    
    if incident.duration_ms:
        formatted_output.append(f"Duration: {incident.duration_ms}ms\n")
    
    formatted_output.append(f"\n{'='*80}\n")
    
    if not logs:
        formatted_output.append("No critical logs found in window\n")
        return "".join(formatted_output)
    
    # Sort logs by timestamp
    sorted_logs = sorted(logs, key=lambda x: x.get('observed_time_unix_nano', 0))
    
    formatted_output.append(f"Critical Logs (window around downtime):\n\n")
    for log in sorted_logs:
        timestamp = format_timestamp(log.get('observed_time_unix_nano', 0))
        service = log.get('_open_tel_service_name') or log.get('scope_name', 'unknown')
        severity_num = log.get('severity_number', 0)
        severity = get_severity_text(severity_num)
        body = log.get('body', '')
        
        
        formatted_output.append(f"({timestamp}) ({service}) [{severity}] {body}\n")
    
    return "".join(formatted_output)

def format_error_spans(spans: List[Dict]) -> str:
    """Format error spans with status messages for analysis"""
    if not spans:
        return "No error spans found in window"
    
    formatted_output = []
    formatted_output.append("Error Span Status Messages (status_code >= 2):\n\n")
    
    # Sort spans by timestamp
    sorted_spans = sorted(spans, key=lambda x: x.get('start_time_unix_nano', 0))
    
    for span in sorted_spans:
        timestamp = format_timestamp(span.get('start_time_unix_nano', 0))
        service = span.get('_open_tel_service_name', 'unknown')
        span_name = span.get('name', 'unknown')
        status_code = span.get('status_code', 0)
        status_message = span.get('status_message', 'No message')
        
        formatted_output.append(
            f"({timestamp}) ({service}) Span: {span_name} | "
            f"Status Code: {status_code} | Status Message: {status_message}\n"
        )
    
    return "".join(formatted_output)

async def init_agents():
    """Initialize both agents"""
    global individual_agent, aggregation_agent
    
    if individual_agent is None:
        individual_agent = create_agent(
            model=analyser_model,
            tools=[],
            system_prompt=individual_incident_prompt,
            response_format=RCAAnalysisOutput
        )
    
    if aggregation_agent is None:
        aggregation_agent = create_agent(
            model=analyser_model,
            tools=[],
            system_prompt=aggregation_prompt,
            response_format=RCAAnalysisOutput
        )

async def analyze_single_incident(
    incident: DowntimeIncident,
    logs_table: TablePayload,
    spans_table: TablePayload,
    window_seconds: int
) -> RCAAnalysisOutput:
    """Analyze a single downtime incident"""
    if individual_agent is None:
        await init_agents()
    
    # Define time window (convert to nanoseconds)
    start_time = incident.timestamp - (window_seconds * 1_000_000_000)
    end_time = incident.timestamp + (window_seconds * 1_000_000_000)
    
    # Fetch critical logs (severity >= 20) in this window
    logs = await get_logs_in_time_window(
        start_time=start_time,
        end_time=end_time,
        logs_table=logs_table,
        min_severity=20
    )
    
    # Fetch error spans (status_code >= 2) in this window
    error_spans = await get_error_spans_in_time_window(
        start_time=start_time,
        end_time=end_time,
        spans_table=spans_table,
        min_status_code=2
    )
    
    # Format logs and spans for analysis
    formatted_logs = format_incident_logs(incident, logs)
    formatted_spans = format_error_spans(error_spans)

    analysis_prompt = (
        f"Analyze this specific downtime incident:\n\n"
        f"{formatted_logs}\n\n"
        f"{formatted_spans}\n\n"
    )
    
    result = await individual_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ]
        }
    )
    
    analysis: RCAAnalysisOutput = result["structured_response"]
    
    return analysis

async def analyze_incidents_node(state: DowntimeAnalysisState) -> Dict:
    """Node that analyzes all incidents in parallel"""
    incidents = state["incidents"][:5]  # Limit to 5 incidents
    logs_table = state["logs_table"]
    spans_table = state["spans_table"]
    window_seconds = state["window_seconds"]
    
    # Analyze each incident (LangGraph will handle parallel execution)
    import asyncio
    analyses = await asyncio.gather(*[
        analyze_single_incident(incident, logs_table, spans_table, window_seconds)
        for incident in incidents
    ])
    
    return {"individual_analyses": analyses}

async def aggregate_analyses_node(state: DowntimeAnalysisState) -> Dict:
    """Node that aggregates all individual analyses"""
    if aggregation_agent is None:
        await init_agents()
    
    individual_analyses = state["individual_analyses"]
    
    # Format individual analyses for aggregation
    analyses_text = []
    for idx, analysis in enumerate(individual_analyses, 1):
        analyses_text.append(
            f"\n{'='*80}\n"
            f"INCIDENT #{idx} ANALYSIS\n"
            f"Root Cause: {analysis.root_cause}\n"
            f"Severity: {analysis.severity}\n"
            f"Affected Services: {', '.join(analysis.affected_services)}\n"
            f"Narrative: {analysis.narrative}\n"
            f"Evidence (Citations):\n"
        )
        
        for citation in analysis.error_citations:
            analyses_text.append(
                f"  - ({citation.timestamp}) {citation.service}: {citation.message}\n"
            )
    
    formatted_analyses = "".join(analyses_text)
    
    aggregation_prompt_text = (
        f"You have received {len(individual_analyses)} individual downtime incident RCA analyses. "
        f"Synthesize these into a comprehensive aggregated root cause analysis following the given schema.\n\n"
        f"{formatted_analyses}\n\n"
        f"Provide an aggregated analysis with ALL required fields:\n"
        f"- root_cause: Systemic issue summary across all incidents (2-3 sentences)\n"
        f"- severity: Overall severity (CRITICAL/HIGH/MEDIUM/LOW)\n"
        f"- affected_services: All services impacted across all incidents\n"
        f"- narrative: Comprehensive technical explanation (4-6 sentences)\n"
        f"- error_citations: 3-7 most critical log citations from all incidents\n"
    )
    
    result = await aggregation_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": aggregation_prompt_text
                }
            ]
        }
    )
    
    output: RCAAnalysisOutput = result["structured_response"]
    
    return {"final_output": output}

# Build LangGraph workflow
def build_downtime_analysis_graph():
    """Build the LangGraph workflow for downtime analysis"""
    workflow = StateGraph(DowntimeAnalysisState)
    
    # Add nodes
    workflow.add_node("analyze_incidents", analyze_incidents_node)
    workflow.add_node("aggregate_analyses", aggregate_analyses_node)
    
    # Define edges
    workflow.set_entry_point("analyze_incidents")
    workflow.add_edge("analyze_incidents", "aggregate_analyses")
    workflow.add_edge("aggregate_analyses", END)
    
    return workflow.compile()

downtime_graph = None

async def analyze_downtime_incidents(
    incidents: List[DowntimeIncident],
    logs_table: TablePayload,
    spans_table: TablePayload,
    window_seconds: int = 30
) -> RCAAnalysisOutput:
    """
    Analyze downtime incidents using parallel execution for individual analyses.
    
    Args:
        incidents: List of downtime incidents with trace_ids and timestamps
        logs_table: TablePayload for logs table
        spans_table: TablePayload for spans table
        window_seconds: Time window in seconds to look before/after each incident (default 30s)
        
    Returns:
        RCAAnalysisOutput with aggregated root cause analysis
    """
    global downtime_graph
    
    if downtime_graph is None:
        await init_agents()
        downtime_graph = build_downtime_analysis_graph()
    
    # Limit to 5 incidents max
    incidents = incidents[:5]
    
    # Run the graph
    initial_state: DowntimeAnalysisState = {
        "incidents": incidents,
        "logs_table": logs_table,
        "spans_table": spans_table,
        "window_seconds": window_seconds,
        "individual_analyses": [],
        "final_output": None
    }
    
    final_state = await downtime_graph.ainvoke(initial_state)
    
    return final_state["final_output"]
