from pydantic import BaseModel
from typing import Type, Literal

# Base Tool Class
class Tool(BaseModel):
    tool_id: str

    # this field describes the description of the node IF it is to be used as a tool
    tool_description: str 

    tool_schema: Type[BaseModel]

class Human(Tool):
    pass