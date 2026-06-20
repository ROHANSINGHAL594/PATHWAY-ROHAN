from datetime import datetime
import random
from fastapi import APIRouter, Request
from .version_manager.routes import serialize_mongo
from .version_manager.schema import Notification, Log
from backend.lib.notifications import add_notification as add_notification_util


router = APIRouter()


@router.post("/test_rca_event")
async def test_rca_event(
    request: Request,
    pipeline_id: str = None
):
    '''
    Test endpoint to create a sample RCA event for testing purposes.
    If pipeline_id is not provided, creates a test event with a dummy pipeline_id.
    '''
    rca_collection = request.app.state.rca_collection
    workflow_collection = request.app.state.workflow_collection

    # If no pipeline_id provided, try to get the first available workflow
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"

    # Create RCA-specific test events
    rca_scenarios = [
        {
            "title": "High Latency Anomaly Detected",
            "description": "ML model detected unusual latency spike in data processing nodes. Triggering root cause analysis.",
            "severity": "high"
        },
        {
            "title": "Error Rate Threshold Breached",
            "description": "Error rate exceeded 5% threshold. Initiating automated RCA to identify failing components.",
            "severity": "critical"
        },
        {
            "title": "SLA Violation Predicted",
            "description": "Predictive model forecasts SLA breach in next 15 minutes based on current throughput trends.",
            "severity": "high"
        },
        {
            "title": "Pipeline Performance Degradation",
            "description": "Significant drop in pipeline throughput detected. Analyzing upstream dependencies.",
            "severity": "medium"
        }
    ]
    
    scenario = random.choice(rca_scenarios)

    test_rca_data = {
        "pipeline_id": pipeline_id,
        "title": scenario["title"],
        "description": scenario["description"],
        "triggered_at": datetime.now(),
        "trace_ids": [f"trace_{random.randint(100, 999)}", f"trace_{random.randint(100, 999)}"],
        "metadata": {
            "test": True,
            "source": "test_endpoint",
            "severity": scenario["severity"],
            "status": "in_progress"
        }
    }

    result = await rca_collection.insert_one(test_rca_data)

    return serialize_mongo({
        "status": "success",
        "message": "Test RCA event created successfully",
        "inserted_id": str(result.inserted_id),
        "inserted_data": test_rca_data,
        "note": "Slack notification will be sent via change stream watcher"
    })


@router.post("/test_notification")
async def test_notification(
    request: Request,
    pipeline_id: str = None,
    notification_type: str = None
):
    '''
    Test endpoint to create pipeline-specific notifications for WebSocket testing.
    
    Parameters:
    - pipeline_id: Optional. If not provided, uses first available workflow.
    - notification_type: Optional. One of: success, error, warning, info
    
    This will:
    1. Insert notification into MongoDB
    2. Trigger change stream
    3. Broadcast via WebSocket to all connected clients
    '''
    notification_collection = request.app.state.notification_collection
    workflow_collection = request.app.state.workflow_collection
    
    # Get pipeline_id
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"
    
    # Pipeline-specific notification types and messages
    types = ["success", "error", "warning", "info"]
    selected_type = notification_type if notification_type in types else random.choice(types)
    
    messages = {
        "success": [
            ("RCA Completed", "Root cause analysis completed successfully. Sending detailed report over Slack."),
            ("Pipeline Recovered", "Pipeline recovered from error state. All nodes operational."),
            ("Runbook Executed", "Automated runbook executed successfully. System stabilized."),
            ("SLA Maintained", "Pipeline met SLA requirements. No action needed.")
        ],
        "error": [
            ("Pipeline Execution Failed", "Critical error in data processing node. RCA triggered."),
            ("Node Connection Lost", "Lost connection to upstream data source. Attempting reconnection."),
            ("Data Validation Failed", "Incoming data failed schema validation. Pipeline paused."),
            ("Runbook Execution Failed", "Automated remediation failed. Manual intervention required.")
        ],
        "warning": [
            ("Latency Threshold Approaching", "Processing latency at 80% of SLA threshold."),
            ("Throughput Degradation", "Data throughput dropped by 30%. Monitoring closely."),
            ("Resource Utilization High", "Pipeline memory usage at 85%. Consider scaling."),
            ("Prediction: SLA Risk", "ML model predicts potential SLA breach in next 30 minutes.")
        ],
        "info": [
            ("RCA Triggered", "Root cause analysis initiated for detected anomaly."),
            ("Pipeline Started", "Data pipeline started processing incoming stream."),
            ("Runbook Available", "New automated runbook available for this error pattern."),
            ("Report Generated", "Analysis report generated. Will be available for download shortly.")
        ]
    }
    
    title, desc = random.choice(messages[selected_type])
    
    notification_data = {
        "pipeline_id": pipeline_id,
        "title": title,
        "desc": desc,
        "type": selected_type,
        "timestamp": datetime.now()
    }
    
    result = await notification_collection.insert_one(notification_data)
    
    return serialize_mongo({
        "status": "success",
        "message": f"Test {selected_type} notification created",
        "inserted_id": str(result.inserted_id),
        "inserted_data": notification_data,
        "websocket_broadcast": "Change stream will broadcast automatically"
    })


@router.post("/test_alert")
async def test_alert(
    request: Request,
    pipeline_id: str = None
):
    '''
    Test endpoint to create an ALERT (actionable notification) for WebSocket testing.
    
    Alerts are special notifications with:
    - type = "alert"
    - alert object containing binary actions (Proceed/Ignore) and status
    
    This will trigger WebSocket broadcast and show in the pending actions panel.
    '''
    notification_collection = request.app.state.notification_collection
    workflow_collection = request.app.state.workflow_collection
    
    # Get pipeline_id
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"
    
    # RCA and Pipeline-specific alert scenarios with binary actions
    alert_scenarios = [
        {
            "title": "RCA Suggests Runbook Execution",
            "desc": "Root cause analysis completed. Agent recommends executing Runbook `restart_upstream_service`. Sending detailed report over Slack.",
        },
        {
            "title": "Anomaly Detected: High Latency",
            "desc": "ML model detected latency anomaly. Agent suggests applying Runbook `scale_pipeline_nodes`. Report will be available for download shortly.",
        },
        {
            "title": "SLA Breach Predicted",
            "desc": "Predictive model forecasts SLA violation in 15 minutes. Agent recommends Runbook `increase_throughput`. Sending detailed report over Slack.",
        },
        {
            "title": "Error Pattern Matched",
            "desc": "Detected known error pattern in logs. Agent suggests Runbook `clear_cache_restart`. Report will be available for download shortly.",
        },
        {
            "title": "Pipeline Recovery Action",
            "desc": "Pipeline recovered from failure. Agent recommends Runbook `validate_data_integrity` to ensure consistency. Sending detailed report over Slack.",
        },
        {
            "title": "Throughput Degradation Alert",
            "desc": "Data throughput dropped 40%. RCA identified upstream bottleneck. Agent suggests Runbook `optimize_query`. Report will be available for download shortly.",
        }
    ]
    
    scenario = random.choice(alert_scenarios)
    
    alert_data = {
        "pipeline_id": pipeline_id,
        "title": scenario["title"],
        "desc": scenario["desc"],
        "type": "alert",
        "timestamp": datetime.now(),
        "alert": {
            "actions": ["Proceed", "Ignore"],  # Binary actions
            "action_taken": None,
            "taken_at": None,
            "action_executed_by": None,
            "action_executed_by_user": None,
            "status": "pending"  # Status: pending, completed, rejected, ignored
        }
    }
    
    result = await notification_collection.insert_one(alert_data)
    
    return serialize_mongo({
        "status": "success",
        "message": "Test alert created",
        "inserted_id": str(result.inserted_id),
        "inserted_data": alert_data,
        "websocket_broadcast": "Change stream will broadcast automatically",
        "note": "Check 'Pending Actions' section in UI"
    })


@router.post("/test_log")
async def test_log(
    request: Request,
    pipeline_id: str = None,
    level: str = None
):
    '''
    Test endpoint to create pipeline-specific log entries for WebSocket testing.
    
    Parameters:
    - pipeline_id: Optional. If not provided, uses first available workflow.
    - level: Optional. One of: debug, info, warning, error, critical
    
    This will:
    1. Insert log into MongoDB logs collection
    2. Trigger change stream
    3. Broadcast via WebSocket with message_type="log"
    4. If level is "critical", send Slack notification
    '''
    log_collection = request.app.state.log_collection
    workflow_collection = request.app.state.workflow_collection
    
    # Get pipeline_id
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"
    
    # Pipeline-specific log levels and messages
    levels = ["debug", "info", "warning", "error", "critical"]
    selected_level = level if level in levels else random.choice(levels)
    
    log_messages = {
        "debug": [
            "Processing batch: 1000 records",
            "Latency check: 45ms",
            "Throughput: 5000 rec/s",
            "Memory usage: 65%"
        ],
        "info": [
            "Pipeline started",
            "Pipeline stopped",
            "Node execution completed",
            "RCA analysis started",
            "Runbook queued for execution",
            "Data ingestion resumed"
        ],
        "warning": [
            "Latency approaching threshold",
            "Throughput degradation detected",
            "Retry attempt 2/3",
            "Prediction: SLA risk in 30min"
        ],
        "error": [
            "Node execution failed",
            "Connection timeout",
            "Data validation failed",
            "Runbook execution failed"
        ],
        "critical": [
            "Pipeline crashed",
            "Data loss detected",
            "SLA breached",
            "System unresponsive"
        ]
    }
    
    sources = ["pipeline", "rca_agent", "runbook", "predictor", "monitor"]
    
    message = random.choice(log_messages[selected_level])
    
    log_data = {
        "pipeline_id": pipeline_id,
        "level": selected_level,
        "message": message,
        "timestamp": datetime.now(),
        "source": random.choice(sources)
    }
    
    result = await log_collection.insert_one(log_data)
    
    return serialize_mongo({
        "status": "success",
        "message": f"Test {selected_level} log created",
        "inserted_id": str(result.inserted_id),
        "inserted_data": log_data,
        "websocket_broadcast": "Change stream will broadcast with message_type='log'",
        "slack_notification": "Will be sent if level is 'critical'"
    })


@router.post("/test_all")
async def test_all(
    request: Request,
    pipeline_id: str = None
):
    '''
    Test endpoint to create one of each: notification, alert, and log.
    Useful for testing the complete WebSocket flow at once.
    '''
    notification_collection = request.app.state.notification_collection
    log_collection = request.app.state.log_collection
    workflow_collection = request.app.state.workflow_collection
    
    # Get pipeline_id
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"
    
    results = []
    
    # 1. Create a notification (pipeline-specific)
    notification_data = {
        "pipeline_id": pipeline_id,
        "title": "RCA Completed",
        "desc": "Root cause analysis completed. Sending detailed report over Slack.",
        "type": "success",
        "timestamp": datetime.now()
    }
    notif_result = await notification_collection.insert_one(notification_data)
    results.append({"type": "notification", "id": str(notif_result.inserted_id)})
    
    # 2. Create an alert (with binary actions)
    alert_data = {
        "pipeline_id": pipeline_id,
        "title": "RCA Suggests Runbook Execution",
        "desc": "Agent recommends executing Runbook `restart_service`. Report will be available for download shortly.",
        "type": "alert",
        "timestamp": datetime.now(),
        "alert": {
            "actions": ["Proceed", "Ignore"],
            "action_taken": None,
            "taken_at": None,
            "action_executed_by": None,
            "action_executed_by_user": None,
            "status": "pending"  # Status: pending, completed, rejected, ignored
        }
    }
    alert_result = await notification_collection.insert_one(alert_data)
    results.append({"type": "alert", "id": str(alert_result.inserted_id)})
    
    # 3. Create a log (pipeline-specific)
    log_data = {
        "pipeline_id": pipeline_id,
        "level": "info",
        "message": "Pipeline started",
        "timestamp": datetime.now(),
        "source": "pipeline"
    }
    log_result = await log_collection.insert_one(log_data)
    results.append({"type": "log", "id": str(log_result.inserted_id)})
    
    return serialize_mongo({
        "status": "success",
        "message": "Created 1 notification, 1 alert, and 1 log",
        "pipeline_id": pipeline_id,
        "results": results,
        "websocket_note": "All items will be broadcast via WebSocket change streams"
    })


@router.post("/test_critical_log")
async def test_critical_log(
    request: Request,
    pipeline_id: str = None
):
    '''
    Test endpoint to specifically test critical log with Slack notification.
    Creates pipeline-specific critical logs.
    '''
    log_collection = request.app.state.log_collection
    workflow_collection = request.app.state.workflow_collection
    
    # Get pipeline_id
    if not pipeline_id:
        first_workflow = await workflow_collection.find_one()
        if first_workflow:
            pipeline_id = str(first_workflow["_id"])
        else:
            pipeline_id = "test_pipeline_id"
    
    # Pipeline-specific critical scenarios
    critical_scenarios = [
        ("Pipeline crashed", "pipeline"),
        ("SLA breached", "monitor"),
        ("Data loss detected", "pipeline"),
        ("System unresponsive", "monitor"),
    ]
    
    message, source = random.choice(critical_scenarios)
    
    log_data = {
        "pipeline_id": pipeline_id,
        "level": "critical",
        "message": message,
        "timestamp": datetime.now(),
        "source": source
    }
    
    result = await log_collection.insert_one(log_data)
    
    return serialize_mongo({
        "status": "success",
        "message": "Critical log created",
        "inserted_id": str(result.inserted_id),
        "inserted_data": log_data,
        "slack_notification": "Sending detailed report over Slack"
    })


@router.post("/add_notification")
async def add_notification(
    data: Notification, 
    request: Request
):
    '''
    Route to add a notification.
    Can be called by agents or the pipeline.
    The change stream watcher will automatically broadcast via WebSocket.
    '''
    notification_collection = request.app.state.notification_collection

    # Convert to dict and use the utility function
    notification_data = data.model_dump()
    return await add_notification_util(notification_data, notification_collection)

@router.post("/add_log")
async def add_log(
    data: Log,
    request: Request
):
    '''
    Route to add a log entry.
    Can be called by agents or the pipeline.
    The change stream watcher will automatically broadcast via WebSocket.
    Critical logs will trigger Slack notifications.
    '''
    log_collection = request.app.state.log_collection

    # Convert to dict and ensure timestamp is set
    log_data = data.model_dump()
    if "timestamp" not in log_data or not log_data["timestamp"]:
        log_data["timestamp"] = datetime.now()

    # Insert log into database
    # The watch_logs change stream will automatically broadcast it via WebSocket
    # Critical logs will trigger Slack notifications via the watcher
    result = await log_collection.insert_one(log_data)

    return serialize_mongo({
        "status": "success",
        "inserted_id": str(result.inserted_id),
        "inserted_data": log_data
    })
