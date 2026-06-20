from fastapi import APIRouter, Request, Depends, HTTPException
from .version_manager.schema import UpdateNotificationAction
from datetime import datetime
from bson.objectid import ObjectId
from .auth.models import User
from .auth.routes import get_current_user
from .auth.database import get_db
from .auth import crud as auth_crud
from sqlalchemy.ext.asyncio import AsyncSession
from .version_manager.routes import serialize_mongo

router = APIRouter()


@router.get("/kpi")
async def fetch_kpi(request: Request, current_user: User = Depends(get_current_user)):
    user_id = str(current_user.id)
    workflow_collection = request.app.state.workflow_collection
    notification_collection = request.app.state.notification_collection
    rca_collection = request.app.state.rca_collection
    query={}
    if current_user.role!="admin":
        query={"owner_ids": user_id}
    workflows = await workflow_collection.find(query).to_list(length=None)

    # Workflow stats
    total_workflows = len(workflows)
    running_workflows = sum(1 for w in workflows if w["status"] == "Running")
    stopped_workflows = sum(1 for w in workflows if w["status"] == "Stopped")
    broken_workflows = total_workflows - running_workflows - stopped_workflows

    user_role = current_user.role
    queries = [{"pipeline_id":str(pipeline["_id"])} for pipeline in workflows]

    notifications =[]
    if queries != []:
        notifications = await notification_collection.find({"$or":queries}).to_list(length=None)
    total_notifications = len(notifications)
    total_runtime = sum(w.get("runtime", 0) for w in workflows if w is not None)

    alerts = [n for n in notifications if n.get("type") == "alert"]
    total_alerts = len(alerts)

    pending_alerts = sum(1 for a in alerts if a.get("alert") and not a["alert"].get("action_taken"))
    seconds = total_runtime
    result=0

    if seconds >= 86400:
        result = f"{seconds // 86400}d"
    elif seconds >= 3600:
        result = f"{seconds // 3600}h"
    elif seconds >= 60:
        result = f"{seconds // 60}m"
    else:
        result = f"{seconds}s"

    # Get RCA triggers count
    rca_events = []
    if queries:
        rca_events = await rca_collection.find({"$or": queries}).to_list(length=None)
    total_rca_triggers = len(rca_events)

    return {
        "pie_chart": {
            "total": total_workflows,
            "running": running_workflows,
            "stopped": stopped_workflows,
            "broken": broken_workflows
        },
        "kpi": [
            {
                "id": "total_runtime",
                "title": "Total Runtime",
                "value": result,
                "subtitle": "Across all pipelines",
                "iconType": "speed",
                "iconColor": "#86C8BC"
            },
            {
                "id": "total_alerts",
                "title": "Total Alerts",
                "value": total_alerts,
                "subtitle": "In the last 24h",
                "iconType": "error-outline",
                "iconColor": "#F0B4C4"
            },
            {
                "id": "pending_alerts",
                "title": "Pending Alerts",
                "value": pending_alerts,
                "subtitle": "Require attention",
                "iconType": "access-time",
                "iconColor": "#F4D4A2"
            },
            {
                "id": "rca_triggers",
                "title": "RCA Triggers",
                "value": total_rca_triggers,
                "subtitle": "Root cause analysis",
                "iconType": "timeline",
                "iconColor": "#A2B8F4"
            }
        ]
    }


@router.get("/logs")
async def get_logs(
    request: Request,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    '''
    Fetch logs for workflows the user has access to.
    Similar to notifications endpoint - filters by user's workflows.
    '''
    user_id = str(current_user.id)
    workflow_collection = request.app.state.workflow_collection
    log_collection = request.app.state.log_collection

    # Get user's workflows (admin sees all)
    query = {}
    if current_user.role != "admin":
        query = {"owner_ids": user_id}

    workflows = await workflow_collection.find(query).to_list(length=None)

    # Build query for logs matching user's pipelines
    pipeline_queries = [{"pipeline_id": str(pipeline["_id"])} for pipeline in workflows]

    logs = []
    if pipeline_queries:
        logs = await log_collection.find(
            {"$or": pipeline_queries}
        ).sort("timestamp", -1).skip(skip).limit(limit).to_list(length=limit)

    return serialize_mongo({
        "status": "success",
        "count": len(logs),
        "data": logs
    })


@router.get("/workflows/")
async def workflow_data(request: Request, skip: int = 0, limit: int = 10, current_user: User = Depends(get_current_user)):
    cursor = request.app.state.workflow_collection.find({"owner_ids": str(current_user.id)}).sort("last_updated", -1).skip(skip).limit(limit)
    recent_pipelines = await cursor.to_list(length=limit)
    data = []
    for pipeline in recent_pipelines:
        data.append({
            "id": str(pipeline["_id"]), "lastModified": str(pipeline["last_updated"])
        })
    return data


@router.get("/total_runtime")
async def total_runtime(request: Request, current_user: User = Depends(get_current_user)):
    cursor = request.app.state.workflow_collection.find({"owner_ids": str(current_user.id)})
    total_runtime = 0
    async for doc in cursor:
        try:
            total_runtime += doc["runtime"]
        except:
            pass
    return total_runtime


@router.get("/notifications")
async def notification(
    request: Request, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = str(current_user.id)
    workflow_collection = request.app.state.workflow_collection
    notification_collection = request.app.state.notification_collection
    query={}
    if current_user.role!="admin":
        query={"owner_ids": user_id}
    workflows = await workflow_collection.find(query).to_list(length=None)


    queries = [{"pipeline_id":str(pipeline["_id"])} for pipeline in workflows]

    notifications =[]
    if queries != []:
        notifications = await notification_collection.find({"$or":queries}).to_list(length=None)


    enriched_notifications = []
    for notif in notifications:
        enriched_notif = dict(notif)

        if enriched_notif.get("alert") and enriched_notif["alert"].get("action_executed_by"):#finds if someone took the action
            action_user_id = enriched_notif["alert"]["action_executed_by"]
            try:
                action_user = await auth_crud.get_user_by_id(db, int(action_user_id))
                if action_user:
                    enriched_notif["action_executed_by_user"] = {
                        "id": str(action_user.id),
                        "email": action_user.email,
                        "full_name": action_user.full_name or action_user.email
                    }
            except (ValueError, Exception):
                pass
        enriched_notifications.append(enriched_notif)

    return serialize_mongo({
        "status": "success",
        "count": len(enriched_notifications),
        "data": enriched_notifications,
        "notifications": notifications
    })


@router.patch("/notifications/{notification_id}/action")
async def update_notification_action(
    notification_id: str,
    action_data: UpdateNotificationAction,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update notification with action taken by user.
    User must have access to the notification (owner, in viewer_ids, and role in allowed_roles)
    """
    notification_collection = request.app.state.notification_collection
    workflow_collection = request.app.state.workflow_collection
    user_role = current_user.role
    is_admin = user_role.lower() == "admin"

    try:
        notification_obj_id = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification ID format")

    notification = await notification_collection.find_one({"_id": notification_obj_id})

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    can_take_action = False
    if is_admin:
        can_take_action = True
    elif notification.get("pipeline_id"):
        workflow = await workflow_collection.find_one({"_id": ObjectId(notification.get("pipeline_id"))})
        if workflow:
            can_take_action = str(current_user.id) in workflow.get("owner_ids", [])
    
    if not can_take_action:
        raise HTTPException(
            status_code=403, 
            detail="You don't have permission to take actions on this notification. Only admins or users with roles in allowed_roles can take actions."
        )


    #if already taken action
    if notification.get("alert") and notification.get("alert").get("action_executed_by"):
        action_user = await auth_crud.get_user_by_id(db, int(notification.get("alert").get("action_executed_by")))
        user_email = action_user.email if action_user else "another user"
        raise HTTPException(
            status_code=403,
            detail=f"Action already taken by {user_email}"
        )
    
    
    update_result = await notification_collection.update_one(
        {"_id": notification_obj_id},
        {
            "$set": {
                "alert.action_taken": action_data.action_taken,
                "alert.taken_at": datetime.now(),
                "alert.action_executed_by": str(current_user.id),
                "alert.status": "completed"  # Mark as completed when action is taken
            }
        }
    )

    return {
        "status": "success",
        "message": "Notification action updated successfully"
    }


@router.get("/charts")
async def fetch_charts_data(request: Request, current_user: User = Depends(get_current_user)):
    """
    Fetch chart data for Admin dashboard:
    - alerts_chart: Alerts per workflow (warning, error, info breakdown)
    - runtime_chart: Runtime per pipeline (bar chart)
    - rca_chart: RCA triggers over time
    """
    user_id = str(current_user.id)
    workflow_collection = request.app.state.workflow_collection
    notification_collection = request.app.state.notification_collection
    rca_collection = request.app.state.rca_collection
    
    query = {}
    if current_user.role != "admin":
        query = {"owner_ids": user_id}
    
    workflows = await workflow_collection.find(query).to_list(length=None)
    
    # Build queries for notifications and RCA events
    queries = [{"pipeline_id": str(pipeline["_id"])} for pipeline in workflows]
    
    notifications = []
    rca_events = []
    if queries:
        notifications = await notification_collection.find({"$or": queries}).to_list(length=None)
        rca_events = await rca_collection.find({"$or": queries}).to_list(length=None)
    
    # Build alerts chart data (per workflow breakdown)
    alerts_chart_data = []
    
    for workflow in workflows:
        workflow_id = str(workflow["_id"])
        workflow_name = workflow.get("name", f"Workflow")
        
        # Filter notifications for this workflow
        workflow_notifications = [n for n in notifications if n.get("pipeline_id") == workflow_id]
        
        # Count by type - map to chart categories
        warning_count = sum(1 for n in workflow_notifications if n.get("type") == "warning")
        error_count = sum(1 for n in workflow_notifications if n.get("type") in ["error", "alert"])  # critical
        info_count = sum(1 for n in workflow_notifications if n.get("type") in ["info", "success"])  # low
        
        alerts_chart_data.append({
            "workflow": workflow_name[:12],  # Truncate for chart display
            "warning": warning_count,
            "critical": error_count,
            "low": info_count
        })
    
    # Sort by total alerts (descending) and take top 8
    alerts_chart_data.sort(key=lambda x: x["warning"] + x["critical"] + x["low"], reverse=True)
    alerts_chart_data = alerts_chart_data[:8]
    
    # Build runtime chart data (runtime per pipeline - bar chart)
    runtime_chart_data = []
    for workflow in workflows:
        workflow_name = workflow.get("name", "Pipeline")
        runtime_seconds = workflow.get("runtime", 0)
        
        # Convert to appropriate unit for display
        if runtime_seconds >= 3600:
            runtime_value = round(runtime_seconds / 3600, 1)  # hours
            runtime_unit = "h"
        elif runtime_seconds >= 60:
            runtime_value = round(runtime_seconds / 60, 1)  # minutes
            runtime_unit = "m"
        else:
            runtime_value = runtime_seconds
            runtime_unit = "s"
        
        runtime_chart_data.append({
            "pipeline": workflow_name[:12],
            "runtime": runtime_seconds,  # Raw seconds for chart
            "runtime_display": f"{runtime_value}{runtime_unit}",
            "runtime_hours": round(runtime_seconds / 3600, 2)  # For bar chart (hours)
        })
    
    # Sort by runtime (descending) and take top 8
    runtime_chart_data.sort(key=lambda x: x["runtime"], reverse=True)
    runtime_chart_data = runtime_chart_data[:8]
    
    # Build RCA triggers chart data (time series)
    from collections import defaultdict
    
    rca_time_buckets = defaultdict(int)  # time -> count
    
    for rca_event in rca_events:
        try:
            triggered_at = rca_event.get("triggered_at") or rca_event.get("timestamp")
            if triggered_at:
                if isinstance(triggered_at, str):
                    triggered_at = datetime.fromisoformat(triggered_at.replace('Z', '+00:00'))
                time_key = triggered_at.strftime("%I:%M %p")
                rca_time_buckets[time_key] += 1
        except Exception:
            pass
    
    # Create RCA chart with last 6 time periods or defaults
    rca_labels = list(rca_time_buckets.keys())[-6:] if rca_time_buckets else ["10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM"]
    rca_values = [rca_time_buckets.get(label, 0) for label in rca_labels]
    
    rca_chart_data = {
        "labels": rca_labels,
        "datasets": [
            {
                "color": "#A2B8F4",  # Blue
                "values": rca_values
            }
        ]
    }
    
    # Total RCA count
    total_rca = len(rca_events)
    
    # RCA breakdown by workflow (for stats)
    rca_stats = []
    for workflow in workflows[:5]:  # Top 5 workflows
        workflow_id = str(workflow["_id"])
        workflow_name = workflow.get("name", "Workflow")
        
        wf_rca_count = sum(1 for r in rca_events if r.get("pipeline_id") == workflow_id)
        rca_stats.append({
            "workflow": workflow_name[:15],
            "count": wf_rca_count
        })
    
    return {
        "alerts_chart": alerts_chart_data,
        "runtime_chart": runtime_chart_data,
        "rca_chart": {
            "total": total_rca,
            "time_series": rca_chart_data,
            "stats": rca_stats
        }
    }
