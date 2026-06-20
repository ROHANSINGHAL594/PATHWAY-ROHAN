from pydantic import BaseModel
from typing import Optional

# Base Node Class
class Node(BaseModel):
    category: str
    node_id: str
    # this field describes the description of the node IF it is to be used as a tool
    tool_description: Optional[str] = ""
    trigger_description: Optional[str] = ""