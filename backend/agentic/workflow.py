from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from typing import List, Union
from pydantic import BaseModel, Field
from .graph_state import GraphState
from .prompts import (
    create_planner_executor,
    AgentPayload,
    Plan,
    CANNOT_EXECUTE_Plan,
    model
)

from .llm_factory import create_reasoning_model
from .executor import PlanExecutor

reasoning_model = create_reasoning_model()
MAX_REPLAN_CYCLES = 3

class AggregatorFinish(BaseModel):
    thought: str = Field(description="Brief reasoning about how action results address the question")
    final_answer: str = Field(description="Complete, helpful answer based on gathered data")

class AggregatorReplan(BaseModel):
    replan_reasoning: str = Field(description="Explanation of what's missing and why replanning is needed, including any errors to avoid")

aggregator_prompt = (
    "You are an aggregator that synthesizes final answers from action results.\n"
    "\n"
    "CONTEXT:\n"
    "- You receive the planner's reasoning explaining their strategy\n"
    "- You receive outputs from all executed actions (labeled $1, $2, etc.)\n"
    "- You receive any errors that occurred during action execution\n"
    "- Your job is to combine these results into a coherent, complete answer\n"
    "\n"
    "AGGREGATION SCENARIOS:\n"
    "You will be called in three situations:\n"
    "1. NORMAL: After plan execution completes - synthesize results and decide if answer is complete\n"
    "2. CANNOT_EXECUTE: Planner/replanner determined query is impossible - provide helpful explanation\n"
    "3. MAX_REPLANS_REACHED: Replan limit exceeded - synthesize best answer from available results\n"
    "\n"
    "GUIDELINES:\n"
    "1. Focus on answering the user's original question directly\n"
    "2. Use the planner's reasoning to understand the strategy behind the actions\n"
    "3. Use data from multiple action outputs when needed\n"
    "4. Ignore irrelevant action results\n"
    "5. Present information in clear, natural language\n"
    "6. If critical information is missing despite all actions, state what's missing\n"
    "\n"
    "ERROR HANDLING:\n"
    "- If errors occurred during execution, analyze whether:\n"
    "  - The available results are still sufficient to answer the query (Finish with partial answer)\n"
    "  - Different actions or approaches could work around the errors (Replan with specific guidance)\n"
    "  - The errors are fundamental blockers (Finish explaining the limitation)\n"
    "- When replanning due to errors, provide specific instructions on how to avoid repeating the same mistakes\n"
    "\n"
    "RESPONSE FORMAT:\n"
    "You must return either AggregatorFinish or AggregatorReplan:\n"
    "\n"
    "AggregatorFinish:\n"
    "- thought: Brief reasoning about how action results address the question\n"
    "- final_answer: Complete, helpful answer based on gathered data\n"
    "\n"
    "AggregatorReplan:\n"
    "- replan_reasoning: Detailed explanation including:\n"
    "  * What information is missing or what went wrong\n"
    "  * Why replanning is needed\n"
    "  * Specific guidance on avoiding previous errors\n"
    "  * What alternative approaches should be tried\n"
    "\n"
    "DECISION CRITERIA:\n"
    "- If action results provide sufficient information → AggregatorFinish with synthesized answer\n"
    "- If errors occurred but results are adequate → AggregatorFinish acknowledging limitations\n"
    "- If critical data is missing AND replans available → AggregatorReplan with error analysis\n"
    "- If CANNOT_EXECUTE or MAX_REPLANS_REACHED → AggregatorFinish (replanning not allowed)\n"
    "\n"
    "OUTPUT: Return AggregatorFinish or AggregatorReplan model."
)



def create_workflow(agents: List[AgentPayload]):
    """Create the LangGraph workflow for plan-execute-aggregate architecture"""
    
    # Initialize components
    planner, planner_prompt, langchain_agents = create_planner_executor(agents)
    replanner_prompt = planner_prompt + (
        "\n\n"
        "REPLANNING INSTRUCTIONS:\n"
        "- You are given the \"Previous Plan\" with execution results (Observations) and overall feedback (Thought)\n"
        "- ANALYZE what worked, what failed, and why (look for error patterns)\n"
        "- Your \"Current Plan\" must LEARN from failures:\n"
        "  * If an action failed, try alternative approaches or agents\n"
        "  * If data was missing, try different data sources or queries\n"
        "  * If dependencies failed, adjust the dependency chain\n"
        "- NEVER repeat the exact same actions from the Previous Plan\n"
        "- Continue task numbering from where the previous plan ended (start at next available ID)\n"
        "- If the feedback indicates the query is fundamentally impossible, return CANNOT_EXECUTE\n"
        "- Focus on filling gaps identified in the feedback, not redoing successful actions\n"
        "- Reference previous results using $N notation where helpful\n"
    )
    replanner_agent = create_agent(
            reasoning_model,
            system_prompt=replanner_prompt,
            response_format=ToolStrategy(Union[Plan, CANNOT_EXECUTE_Plan])
    )
    aggregator_agent = create_agent(
            model,
            system_prompt=aggregator_prompt,
            response_format=ToolStrategy(Union[AggregatorFinish, AggregatorReplan])
    )
    executor = PlanExecutor(langchain_agents)
    
    

    async def planning_node(state: GraphState) -> GraphState:
        """Generate initial plan or handle CANNOT_EXECUTE"""
        query = state["query"]
        
        # Invoke planner
        result = await planner.ainvoke({"messages": [{"role": "user", "content": query}]})
        plan_output = result["structured_response"]
        
        # Check if it's CANNOT_EXECUTE
        if isinstance(plan_output, CANNOT_EXECUTE_Plan):
            return {
                **state,
                "error_message": plan_output.reason,
                "final_answer": f"Unable to process query: {plan_output.reason}",
            }
        
        plan: Plan = plan_output
        return {
            **state,
            "current_plan": plan.actions,
            "plan_reasoning": plan.reasoning,
            "execution_strategy": plan.execution_strategy
        }
    
    async def replanning_node(state: GraphState) -> GraphState:
        """Generate follow-up plan based on aggregator feedback"""
        query = state["query"]
        action_results = state["action_results"]
        aggregator_thought = state["aggregator_thought"]
        next_id = max([r.action_id for r in action_results]) + 1 if action_results else 1
        
        # Build detailed execution summary
        results_summary = []
        for r in action_results:
            result_str = f"${r.action_id}. Agent: {r.agent_name}\n   Request: {r.request}\n   Output: {r.output}"
            if r.error:
                result_str += f"\n   ERROR: {r.error}"
            else:
                result_str += "\n   Success"
            results_summary.append(result_str)
        
        results_text = "\n\n".join(results_summary)
        
        replanner_context = (
            f"ORIGINAL QUERY: {query}\n\n"
            f"PREVIOUS PLAN EXECUTION RESULTS:\n"
            f"{results_text}\n\n"
            f"AGGREGATOR FEEDBACK (Why replanning is needed):\n"
            f"{aggregator_thought}\n\n"
            f"Start your new action IDs at ${next_id}\n"
        )
        
        
        
        result = await replanner_agent.ainvoke({"messages": [{"role": "user", "content": replanner_context}]})
        replan_output = result["structured_response"]
        

        if isinstance(replan_output, CANNOT_EXECUTE_Plan):
            return {
                **state,
                "error_message": replan_output.reason,
                "final_answer": f"Unable to complete query after {state['replan_count']} attempts: {replan_output.reason}",
            }
        
        new_plan: Plan = replan_output
        
        return {
            **state,
            "current_plan": new_plan.actions,
            "plan_reasoning": new_plan.reasoning,
            "execution_strategy": new_plan.execution_strategy,
            "aggregator_decision": None,
            "aggregator_thought": None,
            "replan_count": state["replan_count"] + 1,
        }
    
    async def execution_node(state: GraphState) -> GraphState:
        """Execute the current plan's actions"""
        current_plan = state["current_plan"]
        existing_results = state.get("action_results", [])
        
        new_results = await executor.execute_plan(current_plan, existing_results)
        
        all_results = existing_results + new_results
        
        return {
            **state,
            "action_results": all_results
        }
    
    async def aggregation_node(state: GraphState) -> GraphState:
        """Synthesize results and decide: finish or replan"""
        query = state["query"]
        plan_reasoning = state["plan_reasoning"]
        action_results = state["action_results"]
        execution_strategy = state["execution_strategy"]
        replan_count = state["replan_count"]
        error_message = state.get("error_message")

        # Determine aggregation scenario
        if error_message:
            scenario = "CANNOT_EXECUTE"
        elif replan_count >= MAX_REPLAN_CYCLES:
            scenario = "MAX_REPLANS_REACHED"
        else:
            scenario = "NORMAL"
        scenario_note = f"SCENARIO: {scenario}"

        results_summary = []
        error_count = 0
        success_count = 0
        
        for r in action_results:
            status = "[FAILED]" if r.error else "[SUCCESS]"
            result_line = f"${r.action_id} ({r.agent_name}) - {status}\n   Request: {r.request}\n   Output: {r.output}"
            if r.error:
                result_line += f"\n   Error Details: {r.error}"
                error_count += 1
            else:
                success_count += 1
            results_summary.append(result_line)
        
        results_text = "\n\n".join(results_summary) if results_summary else "No actions were executed."
        

        aggregator_context = (
            f"USER QUERY: {query}\n\n"
            f"EXECUTION STRATEGY: {execution_strategy.upper()}\n"
            f"PLANNER'S STRATEGY: {plan_reasoning}\n\n"
            f"EXECUTION SUMMARY: {success_count} successful, {error_count} failed\n"
            f"REPLAN CYCLES USED: {replan_count}/{MAX_REPLAN_CYCLES}\n"
            f"{scenario_note}\n\n"
            "DETAILED ACTION RESULTS:\n"
            f"{results_text}\n\n"
            "Your task: Based on the scenario above, either provide a final answer (AggregatorFinish) or request replanning (AggregatorReplan, only if scenario allows)."
        )
        
        
        result = await aggregator_agent.ainvoke({"messages": [{"role": "user", "content":aggregator_context}]})
        response = result["structured_response"]
        

        if scenario in ["CANNOT_EXECUTE", "MAX_REPLANS_REACHED"]:
            if isinstance(response, AggregatorReplan):
                # Override with finish if aggregator incorrectly suggested replan
                return {
                    **state,
                    "aggregator_decision": "finish",
                    "aggregator_thought": f"Forced finish due to {scenario}",
                    "final_answer": error_message if error_message else f"Unable to complete query after {replan_count} replan attempts."
                }
        
        if isinstance(response, AggregatorFinish):
            return {
                **state,
                "aggregator_decision": "finish",
                "aggregator_thought": response.thought,
                "final_answer": response.final_answer
            }
        else:
            return {
                **state,
                "aggregator_decision": "replan",
                "aggregator_thought": response.replan_reasoning
            }
    
    def route_after_planning(state: GraphState) -> str:
        """Route to execution or end if CANNOT_EXECUTE"""
        if state.get("error_message"):
            return "aggregate"
        return "execute"
    
    def route_after_aggregation(state: GraphState) -> str:
        """Route to finish, replan, or max cycles"""
        
        if state["aggregator_decision"] == "finish":
            return "end"
        
        if state["replan_count"] >= MAX_REPLAN_CYCLES:
            return "aggregate"
        
        return "replan"
    
    def route_after_replanning(state: GraphState) -> str:
        """Route to execution or end if replanner returned CANNOT_EXECUTE"""
        if state.get("error_message"):
            return "aggregate"
        return "execute"
    

   
    
    workflow = StateGraph(GraphState)
    
    workflow.add_node("plan", planning_node)
    workflow.add_node("execute", execution_node)
    workflow.add_node("aggregate", aggregation_node)
    workflow.add_node("replan", replanning_node)
    
    workflow.set_entry_point("plan")
    workflow.add_conditional_edges("plan", route_after_planning, {
        "execute": "execute",
        "aggregate": "aggregate"
    })
    workflow.add_edge("execute", "aggregate")
    
    workflow.add_conditional_edges("aggregate", route_after_aggregation, {
        "replan": "replan",
        "aggregate": "aggregate",
        "end": END
    })
    workflow.add_conditional_edges("replan", route_after_replanning, {
        "execute": "execute",
        "aggregate": "aggregate",
    })
    
    return workflow.compile()

async def run_agentic_query(query: str,workflow: CompiledStateGraph) -> dict:

    
    initial_state: GraphState = {
        "query": query,
        "current_plan": None,
        "plan_reasoning": "",
        "execution_strategy": "complete",
        "action_results": [],
        "aggregator_decision": None,
        "aggregator_thought": "",
        "final_answer": None,
        "replan_count": 0,
        "error_message": None
    }
    
    final_state = await workflow.ainvoke(initial_state)
    
    # Return formatted response
    if final_state.get("error_message"):
        return {
            "success": False,
            "answer": final_state["error_message"],
            "query": query
        }
    
    return {
        "success": True,
        "query": query,
        "answer": final_state.get("final_answer", "No answer generated"),
        "num_actions": len(final_state["action_results"]),
        "replan_cycles": final_state["replan_count"]
    }
