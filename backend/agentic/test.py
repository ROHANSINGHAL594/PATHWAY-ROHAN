

import pathway as pw
from typing import Annotated, Sequence, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
import json


class EventSchema(pw.Schema):
    timestamp: str
    event_type: str
    event_data: str
    severity: str

rdkafka_settings = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "ambient_agent_group",
    "session.timeout.ms": "6000",
    "enable.auto.commit": "true",
    "auto.commit.interval.ms": "1000",
}

kafka_stream = pw.io.kafka.read(
    rdkafka_settings,
    topic="events_topic",
    schema=EventSchema,
    format="json",
    autocommit_duration_ms=1000
)


# Group by event_type to get all related events
event_history = kafka_stream.groupby(pw.this.event_type).reduce(
    event_type=pw.this.event_type,
    total_count=pw.reducers.count(),
    latest_severity=pw.reducers.any(pw.this.severity),
    latest_timestamp=pw.reducers.any(pw.this.timestamp),
    severity_variety=pw.reducers.count_distinct(pw.this.severity),
)

# Join current events with historical context
events_with_history = kafka_stream.join(
    event_history,
    pw.left.event_type == pw.right.event_type
).select(
    timestamp=pw.left.timestamp,
    event_type=pw.left.event_type,
    event_data=pw.left.event_data,
    severity=pw.left.severity,
    total_occurrences=pw.right.total_count,
    latest_severity_in_history=pw.right.latest_severity,
    severity_variety=pw.right.severity_variety,
)

class AgentState(TypedDict):
    """State maintained by the ambient agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    event_data: dict  # Current event
    event_history: dict  # Historical context
    decision: str
    action_taken: str
    confidence: float
from dotenv import load_dotenv
load_dotenv()
llm = ChatGroq(
    model="llama-3.1-8b-instant"
    
)


def analyze_event_with_history(state: AgentState) -> AgentState:
    """Analyze event with historical context"""
    event_data = state["event_data"]
    history = state["event_history"]
    
    system_prompt = SystemMessage(content="""
    You are an ambient agent monitoring system events in real-time.
    You have access to historical patterns of similar events.
    
    Consider:
    - Current event severity and type
    - Historical frequency of this event type
    - Pattern changes (is this more/less frequent than usual?)
    - Severity trends
    - Cumulative impact
    
    Respond with:
    1. Analysis of current event + patterns
    2. Whether action is needed (yes/no)
    3. Confidence level (0-1)
    """)
    
    history_context = f"""
    Historical Context for {event_data.get('event_type')}:
    - Total occurrences: {history.get('total_occurrences', 0)}
    - Latest severity: {history.get('latest_severity_in_history')}
    - Severity variety: {history.get('severity_variety')}
    """
    
    user_message = HumanMessage(content=f"""
    Current Event:
    Type: {event_data.get('event_type')}
    Severity: {event_data.get('severity')}
    Data: {event_data.get('event_data')}
    Timestamp: {event_data.get('timestamp')}
    
    {history_context}
    """)
    
    response = llm.invoke([system_prompt, user_message])
    
    state["messages"].append(user_message)
    state["messages"].append(response)
    state["decision"] = response.content
    
    return state

def determine_action(state: AgentState) -> Literal["take_action", "monitor", END]:
    """Determine action based on analysis"""
    decision = state["decision"].lower()
    event_severity = state["event_data"].get("severity", "low")
    history_count = state["event_history"].get("total_occurrences", 0)
    
    # Critical events always require action
    if event_severity == "critical":
        return "take_action"
    
    # Escalate if pattern indicates surge
    if history_count > 10 and "frequent" in decision:
        return "take_action"
    
    # Check LLM recommendation
    if "action is needed" in decision or "yes" in decision:
        return "take_action"
    
    if event_severity == "low":
        return END
    
    return "monitor"

def take_action(state: AgentState) -> AgentState:
    """Execute action with historical context"""
    event_data = state["event_data"]
    history = state["event_history"]
    
    action_prompt = HumanMessage(content=f"""
    Generate action plan based on:
    Current Event: {event_data}
    Historical Pattern: {history.get('total_occurrences')} previous occurrences
    
    Consider:
    - Severity trend
    - Frequency pattern
    - Likely root cause
    - Recommended mitigation
    """)
    
    action_response = llm.invoke([*state["messages"], action_prompt])
    
    state["messages"].append(action_prompt)
    state["messages"].append(action_response)
    state["action_taken"] = action_response.content
    
    print(f"ACTION TAKEN: {action_response.content}")
    return state

def monitor_event(state: AgentState) -> AgentState:
    """Monitor without action"""
    state["action_taken"] = "Monitoring - no immediate action required"
    print(f"MONITORING: {state['event_data'].get('event_type')}")
    return state

def create_ambient_agent() -> StateGraph:
    """Create the ambient agent workflow graph"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("analyze", analyze_event_with_history)
    workflow.add_node("take_action", take_action)
    workflow.add_node("monitor", monitor_event)
    
    workflow.set_entry_point("analyze")
    
    workflow.add_conditional_edges(
        "analyze",
        determine_action,
        {
            "take_action": "take_action",
            "monitor": "monitor",
            END: END
        }
    )
    
    workflow.add_edge("take_action", END)
    workflow.add_edge("monitor", END)
    
    return workflow.compile()

agent = create_ambient_agent()

@pw.udf
def process_event_with_agent(
    timestamp: str,
    event_type: str,
    event_data: str,
    severity: str,
    total_occurrences: int,
    latest_severity_in_history: str,
    severity_variety: int,
) -> pw.Json:
    """Process event through agent with historical context"""
    
    current_event = {
        "timestamp": timestamp,
        "event_type": event_type,
        "event_data": event_data,
        "severity": severity
    }
    
    event_history = {
        "total_occurrences": total_occurrences,
        "latest_severity_in_history": latest_severity_in_history,
        "severity_variety": severity_variety,
    }
    
    initial_state = {
        "messages": [],
        "event_data": current_event,
        "event_history": event_history,
        "decision": "",
        "action_taken": "",
        "confidence": 0.0
    }
    
    try:
        result = agent.invoke(initial_state)
        output = {
            "event_id": f"{event_type}_{timestamp}",
            "decision": result.get("decision", ""),
            "action": result.get("action_taken", ""),
            "status": "processed",
            "context_used": {
                "total_occurrences": total_occurrences,
                "severity_variety": severity_variety,
            }
        }
        return pw.Json(output)
    except Exception as e:
        print(f" Error: {e}")
        return pw.Json({
            "event_id": f"{event_type}_{timestamp}",
            "error": str(e),
            "status": "failed"
        })

# Process events with full context
processed_events = events_with_history.select(
    timestamp=pw.this.timestamp,
    event_type=pw.this.event_type,
    event_data=pw.this.event_data,
    severity=pw.this.severity,
    result=process_event_with_agent(
        pw.this.timestamp,
        pw.this.event_type,
        pw.this.event_data,
        pw.this.severity,
        pw.this.total_occurrences,
        pw.this.latest_severity_in_history,
        pw.this.severity_variety,
    )
)


processed_results = processed_events.select(
    timestamp=pw.this.timestamp,
    event_type=pw.this.event_type,
    status=pw.this.result["status"].as_str(),
    decision=pw.this.result["decision"].as_str(),
    action=pw.this.result["action"].as_str(),
)

pw.io.jsonlines.write(processed_results, "./agent_output.jsonl")

print("=" * 70)
print(" Starting Ambient Agent with Historical Context")
print("=" * 70)
print(f"Historical patterns: Tracked by event type")
print(f"Output: ./agent_output.jsonl")
print("=" * 70)

pw.run()
