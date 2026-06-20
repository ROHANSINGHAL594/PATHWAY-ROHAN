from typing import TypedDict, List, Literal, Annotated
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

class Action(BaseModel):
    id: int
    agent: str = Field(description="Agent name to call")
    request: str = Field(description="Natural language request to the agent")


class ActionResult(BaseModel):
    """Result from executing a single action"""
    action_id: int
    agent_name: str
    request: str
    output: str
    error: str | None = None


class GraphState(TypedDict):
    """State for the plan-execute-aggregate workflow"""
    # User input
    query: str
    
    # Planning state
    current_plan: List[Action] | None  # FIX: Allow None for initialization
    plan_reasoning: str
    execution_strategy: Literal["complete", "staged"]
    
    # Execution state
    action_results: List[ActionResult]  # This is fine as list can be empty []
    
    # Aggregator state
    aggregator_decision: Literal["finish", "replan"] | None
    aggregator_thought: str | None
    final_answer: str | None
    
    # Control flow
    replan_count: int  # Prevent infinite loops
    error_message: str | None  # For CANNOT_EXECUTE scenarios
