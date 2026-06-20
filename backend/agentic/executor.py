from typing import List, Dict, Set
import re
import asyncio
from toposort import toposort
from langchain_core.messages import HumanMessage
from .graph_state import ActionResult, Action
from langgraph.graph.state import CompiledStateGraph

class PlanExecutor:
    """Executes action plans by invoking agents in dependency order"""
    
    def __init__(self, langchain_agents: List[CompiledStateGraph]):
        """
        Initialize executor with available agents
        
        Args:
            langchain_agents: List of compiled LangGraph agents
        """
        self.agents = langchain_agents
        self.agent_registry: Dict[str, CompiledStateGraph] = {
            agent.name: agent for agent in self.agents
        }
    
    def _parse_dependencies(self, request: str) -> Set[int]:
        """
        Extract $N references from action request
        
        Args:
            request: The action request string
            
        Returns:
            Set of action IDs this request depends on (not indices!)
        """
        # Match $N pattern where N is a number, but not \$N (escaped)
        pattern = r'(?<!\\)\$(\d+)'
        matches = re.findall(pattern, request)
        return {int(n) for n in matches}
    
    def _build_dependency_graph(self, actions: List[Action]) -> Dict[int, Set[int]]:
        """
        Build dependency graph from actions
        
        Args:
            actions: List of actions to analyze
            
        Returns:
            Dict mapping action index to set of dependency indices
        """
        # CRITICAL FIX: Map action IDs to indices
        id_to_idx = {action.id: idx for idx, action in enumerate(actions)}
        
        dependencies = {}
        for idx, action in enumerate(actions):
            dep_ids = self._parse_dependencies(action.request)
            # Convert dependency IDs to indices
            dep_indices = set()
            for dep_id in dep_ids:
                if dep_id in id_to_idx:
                    dep_indices.add(id_to_idx[dep_id])
                # If dep_id not in current actions, it references a previous result
                # Don't add to graph (it's satisfied by previous_results)
            dependencies[idx] = dep_indices
        return dependencies
    
    def _replace_dependencies(
        self, 
        request: str, 
        all_results: List[ActionResult],
        result_id_map: Dict[int, int]
    ) -> str:
        """
        Replace $N references with actual results
        
        Args:
            request: Original request with $N placeholders
            all_results: All available action results
            result_id_map: Maps action IDs to positions in all_results
            
        Returns:
            Request with $N replaced by actual results and \$N unescaped to $N
        """
        def replacer(match):
            action_id = int(match.group(1))
            # CRITICAL FIX: Look up by action ID, not index
            if action_id not in result_id_map:
                return f"[Result ${action_id} not yet available]"
            
            result_idx = result_id_map[action_id]
            if result_idx >= len(all_results):
                return f"[Result ${action_id} not yet available]"
            
            result = all_results[result_idx]
            if result is None:
                return f"[Result ${action_id} is None]"
            if result.error:
                return f"[Error in ${action_id}: {result.error}]"
            return str(result.output)
        
        # Replace unescaped $N with results
        result = re.sub(r'(?<!\\)\$(\d+)', replacer, request)
        # Unescape \$N to $N
        result = result.replace(r'\$', '$')
        return result
    
    def _should_skip_action(
        self,
        action: Action,
        dependencies: Dict[int, Set[int]],
        action_idx: int,
        all_results: List[ActionResult],
        result_id_map: Dict[int, int]
    ) -> tuple[bool, str]:
        """
        Check if action should be skipped due to failed dependencies
        
        Args:
            action: The action being checked
            dependencies: Dependency graph (maps indices to dependency indices)
            action_idx: Index of action to check
            all_results: All results so far
            result_id_map: Maps action IDs to result positions
            
        Returns:
            Tuple of (should_skip, error_message)
        """
        # Get dependency action IDs from the request (not indices!)
        dep_ids = self._parse_dependencies(action.request)
        failed_deps = []
        
        for dep_id in dep_ids:
            # Check if this dependency has been executed
            if dep_id not in result_id_map:
                # Dependency not yet executed (shouldn't happen due to topo sort)
                failed_deps.append(dep_id)
                continue
            
            result_idx = result_id_map[dep_id]
            if result_idx >= len(all_results):
                # Result not available yet
                failed_deps.append(dep_id)
                continue
                
            result = all_results[result_idx]
            if result is None:
                # Result is None (shouldn't happen)
                failed_deps.append(dep_id)
                continue
                
            if result.error:
                # Result has an error
                failed_deps.append(dep_id)
        
        if len(failed_deps) > 0:
            dep_list = ", ".join(f"${dep_id}" for dep_id in failed_deps)
            return True, f"Skipped due to failed dependencies: {dep_list}"
        
        return False, ""
    
    async def _execute_action(
        self,
        action: Action,
        all_results: List[ActionResult],
        dependencies: Dict[int, Set[int]],
        action_idx: int,
        result_id_map: Dict[int, int]
    ) -> ActionResult:
        """
        Execute a single action
        
        Args:
            action: Action to execute
            all_results: All previous results for dependency resolution
            dependencies: Dependency graph for error propagation
            action_idx: Current action index
            result_id_map: Maps action IDs to result positions
            
        Returns:
            ActionResult with execution outcome
        """
        # Check if we should skip due to failed dependencies
        # CRITICAL FIX: Pass action and result_id_map
        should_skip, skip_error = self._should_skip_action(
            action, dependencies, action_idx, all_results, result_id_map
        )
        if should_skip:
            return ActionResult(
                action_id=action.id,
                agent_name=action.agent,
                request=action.request,
                output="",
                error=skip_error
            )
        
        try:
            # Get the agent
            agent = self.agent_registry.get(action.agent)
            if not agent:
                return ActionResult(
                    action_id=action.id,
                    agent_name=action.agent,
                    request=action.request,
                    output="",
                    error=f"Agent '{action.agent}' not found in registry"
                )
            
            # Replace dependencies - CRITICAL FIX: pass result_id_map
            resolved_request = self._replace_dependencies(action.request, all_results, result_id_map)
            
            # Invoke LangGraph agent asynchronously with resolved request
            agent_result = await agent.ainvoke({"messages": [HumanMessage(content=resolved_request)]})
            
            # Extract the final message content from agent response
            if "messages" in agent_result and len(agent_result["messages"]) > 0:
                output = agent_result["messages"][-1].content
            else:
                output = str(agent_result)
            
            return ActionResult(
                action_id=action.id,
                agent_name=action.agent,
                request=action.request,
                output=output,
                error=None
            )
            
        except Exception as e:
            return ActionResult(
                action_id=action.id,
                agent_name=action.agent,
                request=action.request,
                output="",
                error=f"Execution error: {str(e)}"
            )
    
    def _topological_sort(
        self, 
        actions: List[Action], 
        dependencies: Dict[int, Set[int]]
    ) -> List[List[int]]:
        """
        Topologically sort actions into execution levels (enables parallelism)
        
        Args:
            actions: List of actions
            dependencies: Dependency graph
            
        Returns:
            List of levels, where each level is a list of action indices
            that can be executed in parallel
        """
        try:
            levels = list(toposort(dependencies))
            return [sorted(list(level)) for level in levels]
        except ValueError as e:
            raise ValueError("Circular dependency detected in action plan") from e
    
    async def execute_plan(
        self,
        actions: List[Action],
        previous_results: List[ActionResult]
    ) -> List[ActionResult]:
        """
        Execute a plan's actions in dependency order
        
        Args:
            actions: List of Action objects to execute
            previous_results: Results from prior planning cycles (for $N references)
        
        Returns:
            List of ActionResult objects for the new actions (ordered by original action index)
        """
        if not actions:
            return []
        
        # CRITICAL FIX: Build mapping of action IDs to result positions
        result_id_map = {result.action_id: idx for idx, result in enumerate(previous_results)}
        
        dependencies = self._build_dependency_graph(actions)
        
        try:
            execution_levels = self._topological_sort(actions, dependencies)
        except ValueError as e:
            return [
                ActionResult(
                    action_id=action.id,
                    agent_name=action.agent,
                    request=action.request,
                    output="",
                    error=str(e)
                )
                for action in actions
            ]
        
        # Build complete results list: previous + placeholders for new actions
        all_results = previous_results.copy()
        new_results = [None] * len(actions)
        
        # Reserve space in all_results for indexed access during execution
        all_results.extend([None] * len(actions))
        
        # Execute each level (parallel execution within levels)
        for level in execution_levels:
            # Create tasks for this level
            tasks = []
            for idx in level:
                action = actions[idx]
                task = self._execute_action(action, all_results, dependencies, idx, result_id_map)
                tasks.append((idx, task))
            
            # Execute level in parallel using asyncio.gather
            level_results = await asyncio.gather(*[task for _, task in tasks])
            
            # Store results at correct indices
            for (idx, _), result in zip(tasks, level_results):
                new_results[idx] = result
                # Update all_results at the correct position (offset by previous_results length)
                result_position = len(previous_results) + idx
                all_results[result_position] = result
                # CRITICAL FIX: Update the ID map for newly executed actions
                result_id_map[result.action_id] = result_position
        
        return new_results
