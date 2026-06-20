from typing import List, Dict, Union, Literal
import json
from pydantic import BaseModel
from lib.agents import AlertResponse
from langchain.agents import create_agent
from .prompts import model


alert_agent = create_agent(
    model=model,
    tools=[],
    response_format=AlertResponse
)

class AlertRequest(BaseModel):
    alert_prompt: str
    trigger_description: str
    trigger_data: Dict

async def generate_alert(alert_request: AlertRequest):
    full_prompt = (
        "Generate a structured alert based on the following information:\n\n"
        
        f"ALERT PURPOSE: {alert_request.alert_prompt}\n\n"
        
        f"TRIGGER CONDITION:\n{alert_request.trigger_description}\n\n"
        
        f"TRIGGER DATA:\n{json.dumps(alert_request.trigger_data, indent=2)}\n\n"
        
        "ALERT TYPE CRITERIA:\n"
        "- 'error': Critical failures, system errors, data corruption, security breaches\n"
        "- 'warning': Threshold exceeded, degraded performance, approaching limits, anomalies\n"
        "- 'info': Routine notifications, status updates, successful operations\n\n"
        
        "RESPONSE REQUIREMENTS:\n"
        "- Select the appropriate alert type based on severity\n"
        "- Write a concise message explaining what happened and why it matters\n"
        "- Include relevant values from trigger data (timestamps, counts, identifiers)\n"
        "- Keep message under 200 characters for dashboard display"
    )
    
    answer = await alert_agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        }
    )
    alert : AlertResponse = answer["structured_response"]
    return {"status": "ok", "alert": alert}
