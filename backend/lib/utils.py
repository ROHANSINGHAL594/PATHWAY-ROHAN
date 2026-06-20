import inspect
from typing import Dict, Literal, Optional, get_args, get_origin
from typing_extensions import TypedDict
from pydantic import BaseModel
from . import io_nodes
from . import tables
from . import agents
from . import trigger_rca
from .open_tel import input_nodes
from .types import RdKafkaSettings

def get_node_class_map():
    """
    Collect all node classes from lib/io_node.py, lib/tables.py, and lib/rag.py
    that define a class attribute `node_id`, and return a mapping
    of node_id -> class reference.
    """
    node_map = {}
    modules = [
        io_nodes,
        tables,
        agents,
        trigger_rca,
        input_nodes
    ]

    for module in modules:
        for name, cls in inspect.getmembers(module, inspect.isclass):
            # Check if class is defined in this module or its submodules
            if not cls.__module__.startswith(module.__name__):
                continue
            if not issubclass(cls, BaseModel):
                continue
            if 'node_id' in cls.model_fields:
                node_id_type = cls.model_fields['node_id'].annotation
                if not (get_origin(node_id_type) is Literal):
                    continue
                node_id_value = get_args(node_id_type)[0]
                node_map[node_id_value] = cls

    return node_map


node_map = get_node_class_map()


if __name__ == "__main__":
    for nid, cls in node_map.items():
        print(f"{nid}: {cls.__name__}")
