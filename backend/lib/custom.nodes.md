# Creating Custom Nodes

This guide explains how to create custom nodes for the Pathway pipeline, including defining the schema, implementing mapping functions, and integrating them into the system.

## 1. Node Definition (Schema)

Nodes are defined as Pydantic models. They describe the configuration parameters required by the node.

### Location
Place your node definition in `backend/lib/`. You can use existing subfolders like `tables`, `agents`, or create a new one.

### Example (`backend/lib/tables/my_node.py`)
```python
from typing import Literal
from ..node import Node  # Base class
from .base import TableNode # Or other base classes like TemporalNode

class MyCustomNode(TableNode):
    node_id: Literal["my_custom_node"]  # Unique ID
    category: Literal["table"]          # Category for frontend grouping
    param1: str
    param2: int = 10
    n_inputs: Literal[1] = 1            # Number of input tables expected
```

### Registration
Ensure your node class is exported in the `__init__.py` of its directory so it can be discovered by the backend.

**`backend/lib/tables/__init__.py`**:
```python
from .my_node import MyCustomNode

__all__ = [
    # ... existing nodes
    "MyCustomNode"
]
```

## 2. Mapping Function (Logic)

The mapping function defines how the node transforms input tables into an output table using Pathway.

### Location
Place your mapping logic in `backend/pipeline/mappings/`.

### Example (`backend/pipeline/mappings/my_node.py`)
```python
import pathway as pw
from typing import List
from lib.tables import MyCustomNode # Import your schema

def my_custom_node_fn(inputs: List[pw.Table], node: MyCustomNode) -> pw.Table:
    table = inputs[0]
    
    # Implement your logic using Pathway expressions
    result = table.select(
        *pw.this,
        new_col = pw.this[node.param1] + node.param2
    )
    return result
```

### Registration
Register your mapping function in `backend/pipeline/mappings/__init__.py`.

**`backend/pipeline/mappings/__init__.py`**:
```python
from .my_node import my_custom_node_fn

# ...

mappings = {
    # ... existing mappings
    "my_custom_node": {
        "node_fn": my_custom_node_fn,
        "stringify": lambda node, inputs: f"Adds {node.param2} to column {node.param1}"
    }
}
```

## 3. Frontend Integration

Nodes are automatically rendered in the frontend based on the schema served by the backend.

-   **Visibility**: The backend scans `backend/lib` for Pydantic models inheriting from `Node`.
-   **Category**: The `category` field in your node class determines which group it appears in (e.g., `table`, `agent`, `io`).
    -   `backend.lib.io_nodes` -> `io_nodes`
    -   `backend.lib.tables` -> `table_nodes`
    -   `backend.lib.agents` -> `agent_nodes`
-   **Stringify**: The `stringify` function provided in the `mappings` dictionary is used to generate a description of the node's operation, which is used as context for LLM calls.

## 4. Deployment Context

### Pipeline Nodes (Standard)
If your node logic only uses Pathway libraries and standard Python packages:
1.  Ensure any new dependencies are in `backend/pipeline/requirements.txt`.
2.  The code is automatically included in the pipeline container build.

### Service Nodes (External Services)
If your node requires a separate service (e.g., a heavy ML model, a database, or an agent):

1.  **Create Service**:
    -   Create a folder (e.g., `backend/my_service/`).
    -   Add `Dockerfile`, `requirements.txt`, and `app.py` (FastAPI recommended).
    
2.  **Docker Integration**:
    -   **Development**: Add the service to `backend/docker-compose.yaml`.
    -   **Production/Orchestration**: Update `backend/api/dockerScript.py` to spin up your service container alongside the pipeline.
        -   Define image name.
        -   Update `run_pipeline_container` to start your container, add it to the pipeline network, and pass its URL to the pipeline container.
        -   Update `stop_docker_container` to handle cleanup.

3.  **Connection**:
    -   In your mapping function, use `httpx` or similar to call your service's endpoints.
    -   Use environment variables (passed by `dockerScript.py`) to get the service URL.

    ```python
    import os
    import httpx
    
    SERVICE_URL = os.getenv("MY_SERVICE_URL")
    
    # ... inside AsyncTransformer or similar
    async def invoke(self, x):
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{SERVICE_URL}/predict", json={"data": x})
            return resp.json()
    ```

## 5. Logging and Live Alerts

To send live alerts to the dashboard:

1.  **Compute Alerts**: Create a table containing alert data.
2.  **Write to Kafka**: Use `pw.io.kafka.write` to send data to the `alert_{pipeline_id}` topic.

```python
import os
import pathway as pw

def alert_logic(inputs, node):
    alerts_table = ... # Compute alerts
    
    pipeline_id = os.getenv("PIPELINE_ID")
    
    # Kafka Configuration
    config = {
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVER", "host.docker.internal:9094"),
        "client.id": pipeline_id,
        # ... SASL config if needed
    }
    
    # Write to specific topic
    pw.io.kafka.write(
        alerts_table,
        rdkafka_settings=config,
        topic_name=f"alert_{pipeline_id}",
        format="json"
    )
    return alerts_table
```

The backend automatically listens to this topic and forwards messages to the frontend via WebSocket.
