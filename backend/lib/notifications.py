"""
Notification utilities for adding notifications to the database.
"""
from datetime import datetime
from typing import Any, Dict
from bson import ObjectId


def serialize_mongo(doc):
    """
    Serialize MongoDB documents for JSON response.
    Converts ObjectId and datetime objects to string/ISO format.
    """
    if isinstance(doc, ObjectId):
        return str(doc)
    
    if isinstance(doc, datetime):
        return doc.isoformat()

    if isinstance(doc, list):
        return [serialize_mongo(x) for x in doc]

    if isinstance(doc, dict):
        return {k: serialize_mongo(v) for k, v in doc.items()}

    return doc


async def add_notification(
    notification_data: Dict[str, Any],
    notification_collection
) -> Dict[str, Any]:
    """
    Add a notification to the database.
    
    Args:
        notification_data: Dictionary containing notification data with keys:
            - pipeline_id (str): The pipeline ID
            - title (str): Notification title
            - desc (str): Notification description
            - type (str): Notification type (success, error, warning, info, alert)
            - timestamp (datetime, optional): Timestamp, defaults to now
            - alert (dict, optional): Alert details if type is "alert", containing:
                * actions (List[str]): Available actions
                * action_taken (str | None): Action taken
                * taken_at (datetime | None): When action was taken
                * action_executed_by (str | None): User ID who executed
                * action_executed_by_user (Any | None): User object
                * status (str): "pending", "completed", "rejected", or "ignored"
            - remediation_metadata (dict, optional): Only for runbook approvals
        notification_collection: MongoDB collection for notifications
    
    Returns:
        Dictionary with status, inserted_id, and inserted_data
        
    Note:
        The change stream watcher will automatically broadcast via WebSocket.
    """
    # Ensure timestamp is set
    if "timestamp" not in notification_data or not notification_data["timestamp"]:
        notification_data["timestamp"] = datetime.now()

    # Insert notification into database
    # The watch_notifications change stream will automatically broadcast it via WebSocket
    result = await notification_collection.insert_one(notification_data)

    return serialize_mongo({
        "status": "success",
        "inserted_id": str(result.inserted_id),
        "inserted_data": notification_data
    })
