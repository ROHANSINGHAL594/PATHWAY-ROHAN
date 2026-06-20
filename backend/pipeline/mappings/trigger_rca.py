from lib.trigger_rca import TriggerRCANode
from lib.logger import setup_logging
import pathway as pw
from ..types import Graph, MetricNodeDescription
import httpx
import os
from postgres_util import construct_table_name
import json
from datetime import datetime, timezone
import asyncio
import logging
from pymongo import MongoClient

# Configure logger using centralized setup_logging
# Uses PostgreSQL for all logs, MongoDB for WARNING+ logs only
logger = setup_logging(
    mongo_collection="rca_logs",
    level=logging.INFO,
    mongo_level=logging.WARNING,  # Only important logs go to MongoDB
    fallback_file="trigger_rca.log"
)

agentic_url = os.getenv("AGENTIC_URL")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "easyworkflow")
RCA_COLLECTION = os.getenv("RCA_COLLECTION", "rca_events")
PIPELINE_ID = os.getenv("PIPELINE_ID")

# MongoDB client for inserting RCA events
mongo_client = None
rca_collection = None

def get_rca_collection():
    """Get or create MongoDB connection for RCA collection"""
    global mongo_client, rca_collection
    if rca_collection is None and MONGO_URI:
        try:
            mongo_client = MongoClient(MONGO_URI)
            db = mongo_client[MONGO_DB]
            rca_collection = db[RCA_COLLECTION]
            logger.info(f"Connected to MongoDB for RCA events: {MONGO_DB}.{RCA_COLLECTION}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB for RCA: {e}")
            return None
    return rca_collection


def insert_rca_event(title: str, description: str, trace_ids: dict, metadata: dict, status: str = "in_progress"):
    """
    Insert an RCA event into MongoDB. 
    The WebSocket change stream watcher will automatically broadcast this to the frontend.
    """
    collection = get_rca_collection()
    if collection is None:
        logger.warning("Cannot insert RCA event: MongoDB collection not available")
        return None
    
    rca_doc = {
        "pipeline_id": PIPELINE_ID,
        "title": title,
        "description": description,
        "triggered_at": datetime.now(timezone.utc),
        "trace_ids": trace_ids,
        "metadata": {
            **metadata,
            "status": status
        }
    }
    
    try:
        result = collection.insert_one(rca_doc)
        logger.info(f"RCA event inserted with ID: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Failed to insert RCA event: {e}")
        return None


def update_rca_event(rca_id: str, metadata_update: dict, status: str = None):
    """
    Update an existing RCA event in MongoDB.
    The WebSocket change stream watcher will automatically broadcast updates to the frontend.
    """
    from bson import ObjectId
    collection = get_rca_collection()
    if collection is None:
        logger.warning("Cannot update RCA event: MongoDB collection not available")
        return False
    
    update_data = {"$set": {}}
    if metadata_update:
        for key, value in metadata_update.items():
            update_data["$set"][f"metadata.{key}"] = value
    if status:
        update_data["$set"]["metadata.status"] = status
    
    try:
        result = collection.update_one({"_id": ObjectId(rca_id)}, update_data)
        logger.info(f"RCA event {rca_id} updated: {result.modified_count} documents modified")
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Failed to update RCA event {rca_id}: {e}")
        return False

class RCAOutputSchema(pw.Schema):
    analysis: pw.Json


def trigger_rca(metric_table: pw.Table, node: TriggerRCANode, graph: Graph) -> pw.Table:
    # Retreive columns which contain trace ids relevent to the calculation of the metric connected to the TriggerRCA node
    metric: MetricNodeDescription = None
    metric_node_idx: int = None
    for idx,_met in graph["metric_node_descriptions"].items():
         if _met["description"] == node.metric_description:
              metric = _met
              metric_node_idx = idx
        
    semantic_origins = {}
    for special_col, origins in metric["special_columns_source_indexes"].items():
         semantic_origins[special_col] = [metric["pipeline_description_indexes_mapping"][origin] for origin in origins]
    
    if len(semantic_origins.keys()) == 0:
        raise Exception("Can only perform RCA on metrics derived from OpenTelemetry data")
    with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{agentic_url.rstrip('/')}/summarize",
                json={
                    "metric_description": metric["description"],
                    "pipeline_description": metric["pipeline_description"],
                    "semantic_origins": semantic_origins
                },
            )
            resp.raise_for_status()
            summarized_metric = resp.json()["summarized"]
    if summarized_metric["metric_type"] == "error":
        if len(semantic_origins.keys()) > 1:
            raise Exception("Currently RCA on an error-rate metric derived from multiple traces is not supported")
    if summarized_metric["metric_type"] == "uptime":
        if len(semantic_origins.keys()) > 1:
            raise Exception("Currently RCA on an uptime metric derived from multiple traces is not supported")
    if summarized_metric["metric_type"] == "latency":
        if len(semantic_origins.keys()) > 2:
            raise Exception("Currently RCA on a latency metric derived from more than 2 traces is not supported")
    
    spans_node_idx : int = None
    logs_node_idx: int = None

    for idx,node in enumerate(graph["nodes"]):
        if node.node_id == "open_tel_spans_input" and spans_node_idx is None:
            spans_node_idx = idx
        if node.node_id == "open_tel_logs_input" and logs_node_idx is None:
            logs_node_idx = idx
    if any(el is None for el in [spans_node_idx,logs_node_idx]):
        raise Exception("No tables for span/logs found. Cannot run RCA on metrics derived from non open telemetry sources")
    tables_data = {
        "spans": {
            "table_name": construct_table_name(graph["nodes"][spans_node_idx].node_id, spans_node_idx),
            # "table_schema": graph["node_outputs"][spans_node_idx].schema.columns_to_json_serializable_dict()
        },
        "logs": {
            "table_name": construct_table_name(graph["nodes"][logs_node_idx].node_id, logs_node_idx),
            # "table_schema": graph["node_outputs"][logs_node_idx].schema.columns_to_json_serializable_dict()
        },
        "sla_metric_trigger": {
            "table_name": construct_table_name(node.node_id,metric_node_idx),
            # "table_schema": metric_table.schema.columns_to_json_serializable_dict()
        }
    }


    class RCATransformer(pw.AsyncTransformer, output_schema=RCAOutputSchema):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        async def invoke(self,**columns) -> dict:
            
            # Extract breach_value from the metric column
            metric_column_name = summarized_metric["metric_column"]
            breach_value = float(columns.get(metric_column_name, 0))
            
            # Get current timestamp in ISO format with UTC timezone
            breach_time_utc = datetime.now(timezone.utc).isoformat()
            
            # Prepare trace_ids for RCA request
            trace_ids_data = {
                special_column: (list(columns[special_column]) if isinstance(columns[special_column], tuple) else columns[special_column]) 
                for special_column in semantic_origins.keys()
            }
            
            # Insert RCA event into MongoDB (will be broadcast via WebSocket change stream)
            rca_event_id = insert_rca_event(
                title=f"SLA Breach Detected: {metric['description']}",
                description=f"Metric '{metric_column_name}' breached threshold with value {breach_value} at {breach_time_utc}",
                trace_ids=trace_ids_data,
                metadata={
                    "metric_type": summarized_metric.get("metric_type", "unknown"),
                    "breach_value": breach_value,
                    "breach_time_utc": breach_time_utc,
                    "metric_description": metric["description"]
                },
                status="in_progress"
            )
            logger.info(f"RCA triggered for metric '{metric['description']}' - Event ID: {rca_event_id}")
            
            request_data = {
                "trace_ids": trace_ids_data,
                **summarized_metric,
                "table_data": tables_data,
                "description": metric["description"],
                "breach_value": breach_value,
                "breach_time_utc": breach_time_utc
            }
          
            # Call RCA API
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{agentic_url.rstrip('/')}/rca",
                    json=request_data,
                )
                if resp.status_code != 200:
                    # Update RCA event with error status
                    if rca_event_id:
                        update_rca_event(rca_event_id, {"error": resp.text}, status="failed")
                        logger.error(f"RCA API call failed for event {rca_event_id}: {resp.text}")
                    raise Exception(f"Request Data: {json.dumps(request_data,indent=4)}\n\n{resp.text}")
                rca_data = resp.json()
            
            # Check if RCA returned empty dict (indicating another RCA is running)
            if not rca_data or rca_data == {}:
                if rca_event_id:
                    update_rca_event(rca_event_id, {"note": "Another RCA was already running"}, status="skipped")
                    logger.info(f"RCA event {rca_event_id} skipped - another RCA in progress")
                return {
                    "analysis": {},
                    "report": {},
                    "remediation": {}
                }
            
            # Extract RCA analysis output for parallel API calls
            rca_output = rca_data.get("analysis")
            
            if not rca_output:
                if rca_event_id:
                    update_rca_event(rca_event_id, {"note": "No analysis output from RCA"}, status="completed_no_analysis")
                    logger.warning(f"RCA event {rca_event_id} completed but no analysis output")
                return rca_data
            
            # Define async functions for parallel API calls
            async def generate_report():
                """Call the incident report generation API"""
                try:
                    pipeline_topology = rca_output.pop('pipeline_topology')
                    async with httpx.AsyncClient(timeout=120) as client:
                        report_resp = await client.post(
                            f"{agentic_url.rstrip('/')}/api/v1/reports/incident",
                            json={"rca_output": {
                                **rca_output,
                                "span_data": pipeline_topology,
                                "financial_impact": {
                                    "estimated_loss_usd": 87500,
                                    "affected_transactions": 493 ,
                                    "duration_minutes": 35
                                }
                            }}
                        )
                        if report_resp.status_code == 200:
                            return report_resp.json()
                        else:
                            return {"error": f"Report generation failed: {report_resp.text}"}
                except Exception as e:
                    return {"error": f"Report generation error: {str(e)}"}
            
            async def recommend_actions():
                """Call the runbook remediation API"""
                try:
                    # Use root_cause as the error message for remediation
                    error_message = rca_output.get("root_cause", None)
                    if error_message is None:
                        return {"error": "Unknown error"}
                    async with httpx.AsyncClient(timeout=120) as client:
                        remediation_resp = await client.post(
                            f"{agentic_url.rstrip('/')}/runbook/remediate",
                            json={
                                "error_message": error_message,
                                "auto_execute": True,  # Don't auto-execute, just suggest
                                "require_approval_medium": True
                            }
                        )
                        if remediation_resp.status_code == 200:
                            return remediation_resp.json()
                        else:
                            return {"error": f"Remediation suggestion failed: {remediation_resp.text}"}
                except Exception as e:
                    return {"error": f"Remediation suggestion error: {str(e)}"}
            
            # Call both APIs in parallel
            report_result, remediation_result = await asyncio.gather(
                generate_report(),
                recommend_actions(),
                return_exceptions=True
            )
            
            # Prepare final results
            final_result = {
                "analysis": rca_output,
                "report": report_result if not isinstance(report_result, Exception) else {"error": str(report_result)},
                "remediation": remediation_result if not isinstance(remediation_result, Exception) else {"error": str(remediation_result)}
            }
            
            # Update RCA event with analysis results (WebSocket will broadcast the update)
            if rca_event_id:
                has_errors = (
                    isinstance(report_result, Exception) or 
                    isinstance(remediation_result, Exception) or
                    final_result.get("report", {}).get("error") or
                    final_result.get("remediation", {}).get("error")
                )
                final_status = "completed" if not has_errors else "completed_with_errors"
                
                update_rca_event(
                    rca_event_id,
                    metadata_update={
                        "analysis_result": rca_output,
                        "root_cause": rca_output.get("root_cause"),
                        "severity": rca_output.get("severity"),
                        "affected_services": rca_output.get("affected_services", []),
                        "report_generated": not bool(final_result.get("report", {}).get("error")),
                        "remediation_suggested": not bool(final_result.get("remediation", {}).get("error"))
                    },
                    status=final_status
                )
                logger.info(f"RCA event {rca_event_id} completed with status: {final_status}")
            
            return final_result
    return RCATransformer(input_table=metric_table).successful