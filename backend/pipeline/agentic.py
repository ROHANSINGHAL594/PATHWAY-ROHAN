from typing import List, Dict, Literal, Type
from lib.agents import Agent
from lib.node import Node
from postgres_util import construct_table_name
import pathway as pw
import json
import os
import httpx
import requests


agentic_url = os.getenv("AGENTIC_URL")




class AgentOutputSchema(pw.Schema):
    prompt: str
    answer: str
    caller: str



def build_agentic_graph(
    agents: List[Agent],
    pipeline_name: str,
    nodes: List[Node],
    node_outputs: List[pw.Table],
) -> Dict[Literal["prompt", "trigger"], pw.AsyncTransformer]:

    payload = []
    for i,agent in enumerate(agents):
        # Build table-backed tool context (when agent.tools contains int indexes into `nodes`)
        tool_tables = []
        other_tools = []
        if getattr(agent, "tools", None):
            for t in agent.tools:
                if isinstance(t, int):
                    if t < 0 or t >= len(nodes):
                        raise IndexError(f"Tool index {t} out of range for nodes.")
                    node = nodes[t]
                    if not hasattr(node, "tool_description") or not node.tool_description:
                        raise ValueError(f"Node at index {t} must have tool_description.")
                    if node.node_id == "rag_node":
                        port = node_outputs[t]
                        other_tools.append({
                            "tool_id": "rag",
                            "tool_description": node.tool_description,
                            "port": port
                        })
                        continue
                    out_tbl = node_outputs[t]
                    tool_tables.append({
                        "table_name": construct_table_name(node.node_id, t),
                        "table_schema": out_tbl.schema.columns_to_json_serializable_dict(),
                        "description": node.tool_description,
                    })
                else:
                    # Handle alert tool
                    if t == "alert":
                        other_tools.append({
                            "tool_id": "alert",
                        })

        payload.append({
            "name": agent.name,
            "description": agent.description,
            "tools": [*tool_tables, *other_tools],
        })

       
    url = agentic_url.rstrip("/") + "/build"
    resp = requests.post(url, json={"agents": payload, "pipeline_name": pipeline_name}, timeout=60)
    resp.raise_for_status()
   

    class SupervisorPromptTransformer(pw.AsyncTransformer, output_schema=AgentOutputSchema):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        async def infer(self, role: str, content: str) -> str:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{agentic_url.rstrip('/')}/infer",
                    json={"role": role, "content": content},
                )
                resp.raise_for_status()
                data = resp.json()
                return data["answer"]
        
        async def invoke(self, prompt: str) -> dict:
            return {
                "caller": "user",
                "prompt": prompt,
                "answer": await self.infer("user", prompt),
            }

    class SupervisorTriggerTransformer(SupervisorPromptTransformer, output_schema=AgentOutputSchema):
        def __init__(
            self,
            trigger_name: str,
            trigger_description: str,
            trigger_schema: Type[pw.Schema],
            *args,
            **kwargs,
        ):
            self.trigger_name = trigger_name
            self.trigger_description = trigger_description
            self.trigger_schema = trigger_schema
            super().__init__(*args, **kwargs)

        async def invoke(self, **kwargs):
            prompt = (
                "This is a trigger from a table.\n"
                f"Schema: {json.dumps(self.trigger_schema.columns_to_json_serializable_dict(), indent=4)}\n"
                f"Description: {self.trigger_description}\n"
                f"New row: {json.dumps(kwargs, indent=4)}\n"
                "This row is a new addition to the table. "
            )
            answer = await self.infer("trigger", prompt)
            return {
                "caller": self.trigger_name,
                "prompt": prompt,
                "answer": answer,
            }

    return dict(prompt=SupervisorPromptTransformer, trigger=SupervisorTriggerTransformer)
