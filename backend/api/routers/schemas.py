from pydantic import BaseModel
from typing import Any, Dict, Optional, Type, Union, List, get_args, get_origin, Literal
from fastapi import APIRouter, Request, status, HTTPException
from backend.lib.utils import node_map
import inspect


router = APIRouter()
NODES: Dict[str, BaseModel] = node_map


def get_base_pydantic_model(model_class: type) -> type:
    """
    Traverses the Method Resolution Order (MRO) of a class to find the first
    Pydantic BaseModel subclass.
    """
    mro = getattr(model_class, "__mro__", ())
    for i, cls in enumerate(mro):
        if cls is BaseModel:
            return mro[i - 1] if i > 0 else cls
    return model_class


def get_schema_for_node(node: Union[str, Type[Any]]) -> dict:
    """
    Retrieves the Pydantic JSON schema for a given node type.
    """
    if inspect.isclass(node):
        cls: Optional[Type[Any]] = node
    else:
        cls = NODES.get(node)

    if cls is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"node not found: {node}")

    if not (inspect.isclass(cls) and issubclass(cls, BaseModel)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="node is not a Pydantic model class")

    if hasattr(cls, "model_json_schema"):
        schema = cls.model_json_schema(mode='serialization')
    else:
        schema = cls.model_json_schema(mode='serialization')

    return schema



@router.get("/all")
def schema_index(request: Request):
    """
    Returns category wise list of all available node types.
    """
    result: Dict[str, List[str]] = {}
    for node_id, cls in NODES.items():
        category = 'uncategorized'
        if 'category' in cls.model_fields:
            field_info = cls.model_fields['category']
            # Check if it is a Literal
            if get_origin(field_info.annotation) is Literal:
                 args = get_args(field_info.annotation)
                 if args:
                     category = args[0]
        
        if category not in result:
            result[category] = []
        result[category].append(node_id)
    return result

@router.get("/{node_name}")
def schema_for_node(node_name: str):
    """
    Returns the JSON schema for a specific node type.
    """
    schema_obj = get_schema_for_node(node_name)
    return schema_obj   
