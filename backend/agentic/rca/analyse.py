from typing import List, Dict, Union, Literal, Any, Optional
from typing_extensions import TypedDict
import hashlib
import os
from datetime import datetime, timedelta
from .summarize import SummarizeOutput
from .tools import get_error_logs_for_trace_ids, get_error_spans_for_trace_ids, get_downtime_timestamps, get_full_span_tree, TablePayload
from .error_agent import analyze_error_logs
from .downtime_agent import analyze_downtime_incidents, DowntimeIncident
from .latency_agent import build_graph, MetricAlert
from .output import RCAAnalysisOutput, PipelineTopology
from .rca_logger import rca_logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# RCA cache to prevent concurrent runs for the same metric
rca_cache: Dict[str, Dict[str, Any]] = {}
RCA_TIMEOUT_MINUTES = 10


async def save_rca_to_mongodb(
    rca_collection: AsyncIOMotorCollection,
    pipeline_id: str,
    metric_type: str,
    metric_description: str,
    trace_ids: Union[List[str], str],
    analysis: RCAAnalysisOutput
) -> Optional[str]:
    """
    Save RCA analysis results to MongoDB RCA collection.
    Returns the inserted document ID.
    """
    try:
        # Ensure trace_ids is a list
        if isinstance(trace_ids, str):
            trace_ids = [trace_ids]
        
        # Create RCA document
        rca_doc = {
            "pipeline_id": pipeline_id,
            "metric_type": metric_type,
            "title": f"{metric_type.upper()} - {metric_description[:100]}",
            "description": metric_description,
            "trace_ids": trace_ids,
            "triggered_at": datetime.now(),
            "metadata": {
                "status": "completed",
                "severity": analysis.severity,
                "affected_services": analysis.affected_services,
                "root_cause": analysis.root_cause,
                "narrative": analysis.narrative
            },
            "analysis": analysis.model_dump(),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Insert into MongoDB
        result = await rca_collection.insert_one(rca_doc)
        rca_logger.info(f"RCA analysis saved to MongoDB with ID: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        rca_logger.error(f"Failed to save RCA analysis to MongoDB: {e}")
        return None

async def build_pipeline_topology(trace_ids: Union[List[str], str], spans_table: TablePayload) -> PipelineTopology:
    """
    Build pipeline topology from trace_ids by aggregating all spans.
    Creates nodes and edges representing the trace tree structure.
    Identifies affected nodes (status_code >= 2).
    """
    if not trace_ids:
        return PipelineTopology(
            nodes=[],
            edges=[],
            affected_nodes=[]
        )
    if isinstance(trace_ids, str):
        trace_ids = [trace_ids]
    trace_ids = [trace_ids[0]]
    all_spans = []
    span_id_to_node_id = {}  # Map span_id to node_id (incremental)
    node_id_counter = 1
    
    # Collect all spans from all traces
    for trace_id in trace_ids:
        spans = await get_full_span_tree(trace_id, spans_table)
        all_spans.extend(spans)
    
    # Build nodes list with incremental node_ids
    nodes = []
    edges = []
    affected_nodes = []
    
    for span in all_spans:
        span_id = span.get('_open_tel_span_id')
        if span_id not in span_id_to_node_id:
            span_id_to_node_id[span_id] = node_id_counter
            
            nodes.append({
                "node_id": node_id_counter,
                "name": span.get('name', 'Unknown'),
                "service": span.get('_open_tel_service_name', 'Unknown'),
                "span_id": span_id
            })
            
            # Check if span is affected (status_code >= 2)
            # OpenTelemetry status codes: 0=UNSET, 1=OK, 2=ERROR
            status_code = span.get('status_code', 'UNSET')
            if isinstance(status_code, str):
                if status_code == 'ERROR':
                    affected_nodes.append(node_id_counter)
            elif isinstance(status_code, int) and status_code >= 2:
                affected_nodes.append(node_id_counter)
            
            node_id_counter += 1
    
    # Build edges from parent-child relationships
    for span in all_spans:
        span_id = span.get('_open_tel_span_id')
        parent_span_id = span.get('_open_tel_parent_span_id')
        
        if parent_span_id and parent_span_id in span_id_to_node_id:
            edges.append({
                "source": span_id_to_node_id[parent_span_id],
                "target": span_id_to_node_id[span_id]
            })
    
    return PipelineTopology(
        nodes=nodes,
        edges=edges,
        affected_nodes=affected_nodes
    )


class InitRCA(SummarizeOutput):
    # description of the metric
    description: str
    # Dict of column_name: trace_id(s) in that column. This column and its values relevant to calculation of the SLA metric
    trace_ids : Dict[str,Union[List[str],str]]
    table_data: Dict[Literal["spans","logs", "sla_metric_trigger"], TablePayload]
    # For latency analysis
    breach_time_utc: Optional[str] = None
    breach_value: Optional[float] = None

async def rca(
    init_rca_request: InitRCA,
    rca_collection: Optional[AsyncIOMotorCollection] = None
):
    # Generate cache key from metric description hash
    metric_hash = hashlib.sha256(init_rca_request.description.encode()).hexdigest()
    
    # Check if RCA is already running for this metric
    current_time = datetime.now()
    if metric_hash in rca_cache:
        cache_entry = rca_cache[metric_hash]
        if cache_entry["status"] == "running":
            # Check if the RCA is still within the timeout window
            time_elapsed = current_time - cache_entry["timestamp"]
            if time_elapsed < timedelta(minutes=RCA_TIMEOUT_MINUTES):
                rca_logger.warning(f"RCA already running for metric: {init_rca_request.description} (started {time_elapsed.seconds}s ago)")
                return {}
            else:
                # Timeout expired, allow new RCA to run
                rca_logger.info(f"Previous RCA timed out for metric: {init_rca_request.description}, starting new RCA")
    
    # Mark RCA as running
    rca_cache[metric_hash] = {
        "status": "running",
        "timestamp": current_time
    }
    
    try:
        # Log RCA initialization for user visibility
        rca_logger.info(f"Starting Root Cause Analysis for {init_rca_request.metric_type} metric: {init_rca_request.description}")
        
        print("RCA invoked")
        
        if len(init_rca_request.trace_ids.keys()) == 1:
            # Get the single column name and its trace_ids
            column_name = list(init_rca_request.trace_ids.keys())[0]
            trace_ids = init_rca_request.trace_ids[column_name]
            
            match init_rca_request.metric_type:
                case "error":
                    # Get error logs for analysis
                    error_logs = await get_error_logs_for_trace_ids(
                        trace_ids, 
                        init_rca_request.table_data["logs"],
                        13
                    )
                    
                    # Get error spans with status_code >= 2 for additional context
                    error_spans = await get_error_spans_for_trace_ids(
                        trace_ids,
                        init_rca_request.table_data["spans"],
                        2
                    )
                    
                    # Group logs by trace_id
                    logs_by_trace: Dict[str, List[Dict]] = {}
                    for log in error_logs:
                        trace_id = log.get('_open_tel_trace_id', 'unknown')
                        if trace_id not in logs_by_trace:
                            logs_by_trace[trace_id] = []
                        logs_by_trace[trace_id].append(log)
                    
                    # Group error spans by trace_id
                    spans_by_trace: Dict[str, List[Dict]] = {}
                    for span in error_spans:
                        trace_id = span.get('_open_tel_trace_id', 'unknown')
                        if trace_id not in spans_by_trace:
                            spans_by_trace[trace_id] = []
                        spans_by_trace[trace_id].append(span)
                    
                    # Analyze error logs and span status messages to find root cause
                    analysis: RCAAnalysisOutput = await analyze_error_logs(logs_by_trace, spans_by_trace)
                    
                    # Build pipeline topology
                    pipeline_topology = await build_pipeline_topology(
                        trace_ids,
                        init_rca_request.table_data["spans"]
                    )
                    
                    # Add topology to analysis
                    analysis.pipeline_topology = pipeline_topology
                    
                    rca_logger.info(f"Root Cause Analysis completed for error metric: {init_rca_request.description}")
                    
                    # Save to MongoDB if collection provided
                    if rca_collection is not None:
                        pipeline_id = os.getenv("PIPELINE_ID", column_name)
                        await save_rca_to_mongodb(
                            rca_collection,
                            pipeline_id,
                            init_rca_request.metric_type,
                            init_rca_request.description,
                            trace_ids,
                            analysis
                        )
                    
                    return {
                        "analysis": analysis.model_dump()
                    }
                
                case "latency":
                    # Create metric alert from the summarized data
                    metric_alert = MetricAlert(
                        metric_description=init_rca_request.description,
                        breach_time_utc=init_rca_request.breach_time_utc,
                        breach_value=init_rca_request.breach_value
                    )
                    
                    # Build and run the latency analysis graph
                    latency_graph = build_graph()
                    
                    # Pass table information to the graph
                    initial_state = {
                        "metric_alert": metric_alert,
                        "sla_alerts": [],
                        "messages": [],
                        "final_reports": None,
                        "analysis_summary": None,
                        "rca_output": None,
                        "table_data": {
                            "spans": init_rca_request.table_data["spans"],
                            "logs": init_rca_request.table_data["logs"]
                        }
                    }
                    
                    result = await latency_graph.ainvoke(initial_state)
                    
                    analysis: RCAAnalysisOutput = result.get("rca_output")
                    
                    if not analysis:
                        rca_logger.warning(f"Root Cause Analysis could not be completed for latency metric: {init_rca_request.description}")
                        return {
                            "analysis": {
                                "message": "Latency analysis could not be completed"
                            }
                        }
                    
                    # Build pipeline topology
                    pipeline_topology = await build_pipeline_topology(
                        trace_ids,
                        init_rca_request.table_data["spans"]
                    )
                    
                    # Add topology to analysis
                    analysis.pipeline_topology = pipeline_topology
                    
                    rca_logger.info(f"Root Cause Analysis completed for latency metric: {init_rca_request.description}")
                    
                    # Save to MongoDB if collection provided
                    if rca_collection is not None:
                        pipeline_id = os.getenv("PIPELINE_ID", column_name)
                        await save_rca_to_mongodb(
                            rca_collection,
                            pipeline_id,
                            init_rca_request.metric_type,
                            init_rca_request.description,
                            trace_ids,
                            analysis
                        )
                    
                    return {
                        "analysis": analysis.model_dump()
                    }
                
                case "uptime":
                    # Get actual timestamps from sla_metric_trigger table
                    timestamp_data = await get_downtime_timestamps(
                        trace_ids,
                        column_name,
                        init_rca_request.table_data["sla_metric_trigger"]
                    )
                    
                    # Create downtime incidents with actual timestamps
                    incidents = []
                    for row in timestamp_data:
                        incidents.append(DowntimeIncident(
                            trace_id=row["trace_id"],
                            timestamp=row["time"],
                            duration_ms=None
                        ))
                    
                    if not incidents:
                        return {
                            "analysis":{ 
                                "message": "No downtime incidents found in SLA metric trigger table"
                            }
                        }
                    
                    # Analyze downtime with 30-second window around each incident
                    # Uses parallel execution for individual incidents
                    analysis: RCAAnalysisOutput = await analyze_downtime_incidents(
                        incidents=incidents,
                        logs_table=init_rca_request.table_data["logs"],
                        spans_table=init_rca_request.table_data["spans"],
                        window_seconds=30
                    )
                    
                    # Build pipeline topology
                    pipeline_topology = await build_pipeline_topology(
                        trace_ids,
                        init_rca_request.table_data["spans"]
                    )
                    
                    # Add topology to analysis
                    analysis.pipeline_topology = pipeline_topology
                    
                    rca_logger.info(f"Root Cause Analysis completed for uptime metric: {init_rca_request.description}")
                    
                    # Save to MongoDB if collection provided
                    if rca_collection is not None:
                        pipeline_id = os.getenv("PIPELINE_ID", column_name)
                        await save_rca_to_mongodb(
                            rca_collection,
                            pipeline_id,
                            init_rca_request.metric_type,
                            init_rca_request.description,
                            trace_ids,
                            analysis
                        )
                    
                    return {
                        "analysis": analysis.model_dump()
                    }
                
                case _:
                    raise ValueError(f"Unknown metric type: {init_rca_request.metric_type}")
        else:
            # Handle multiple trace_id columns
            pass
    
    finally:
        # Mark RCA as completed
        if metric_hash in rca_cache:
            rca_cache[metric_hash] = {
                "status": "completed",
                "timestamp": datetime.now()
            }
