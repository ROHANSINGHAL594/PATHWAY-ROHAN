from typing import List
import pathway as pw
import httpx
import os
from datetime import datetime
from lib.agents import AlertNode
from lib.notifications import add_notification
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

agentic_url = os.getenv("AGENTIC_URL")

class AlertResponseSchema(pw.Schema):
    type: str
    message: str

class GenerateAlert(pw.AsyncTransformer, output_schema=AlertResponseSchema):
    alert_node: AlertNode
    
    def __init__(self, alert_node: AlertNode, *args, **kwargs):
        self.alert_node = alert_node
        super().__init__(*args, **kwargs)
    
    async def invoke(self, **kwargs) -> dict:
        # Get alert from agentic service
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{agentic_url.rstrip('/')}/generate-alert",
                json=dict(
                    alert_prompt=self.alert_node.alert_prompt,
                    trigger_description=self.alert_node.input_trigger_description,
                    trigger_data=kwargs,
                ),
            )
            resp.raise_for_status()
            data = resp.json()
            alert = data["alert"]
        
        # Send notification to MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        if mongo_uri:
            try:
                mongo_client = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
                db = mongo_client[os.getenv("MONGO_DB", "db")]
                notification_collection = db[os.getenv("NOTIFICATION_COLLECTION", "notifications")]
                
                pipeline_id = os.getenv("PIPELINE_ID")
                notification_data = {
                    "pipeline_id": pipeline_id,
                    "title": f"Alert: {alert.get('type', 'info').upper()}",
                    "desc": alert.get("message", "Alert triggered"),
                    "type": "alert",
                    "timestamp": datetime.now(),
                    "alert": {
                        "actions": alert.get("actions", ["Acknowledge"]),
                        "action_taken": None,
                        "taken_at": None,
                        "action_executed_by": None,
                        "action_executed_by_user": None,
                        "status": "pending",
                        "alert_data": alert  # Original alert data from agentic service
                    },
                }
                
                await add_notification(notification_data, notification_collection)
            except Exception as e:
                # Log error but don't fail the pipeline
                print(f"Error sending notification: {e}")
        
        return alert

def alert_node_fn(inputs: List[pw.Table], alert_node: AlertNode):
    trigger_table = inputs[0]
    alerts = GenerateAlert(alert_node, input_table=trigger_table).successful
    return alerts
