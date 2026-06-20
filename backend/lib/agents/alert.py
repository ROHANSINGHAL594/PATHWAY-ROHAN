from ..node import Node
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    type: Literal["warning","error","info"] = Field(description="Alert type")
    message: str = Field(description="Alert message")

class AlertNode(Node):
    node_id : Literal["alert"]
    category: Literal["action"]
    alert_prompt: str
    n_inputs: Literal[1] = 1
    model_config = ConfigDict(extra="allow")
