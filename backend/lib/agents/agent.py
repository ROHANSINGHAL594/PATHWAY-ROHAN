from pydantic import BaseModel
from typing import List, Literal, get_args, get_origin, Union, Optional
from . import tools
import inspect
from pydantic import field_validator


def get_tool_class_map():
    """
    Collect all tool classes from lib/tools.py
    that define a class attribute `tool_id`, and return a mapping
    of tool_id -> class reference.
    """
    tool_class_map = {}
    modules = [tools]

    for module in modules:
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            if 'tool_id' in cls.model_fields:
                tool_id_type = cls.model_fields['tool_id'].annotation
                if not (get_origin(tool_id_type) is Literal):
                    continue
                node_id_value = get_args(tool_id_type)[0]
                tool_class_map[node_id_value] = cls

    return tool_class_map

tool_map = get_tool_class_map()


class Agent(BaseModel):
    name: str
    description: str
    tools : Optional[List[Union[int,str]]] = []
    rag_nodes : List[int]
    @field_validator("tools")
    def check_tools(cls, tools):
        for t in tools:
            if isinstance(t, str) and t not in tool_map:
                raise ValueError(f"Unknown tool: {t}")
        return tools
