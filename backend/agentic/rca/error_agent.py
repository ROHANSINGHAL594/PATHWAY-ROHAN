from typing import List, Dict
from langchain_core.messages import HumanMessage, SystemMessage
from .output import RCAAnalysisOutput
from datetime import datetime
from ..llm_factory import create_analyser_model
from .rca_logger import rca_logger
from ..llm_config import LLMProvider

# Create the analyzer model instance
analyser_model = create_analyser_model()

error_analysis_prompt = """
You are an expert Site Reliability Engineer (SRE) and system diagnostics specialist. Your task is to analyze error logs and span status messages from distributed systems to identify root causes of failures that triggered SLA threshold violations.

You will be provided with:
1. ERROR LOGS: Error logs grouped by trace_id, where each trace represents a request flow through the system
2. ERROR SPAN STATUS MESSAGES: Status messages from spans with error status codes (status_code >= 2)

The logs and spans are ordered chronologically within each trace, and traces themselves are ordered by time.

Log Format:
Each log entry follows this format:
(timestamp) (service_name or scope_name) Log body

Span Format:
Each span entry follows this format:
(timestamp) (service_name) Span: span_name | Status Code: status_code | Status Message: status_message

Your Analysis Must:

1. IDENTIFY PATTERNS: Look for common error patterns across traces
   - Recurring error messages in both logs and span status messages
   - Specific services that consistently fail
   - Temporal patterns (e.g., cascading failures)
   - Error propagation through the service chain
   - Correlation between span errors and log entries

2. DETERMINE SEVERITY: Assess the impact level
   - CRITICAL: System-wide outage, data loss, security breach
   - HIGH: Multiple services affected, user-facing errors
   - MEDIUM: Isolated service issues, degraded performance
   - LOW: Minor issues, self-recovering errors

3. IDENTIFY AFFECTED SERVICES: List all services involved
   - Primary affected service (where the root cause originates)
   - Secondary affected services (cascade effects)
   - Include service names and their roles

4. CONSTRUCT NARRATIVE: Provide a clear, concise explanation
   - What happened (the failure mode)
   - Why it happened (the root cause)
   - How it propagated (if applicable)
   - Impact on system behavior
   - Keep it under 5 sentences, technical but accessible

5. CITE EVIDENCE: Reference specific log entries and span status messages
   - Quote relevant error messages from both logs and spans
   - Include timestamps and services
   - Show the progression of the failure
   - Minimum 2-3 citations, maximum 5
   - Prioritize span status messages as they often contain structured error information

6. DETERMINE ROOT CAUSE: Identify the underlying issue
   - Technical root cause (e.g., "Database connection pool exhaustion")
   - Contributing factors if applicable
   - Distinguish between symptoms and root causes
   - Use span status messages to identify specific error conditions

ANALYSIS GUIDELINES:
- Focus on actionable insights, not just description
- Distinguish between root causes and symptoms
- Consider cascading failures and dependencies
- Look for common error codes, exceptions, or patterns in both logs and spans
- Pay attention to the first occurrence of errors in each trace
- Consider resource exhaustion, timeouts, network issues, data corruption
- Be precise and evidence-based
- Span status messages often provide more structured error information than logs

IMPORTANT - INSUFFICIENT EVIDENCE HANDLING:
If you do NOT have sufficient evidence to perform a meaningful analysis (e.g., empty logs, no error messages, unclear patterns), you MUST output an RCAAnalysisOutput with:
- severity: "LOW"
- affected_services: [] (empty list)
- narrative: "Insufficient evidence to perform root cause analysis. No clear error patterns or messages found in the provided logs and spans."
- error_citations: [] (empty list)
- root_cause: "Can't analyse - insufficient data"

DO NOT fabricate or speculate on analysis when evidence is lacking. It is better to acknowledge insufficient data than to provide misleading analysis.

Output a structured response with all required fields.
"""





structured_analyser_model = None

def format_timestamp(unix_nano: int) -> str:
    """Convert Unix nanoseconds to readable timestamp"""
    if unix_nano == 0:
        return "unknown"
    timestamp_seconds = unix_nano / 1_000_000_000
    dt = datetime.fromtimestamp(timestamp_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def format_error_spans_for_analysis(spans_by_trace: Dict[str, List[Dict]]) -> str:
    """
    Format error spans with status messages grouped by trace for analysis.
    
    Args:
        spans_by_trace: Dictionary mapping trace_id to list of span dictionaries
        
    Returns:
        Formatted string with error spans ordered by trace and timestamp
    """
    formatted_output = []
    
    # Sort traces by earliest span timestamp
    sorted_traces = sorted(
        spans_by_trace.items(),
        key=lambda x: min(span.get('start_time_unix_nano', 0) for span in x[1])
    )
    
    for trace_id, spans in sorted_traces:
        formatted_output.append(f"\n=== ERROR SPANS FOR TRACE: {trace_id} ===\n")
        
        for span in spans:
            timestamp = format_timestamp(span.get('start_time_unix_nano', 0))
            service = span.get('_open_tel_service_name') or span.get('scope_name', 'unknown')
            span_name = span.get('name', 'unknown')
            status_code = span.get('status_code', 'unknown')
            status_message = span.get('status_message', '')
            
            formatted_output.append(
                f"({timestamp}) ({service}) Span: {span_name} | "
                f"Status Code: {status_code} | Status Message: {status_message}"
            )
        
        formatted_output.append("")  # Empty line between traces
    
    return "\n".join(formatted_output)

def format_logs_for_analysis(logs_by_trace: Dict[str, List[Dict]]) -> str:
    """
    Format logs grouped by trace for analysis.
    
    Args:
        logs_by_trace: Dictionary mapping trace_id to list of log dictionaries
        
    Returns:
        Formatted string with logs ordered by trace and timestamp
    """
    formatted_output = []
    
    # Sort traces by earliest log timestamp
    sorted_traces = sorted(
        logs_by_trace.items(),
        key=lambda x: min(log.get('observed_time_unix_nano', 0) for log in x[1])
    )
    
    for trace_id, logs in sorted_traces:
        formatted_output.append(f"\n=== TRACE: {trace_id} ===\n")
        
        
        for log in logs:
            timestamp = format_timestamp(log.get('observed_time_unix_nano', 0))
            service = log.get('_open_tel_service_name') or log.get('scope_name', 'unknown')
            body = log.get('body', '')
            
            formatted_output.append(f"({timestamp}) ({service}) {body}")
        
        formatted_output.append("")  # Empty line between traces
    
    return "\n".join(formatted_output)

async def init_error_analysis_agent():
    """Initialize the error analysis model with structured output"""
    global structured_analyser_model
    # Use direct structured output instead of agent framework for simpler, more reliable parsing
    structured_analyser_model = analyser_model.with_structured_output(RCAAnalysisOutput)

async def analyze_error_logs(logs_by_trace: Dict[str, List[Dict]], error_spans_by_trace: Dict[str, List[Dict]] = None, skip_injection_scan: bool = True) -> RCAAnalysisOutput:
    """
    Analyze error logs and error span status messages to identify root causes of failures.
    
    Args:
        logs_by_trace: Dictionary mapping trace_id to list of log dictionaries
        error_spans_by_trace: Dictionary mapping trace_id to list of error span dictionaries (optional)
        skip_injection_scan: If True, skip prompt injection scanning (use for trusted internal log data)
        
    Returns:
        RCAAnalysisOutput with structured analysis
    """
    if structured_analyser_model is None:
        await init_error_analysis_agent()

    # Format logs for analysis
    formatted_logs = format_logs_for_analysis(logs_by_trace)
    
    # Format error spans if provided
    formatted_spans = ""
    if error_spans_by_trace:
        formatted_spans = format_error_spans_for_analysis(error_spans_by_trace)

    # Build analysis prompt with both logs and spans
    analysis_prompt_parts = [
        "Analyze the following error logs from traces that triggered an SLA threshold violation:\n\n",
        "ERROR LOGS:\n",
        f"{formatted_logs}\n\n"
    ]
    
    if formatted_spans:
        analysis_prompt_parts.extend([
            "ERROR SPAN STATUS MESSAGES:\n",
            f"{formatted_spans}\n\n"
        ])
    
    analysis_prompt_parts.append(
        "Provide a structured analysis identifying the root cause, severity, affected services, "
        "a clear narrative, and cite specific log entries and span status messages as evidence."
    )
    
    analysis_prompt = "".join(analysis_prompt_parts)
    
    # Use direct LLM call with structured output - simpler and more reliable than agent framework
    result = await structured_analyser_model.ainvoke([
        SystemMessage(content=error_analysis_prompt),
        HumanMessage(content=analysis_prompt)
    ])
    
    return result
