import asyncio
from typing import List, Union, Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from lib.agents import Agent
from .sql_tool import TablePayload, create_sql_tool
from .llm_factory import create_agent_model
from langchain_mcp_adapters.client import MultiServerMCPClient
import os
from datetime import datetime
from lib.notifications import add_notification
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from .graph_state import Action


class Plan(BaseModel):
    actions: List[Action]
    reasoning: str = Field(description="Reasoning behind the plan")
    execution_strategy: Literal["complete","staged"]

class CANNOT_EXECUTE_Plan(BaseModel):
    reason: str= Field(description="Reason why the request cannot be processed by our agentic system")

class RagTool(BaseModel):
    tool_id: Literal["rag"]
    tool_description: str
    port: int

class AlertTool(BaseModel):
    tool_id: Literal["alert"]

class AgentPayload(Agent):
    tools: List[Union[TablePayload, RagTool, AlertTool, str]]

# Create agent model using the factory
# This will use the default provider (Groq) with agent-optimized settings
# To change provider, set DEFAULT_AGENT_PROVIDER environment variable
model = create_agent_model()

def create_alert_tool():
    """Create an alert tool that sends notifications using add_notification"""
    @tool
    async def send_alert(
        title: str,
        description: str,
        alert_type: str = "alert",
    ) -> str:
        """
        Send an alert notification to the system.
        
        Args:
            title: The title of the alert
            description: Detailed description of the alert
            alert_type: Type of alert (default: 'alert', can be 'warning', 'error', 'info', 'success')
        
        Returns:
            Status message indicating if the alert was sent successfully
        """
        # Get environment variables directly

        
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            return "Error: MONGO_URI environment variable not set. Cannot send alert."
        
       
        try:
            # Connect to MongoDB
            mongo_client = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
            db = mongo_client[os.getenv("MONGO_DB", "db")]
            notification_collection = db[os.getenv("NOTIFICATION_COLLECTION", "notifications")]
            
            notification_data = {
                "pipeline_id": os.getenv("PIPELINE_ID"),
                "title": title,
                "desc": description,
                "type": alert_type,
                "timestamp": datetime.now(),
            }
            
            # Add alert structure for actionable alerts
            if alert_type == "alert":
                notification_data["alert"] = {
                    "actions": ["Acknowledge", "Dismiss"],
                    "action_taken": None,
                    "taken_at": None,
                    "action_executed_by": None,
                    "action_executed_by_user": None,
                    "status": "pending"
                }
            
            result = await add_notification(notification_data, notification_collection)
            return f"Alert sent successfully: {title}"
        except Exception as e:
            return f"Error sending alert: {str(e)}"
    
    return send_alert

def build_agent(agent: AgentPayload) -> BaseTool:
    agent.name = agent.name.replace(" ", "_")
    # TODO: Implement alert tool

    tool_tables = [tool for tool in agent.tools if isinstance(tool,TablePayload)]
    tool_rags = [tool for tool in agent.tools if isinstance(tool,RagTool)]
    tool_alerts = [tool for tool in agent.tools if isinstance(tool,AlertTool)]
    tools = []
    table_descriptions = None
    rag_descriptions = []
    alert_description = None
    
    # Add SQL query tools for database tables
    if len(tool_tables) > 0: 
        query_tool, _table_descriptions= create_sql_tool(tool_tables, agent.name)
        table_descriptions = _table_descriptions
        tools.append(query_tool)

    # Add RAG tools via MCP client connection
    if len(tool_rags) > 0:
        for rag_tool in tool_rags:
            # Connect to the RAG node's MCP server
            mcp_client = MultiServerMCPClient({
                f"rag_{rag_tool.port}": {
                    "transport": "streamable_http",
                    "url": f"http://localhost:{rag_tool.port}/mcp",
                }
            })
            
            # Get tools from the MCP server (synchronous call in init)
            import asyncio
            rag_mcp_tools = asyncio.run(mcp_client.get_tools())
            tools.extend(rag_mcp_tools)
            
            # Build description for this RAG tool
            rag_descriptions.append(
                f"- RAG Document Store: {rag_tool.tool_description}\n"
                f"  Access via MCP server on port {rag_tool.port}\n"
                f"  Use the provided tools to search and retrieve relevant documents"
            )
    
    # Add alert tool
    if len(tool_alerts) > 0:
        alert_tool = create_alert_tool()
        tools.append(alert_tool)
        alert_description = (
            "- Alert System: Send notifications and alerts to the system\n"
            "  Use this tool to create alerts when important events or issues are detected\n"
            "  Alerts will be visible in the notification center"
        )
    
    # Build system prompt with RAG and Alert tool instructions
    rag_instructions = ""
    if len(rag_descriptions) > 0:
        rag_instructions = (
            "\n\nRAG TOOL USAGE:\n"
            "You have access to document retrieval tools (RAG - Retrieval Augmented Generation).\n"
            + "\n".join(rag_descriptions) + "\n"
            "When a query requires knowledge from documents, use these tools to search and retrieve relevant information.\n"
        )
    
    alert_instructions = ""
    if alert_description:
        alert_instructions = (
            "\n\nALERT TOOL USAGE:\n"
            "You have access to an alert system tool.\n"
            f"{alert_description}\n"
            "Use this tool to send notifications when:\n"
            "- Critical issues or errors are detected\n"
            "- Important thresholds are exceeded\n"
            "- Significant events occur that require attention\n"
        )
    
    agent_system_prompt = (
        f"You are an agent with the following description:\n{agent.description}\n\n"
        
        "OUTPUT RULES (CRITICAL):\n"
        "1. Answer ONLY what is explicitly requested\n"
        "3. Do NOT provide additional context, related fields, or explanations unless requested\n"
        "4. Format: Clear, natural language with actual values\n"
        "5. Convert raw data (objects, tuples, SQL results) into readable sentences\n"
        f"{rag_instructions}"
        f"{alert_instructions}"
    )
        
    langchain_agent = create_agent(model=model, system_prompt=agent_system_prompt, tools=tools)
    agent_description = f"This is an agent with the following description:\n{agent.description}"
    
    if len(tool_tables) > 0:
        agent_description += f"\nIt has read access to the following postgres tables:\n{table_descriptions}"
    
    if len(rag_descriptions) > 0:
        agent_description += "\nIt has access to the following document stores (RAG):\n" + "\n".join(rag_descriptions)
    
    if alert_description:
        agent_description += "\nIt has access to an alert system for sending notifications"
    
    langchain_agent.description = agent_description
    langchain_agent.name = agent.name
    return langchain_agent
    # @tool(agent.name, description=agent_description)
    # async def secure_agent_tool(request: str) -> str:
    #     """securely execute an agent request"""
    #     issues = await gateway.scan_text_for_issues(request)
    #     if issues:
    #         raise ValueError(f"Request failed security checks: {', '.join(issues)}")
        
    #     result = await langchain_agent.ainvoke({"input": request})
    #     return result
    
    # return secure_agent_tool

def create_planner_executor(_agents: List[AgentPayload]):
    langchain_agents = [build_agent(_agent) for _agent in _agents]
    tool_descriptions = "\n".join(
        f"{i + 1}. {tool.name}(request: str)\n{tool.description}"
        for i, tool in enumerate(langchain_agents)
    )
    
    num_tools = len(_agents)
    planner_prompt = (
        f"You are a plan generator using {num_tools} available agents.\n\n"
        
        f"AGENTS:\n{tool_descriptions}\n\n"
        
        "PLANNING RULES:\n"
        "1. actions: List[Action(id: int, agent: exact_agent_name, request: str)]\n"
        "   - IDs start at 1 and increment sequentially\n"
        "   - Agent names must exactly match the list above (case-sensitive)\n"
        "2. Dependencies: Reference prior action outputs as $1, $2, etc. in request strings\n"
        "   - Example: 'Calculate profit margin from revenue $1 and expenses $2'\n"
        "   - Escape literal dollars: Write \\$100 to represent the value '$100'\n"
        "3. Validation: Trace $id references to ensure no circular dependencies\n"
        "   - INVALID: Action 1 uses $2, Action 2 uses $1 (cycle)\n"
        "4. No conditionals in action requests (no if/else logic)\n"
        "   - If conditionals are required, use staged execution\n\n"
        
        "EXECUTION STRATEGIES:\n"
        "complete: Plan all steps upfront when the full solution is deterministic\n"
        "  - Use when: All actions are independent or have clear $id dependencies\n"
        "  - After execution: An aggregator receives your reasoning + all outputs\n"
        "  - The aggregator synthesizes the final answer, so focus on data gathering\n\n"
        "  - Example: 'Get revenue, get expenses, calculate margin' - all steps known\n\n"
        
        "staged: Plan partial steps, inspect results, then replan (USE SPARINGLY)\n"
        "  - Use ONLY when: Next actions genuinely depend on runtime values\n"
        "  - Good use: 'Check if table X exists, then query it or return error'\n"
        "  - Bad use: 'Get sales data, THEN calculate average' (use complete + $1)\n"
        "  - After stage 1: You'll be re-invoked with outputs to plan next actions\n"
        "  - Once dependencies resolve, switch to 'complete' for final gathering\n\n"
        "  - Only plan the actions that we must definitely take in this case i.e their execution does not depend on a conditional"
        
        "REASONING FIELD (2-3 sentences):\n"
        "- For execution_strategy = completed, Explain how the actions taken will help the aggregator solve the task given by the user\n"
        "- If staged: Explain what you plan to do next once the planned actions are executed\n\n"
        
        "EXAMPLE (complete strategy):\n"
        "Query: 'What was Q4 profit margin?'\n"
        "Plan:\n"
        "  actions:\n"
        "    - id: 1, agent: 'finance_agent', request: 'Get total revenue for Q4 2024'\n"
        "    - id: 2, agent: 'finance_agent', request: 'Get total expenses for Q4 2024'\n"
        "    - id: 3, agent: 'finance_agent', request: 'Calculate profit margin using revenue $1 and expenses $2'\n"
        "  reasoning: 'Actions 1-2 run in parallel (no deps). Action 3 waits for both. Aggregator will format final percentage.'\n"
        "  execution_strategy: 'complete'\n\n"
        
        "EXAMPLE (staged strategy):\n"
        "Query: 'Show sales for product XYZ if it exists'\n"
        "Stage 1:\n"
        "  actions:\n"
        "    - id: 1, agent: 'inventory_agent', request: 'Check if product XYZ exists in catalog'\n"
        "  reasoning: 'Must verify existence before querying sales. Will plan sales query or error response in stage 2.'\n"
        "  execution_strategy: 'staged'\n"
        "[After stage 1, you receive result and plan next actions based on existence]\n\n"
        
        "CANNOT_EXECUTE (return instead of Plan):\n"
        "Use when the request is fundamentally impossible:\n"
        "- No agent has access to required data sources\n"
        "  Example: Query asks for customer_churn but no agent has that table\n"
        "- Missing capability: 'Predict future sales' but no ML/forecasting agent\n"
        "- Cross-database JOIN required but no single agent has both tables\n\n"
        "Format:\n"
        "  reason: 'Cannot execute: No agent has access to customer_churn table. Available tables: sales_data (finance_agent), inventory (warehouse_agent). Suggest: Rephrase query using available data or add agent with churn table access.'\n\n"
        
        "OUTPUT: Return Plan or CANNOT_EXECUTE_Plan model.\n"
    )
    
    planner_executor = create_agent(model, system_prompt=planner_prompt, response_format=ToolStrategy(Union[Plan, CANNOT_EXECUTE_Plan]))
    return planner_executor, planner_prompt, langchain_agents
