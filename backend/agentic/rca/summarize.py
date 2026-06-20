from pydantic import BaseModel
from typing import List, Dict, Union, Literal
from .cache import get_cached_response, cache_response, init_cache_db
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
import os
from ..llm_factory import create_summarization_model
from ..llm_config import LLMProvider

reasoning_model = create_summarization_model()
summarize_prompt = """
You are a domain-expert telemetry analyst and technical summarizer. Your task is to interpret SLA-metric pipelines— and produce a clear, technically accurate natural-language summary of what each final special column (defined below) in the resulting metric table represents.
A special column is a column which contains _open_tel_trace_id somewhere in its name.
Basically, columns containing OpenTelemetry trace identifiers have _open_tel_trace_id in their name and are considered special.

A pipeline is a numbered list of nodes, where:

- Each node performs a transformation on telemetry data (for example: OpenTelemetry ingestion (spans or logs or metrics), filter, join, group-by, window, aggregation, etc.).

- Nodes reference prior nodes by index (e.g., “Filters input $3” or “Joins $1 with $2”).

- The final node corresponds to the SLA metric table whose columns you must describe.

### Naming convention of columns after transformations are applied:

1) When a join node is applied, all columns other than the ones on which the join is applied are prefixed with _pw_left_ or _pw_right_ depending on which side they come from. For the columns on which the join is applied
    - Case a) If the columns on which the join is applied have the same name, only one column with that name is passed on
    - Case b) Otherwise both are prefixed with their respective prefixes
2) For group-by or window by operations (special columns are always reduced to an array (preserving order) and renamed to _pw_grouped_ or _pw_windowed_ respectively) unless the group by is performed ON them
      


A trace identifier refers to one of possibly several related trace ID columns in the final metric that together indicate how different telemetry sources or event streams contribute to the derived SLA metric.

The semantic origin of a trace identifier is the last node in the pipeline after which its meaning no longer changes—beyond that point, it continues to represent the same underlying telemetry entities or events through all subsequent transformations.

You will be provided with:

The SLA metric description, describing the monitored condition.

The pipeline description, listing all nodes and their transformations.

The semantic origins of each trace identifier, marking where their meanings stabilize.
"""

class SummarizeOutput(BaseModel):
    special_column_descriptions: Dict[str,str]
    metric_calculation_explanation: str
    metric_type: Literal["error", "uptime", "latency"]
    metric_calculation_window: int
    metric_column: str

class SummarizeRequest(BaseModel):
    metric_description: str
    pipeline_description: str
    semantic_origins: Dict[str, List[int]]

mcp_client = MultiServerMCPClient({
    "context7": {
        "transport": "streamable_http",
        "url": "https://mcp.context7.com/mcp",
        "headers": {"CONTEXT7_API_KEY": os.environ.get("CONTEXT7_API_KEY", "")},
    }
})

summarize_agent = None


async def init_summarize_agent():
    global summarize_agent
    init_cache_db()
    tools =  await mcp_client.get_tools()
    summarize_agent = create_agent(
        model=reasoning_model,
        tools=tools,
        system_prompt=summarize_prompt,
        response_format=SummarizeOutput
    )


async def summarize(request: SummarizeRequest):
    """
    Generate natural language descriptions for special columns in SLA metric tables.
    """
    if summarize_agent is None:
        await init_summarize_agent()
    
    # Format semantic origins for the prompt
    semantic_origins_text = "\n".join(
        f"- {col_name}: Semantic origin at node(s) {str(origins)}"
        for col_name, origins in request.semantic_origins.items()
    )
    full_prompt = (
        f"=== SLA METRIC DESCRIPTION ===\n{request.metric_description}\n\n"
        f"=== PIPELINE DESCRIPTION ===\n{request.pipeline_description}\n\n"
        f"=== SEMANTIC ORIGINS ===\n{semantic_origins_text}\n\n"
        "Your goal is to produce structured output with two components:\n\n"
        "1. SPECIAL COLUMN DESCRIPTIONS: For each special column listed in the semantic origins, provide a concise, "
        "professional, and technically precise natural-language description (MAXIMUM 3 lines per column) explaining what "
        "the column represents and its relation to telemetry entities or relationships in the form of a dict { column_name: description } \n\n"
        "2. METRIC CALCULATION EXPLANATION: Provide a comprehensive explanation (MAXIMUM 4 lines) of how these special "
        "columns work together to calculate the SLA metric, describing how different telemetry sources or event streams "
        "contribute to the derived metric value.\n\n"
        "3. METRIC TYPE:\n"
        "   - 'error' if the metric type is error rates of a service in the time window"
        "   - 'uptime' if the metric type is the uptime of a service in the time window"
        "   - 'latency' if the metric type is percentile of latency between 2 events in the time window"
        "4. METRIC CALCULATION WINDOW: The time window in seconds in which the metric is calculated\n"
        "5. METRIC COLUMN: The name of the column in the final metric table that contains the calculated metric value\n"
        "Focus on semantics and context, not syntax or full restatement of the pipeline.\n"
        "Use library /pathwaycom/pathway"
    )
    
    # Check cache first
    cached_response = get_cached_response(full_prompt)
    if cached_response:
        return {"status": "ok", "summarized": cached_response, "cached": True}
    
    answer = await summarize_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        }
    )
    print(answer)
    summarized = answer["structured_response"]
    
    # Cache the response
    cache_response(full_prompt, summarized)
    
    return {"status": "ok", "summarized": summarized, "cached": False}
