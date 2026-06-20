"""
Remediation Orchestrator - Connects error retrieval to action execution
Queries Pathway API for error-action mappings and executes highest confidence actions
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from ..execution.execution_engine import ActionExecutor
from ..execution.execution_adapter import ExecutionAdapter
from ..core.runbook_registry import RunbookRegistry, RemediationAction
from ..core.llm_suggestion_service import LLMSuggestionService, ErrorRegistrySuggestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence classification for error matching"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorMatch:
    """Represents a matched error with confidence"""
    error: str
    actions: List[str]
    description: str
    distance: float
    confidence: ConfidenceLevel
    
    @property
    def is_actionable(self) -> bool:
        """Check if confidence is high enough to execute"""
        return self.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


@dataclass
class ActionExecutionState:
    """Tracks execution state for a single action"""
    action_id: str
    requires_approval: bool
    approved: bool = False
    executed: bool = False
    success: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class ApprovalRequest:
    """Represents a pending approval request with full state preservation and per-action tracking"""
    request_id: str
    error_message: str
    best_match: ErrorMatch
    action_ids: List[str]
    created_at: datetime
    status: str = "pending"  # pending, approved, rejected, executing, completed
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    execution_state: Dict[str, ActionExecutionState] = field(default_factory=dict)  # action_id → state
    current_action_index: int = 0  # Track which action to execute next
    
    def get_next_action(self) -> Optional[str]:
        """Get next action to execute"""
        if self.current_action_index < len(self.action_ids):
            return self.action_ids[self.current_action_index]
        return None
    
    def get_pending_approval_actions(self) -> List[str]:
        """Get actions that need approval before execution"""
        pending = []
        for action_id, state in self.execution_state.items():
            if state.requires_approval and not state.approved and not state.executed:
                pending.append(action_id)
        return pending
    
    def mark_action_executed(self, action_id: str, success: bool, result: Any = None, error: str = None):
        """Mark an action as executed"""
        if action_id in self.execution_state:
            state = self.execution_state[action_id]
            state.executed = True
            state.success = success
            state.result = result
            state.error = error
    
    def approve_action(self, action_id: str, approved_by: str):
        """Approve a specific action"""
        if action_id in self.execution_state:
            state = self.execution_state[action_id]
            state.approved = True
            state.approved_by = approved_by
            state.approved_at = datetime.now()
    
    def can_execute_action(self, action_id: str) -> bool:
        """Check if action can be executed (approved if needed)"""
        if action_id not in self.execution_state:
            return False
        state = self.execution_state[action_id]
        return not state.requires_approval or state.approved
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API responses"""
        return {
            'request_id': self.request_id,
            'error_message': self.error_message,
            'matched_error': self.best_match.error,
            'description': self.best_match.description,
            'distance': self.best_match.distance,
            'confidence': self.best_match.confidence.value,
            'action_ids': self.action_ids,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'rejection_reason': self.rejection_reason,
            'current_action_index': self.current_action_index,
            'execution_state': {
                action_id: {
                    'requires_approval': state.requires_approval,
                    'approved': state.approved,
                    'executed': state.executed,
                    'success': state.success,
                    'approved_by': state.approved_by,
                    'approved_at': state.approved_at.isoformat() if state.approved_at else None
                }
                for action_id, state in self.execution_state.items()
            },
            'pending_approval_actions': self.get_pending_approval_actions()
        }


class ApprovalManager:
    """Manages approval requests - preserves state between pause and resume"""
    def __init__(self):
        self.pending_requests: Dict[str, ApprovalRequest] = {}
    
    async def create_request(
        self,
        error_message: str,
        best_match: ErrorMatch,
        action_ids: List[str],
        actions: List['RemediationAction'] = None
    ) -> ApprovalRequest:
        """Create and store a new approval request with per-action state"""
        request_id = f"APR-{uuid.uuid4().hex[:12]}"
        
        # Initialize execution state for each action
        execution_state = {}
        if actions:
            for action in actions:
                execution_state[action.action_id] = ActionExecutionState(
                    action_id=action.action_id,
                    requires_approval=action.requires_approval
                )
        else:
            # Fallback if actions not provided
            for action_id in action_ids:
                execution_state[action_id] = ActionExecutionState(
                    action_id=action_id,
                    requires_approval=False  # Will be updated when fetched
                )
        
        request = ApprovalRequest(
            request_id=request_id,
            error_message=error_message,
            best_match=best_match,
            action_ids=action_ids,
            created_at=datetime.now(),
            execution_state=execution_state
        )
        self.pending_requests[request_id] = request
        logger.info(f"Created approval request: {request_id}")
        return request
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Retrieve a request by ID"""
        return self.pending_requests.get(request_id)
    
    def approve_request(
        self,
        request_id: str,
        approved_by: str
    ) -> bool:
        """Approve a pending request"""
        request = self.pending_requests.get(request_id)
        if request and request.status == "pending":
            request.status = "approved"
            request.approved_at = datetime.now()
            request.approved_by = approved_by
            logger.info(f"Approved request {request_id} by {approved_by}")
            return True
        return False
    
    def reject_request(
        self,
        request_id: str,
        rejected_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """Reject a pending request"""
        request = self.pending_requests.get(request_id)
        if request and request.status == "pending":
            request.status = "rejected"
            request.approved_at = datetime.now()
            request.approved_by = rejected_by
            request.rejection_reason = reason
            logger.info(f"Rejected request {request_id} by {rejected_by}")
            return True
        return False
    
    def list_pending(self) -> List[ApprovalRequest]:
        """List all pending requests"""
        return [r for r in self.pending_requests.values() if r.status == "pending"]


class RemediationOrchestrator:
    """
    Orchestrates error detection -> action retrieval -> execution pipeline
    """
    
    def __init__(
        self,
        pathway_api_url: str,
        runbook_registry: RunbookRegistry,
        action_executor: ActionExecutor,
        confidence_thresholds: Dict[str, float] = None,
        suggestion_service: Optional[LLMSuggestionService] = None
    ):
        """
        Args:
            pathway_api_url: URL of Pathway retrieval API (e.g., http://localhost:8000)
            runbook_registry: Registry to fetch action details
            action_executor: Executor for running actions
            confidence_thresholds: Distance thresholds for confidence levels
            suggestion_service: Optional LLM service for generating suggestions
        """
        self.pathway_api_url = pathway_api_url
        self.runbook_registry = runbook_registry
        self.action_executor = action_executor
        
        # Initialize approval manager for state preservation
        self.approval_manager = ApprovalManager()
        
        # Initialize suggestion service
        self.suggestion_service = suggestion_service
        
        # Default confidence thresholds (cosine distance)
        # HIGH: Very close semantic match (< 0.3)
        # MEDIUM: Reasonable match (0.3 - 0.5)
        # LOW: Poor match (>= 0.5)
        self.confidence_thresholds = confidence_thresholds or {
            'high': 0.3,
            'medium': 0.5
        }
    
    def _classify_confidence(self, distance: float) -> ConfidenceLevel:
        """Classify confidence based on cosine distance"""
        if distance < self.confidence_thresholds['high']:
            return ConfidenceLevel.HIGH
        elif distance < self.confidence_thresholds['medium']:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    async def query_error_actions(
        self,
        error_message: str,
        k: int = 5
    ) -> List[ErrorMatch]:
        """
        Query Pathway API for matching error-action mappings
        
        Args:
            error_message: Error message to search for
            k: Number of top matches to retrieve
            
        Returns:
            List of ErrorMatch objects sorted by confidence
        """
        url = f"{self.pathway_api_url}/v1/retrieve"
        params = {"query": error_message, "k": k}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Pathway API error: {response.status}")
                        return []
                    
                    results = await response.json()
                    print(results)
            
            # Parse results into ErrorMatch objects
            matches = []
            for result in results:
                metadata = result.get('metadata', {})
                full_data = metadata.get('full_data', {})
                distance = result.get('dist', 1.0)
                
                error_match = ErrorMatch(
                    error=full_data.get('error', ''),
                    actions=full_data.get('actions', []),
                    description=full_data.get('description', ''),
                    distance=distance,
                    confidence=self._classify_confidence(distance)
                )
                matches.append(error_match)
            
            logger.info(f"Found {len(matches)} error matches for: {error_message}")
            return matches
            
        except Exception as e:
            logger.error(f"Failed to query Pathway API: {e}")
            return []
    
    async def get_action_details(
        self,
        action_ids: List[str]
    ) -> List[RemediationAction]:
        """
        Fetch full action details from runbook registry
        
        Args:
            action_ids: List of action IDs to fetch
            
        Returns:
            List of RemediationAction objects
        """
        actions = []
        for action_id in action_ids:
            try:
                action = await self.runbook_registry.get(action_id)
                if action:
                    actions.append(action)
                else:
                    logger.warning(f"Action not found in registry: {action_id}")
            except Exception as e:
                logger.error(f"Failed to fetch action {action_id}: {e}")
        
        return actions
    
    async def execute_remediation(
        self,
        error_message: str,
        auto_execute_high_confidence: bool = True,
        require_approval_medium: bool = True
    ) -> Dict[str, Any]:
        """
        Main orchestration flow: detect error -> find actions -> execute
        
        Args:
            error_message: Error message from monitoring/logs
            auto_execute_high_confidence: Auto-execute high confidence matches
            require_approval_medium: Require approval for medium confidence
            
        Returns:
            Execution result with status and details
        """
        logger.info(f"Starting remediation for error: {error_message}")
        
        # Step 1: Query Pathway API for error-action mappings
        matches = await self.query_error_actions(error_message, k=3)
        
        if not matches:
            return {
                'status': 'no_match',
                'error': error_message,
                'message': 'No matching error-action mappings found'
            }
        
        # Step 2: Filter by confidence
        best_match = matches[0]
        logger.info(
            f"Best match: {best_match.error} "
            f"(distance: {best_match.distance:.3f}, "
            f"confidence: {best_match.confidence.value})"
        )
        
        # Check if actionable
        if not best_match.is_actionable:
            # Generate LLM suggestion for low confidence matches
            suggestion = None
            if self.suggestion_service:
                try:
                    logger.info(f"Generating suggestion for low confidence error: {error_message}")
                    
                    # Get all available actions for context
                    all_actions = await self.runbook_registry.list_all()
                    actions_context = [
                        {
                            'action_id': action.action_id,
                            'method': action.method,
                            'definition': action.definition,
                            'risk_level': action.risk_level,
                            'requires_approval': action.requires_approval
                        }
                        for action in all_actions
                    ]
                    
                    # Get existing errors for context
                    existing_errors = [
                        {
                            'error': match.error,
                            'description': match.description,
                            'actions': match.actions
                        }
                        for match in matches
                    ]
                    
                    suggestion = await self.suggestion_service.suggest_error_registry_entry(
                        error_message=error_message,
                        existing_errors=existing_errors,
                        available_actions=actions_context
                    )
                    logger.info(f"Generated suggestion: {suggestion.error_name} (feasible: {suggestion.feasible})")
                except Exception as e:
                    logger.error(f"Failed to generate suggestion: {e}", exc_info=True)
            
            return {
                'status': 'low_confidence',
                'error': error_message,
                'best_match': best_match.error,
                'distance': best_match.distance,
                'confidence': best_match.confidence.value,
                'message': 'Match found but confidence too low to execute',
                'suggestion': {
                    'error_name': suggestion.error_name,
                    'description': suggestion.description,
                    'suggested_actions': [
                        {
                            'action_id': act.action_id,
                            'reason': act.reason
                        }
                        for act in suggestion.suggested_actions
                    ],
                    'confidence_reasoning': suggestion.confidence_reasoning,
                    'feasible': suggestion.feasible,
                    'additional_actions_needed': suggestion.additional_actions_needed
                } if suggestion else None
            }
        
        # Check approval requirements
        if best_match.confidence == ConfidenceLevel.MEDIUM and require_approval_medium:
            # Fetch actions first to check per-action approval requirements
            logger.info(f"Fetching action details for approval check: {best_match.actions}")
            actions = await self.get_action_details(best_match.actions)
            
            # Create approval request with full action state
            approval_request = await self.approval_manager.create_request(
                error_message=error_message,
                best_match=best_match,
                action_ids=best_match.actions,
                actions=actions  # Pass actions to initialize per-action state
            )
            
            # Check if any actions require individual approval
            actions_requiring_approval = [
                a.action_id for a in actions if a.requires_approval
            ]
            
            return {
                'status': 'approval_required',
                'request_id': approval_request.request_id,  # ← Key for resumption
                'error': error_message,
                'best_match': best_match.error,
                'distance': best_match.distance,
                'confidence': best_match.confidence.value,
                'actions': best_match.actions,
                'description': best_match.description,
                'message': 'Medium confidence match requires approval before execution',
                'created_at': approval_request.created_at.isoformat(),
                'actions_requiring_individual_approval': actions_requiring_approval
            }
        
        # Step 3: Get action details from registry
        logger.info(f"Fetching action details for: {best_match.actions}")
        actions = await self.get_action_details(best_match.actions)
        
        if not actions:
            return {
                'status': 'actions_not_found',
                'error': error_message,
                'action_ids': best_match.actions,
                'message': 'Matched actions not found in registry'
            }
        
        # Check if any actions require individual approval (even for HIGH confidence)
        actions_requiring_approval = [
            a.action_id for a in actions if a.requires_approval
        ]
        
        if actions_requiring_approval:
            # Create approval request instead of auto-executing
            logger.info(f"Actions require individual approval: {actions_requiring_approval}")
            approval_request = await self.approval_manager.create_request(
                error_message=error_message,
                best_match=best_match,
                action_ids=best_match.actions,
                actions=actions
            )
            
            return {
                'status': 'approval_required',
                'request_id': approval_request.request_id,
                'error': error_message,
                'matched_error': best_match.error,
                'distance': best_match.distance,
                'confidence': best_match.confidence.value,
                'actions': best_match.actions,
                'description': best_match.description,
                'message': f'Actions require individual approval before execution: {", ".join(actions_requiring_approval)}',
                'created_at': approval_request.created_at.isoformat(),
                'actions_requiring_individual_approval': actions_requiring_approval
            }
        
        # Step 4: Execute actions in sequence
        execution_results = []
        for action in actions:
            #TODO: Add LLM logic to check the output of the previous action(and match with the expected outcome,ie description to check if did its job) and decide whether to continue, alert, or rollback.
            logger.info(f"Executing action: {action.action_id} ({action.definition})")
            
            try:
                # Convert to execution format
                exec_action = ExecutionAdapter.to_execution_format(action)
                
                # Execute with safety pipeline
                #TODO: Add if approval is required from the user to run this action thing.
                result = await self.action_executor.execute_with_safety(
                    action=exec_action,
                    allow_rollback=True
                )
                
                execution_results.append({
                    'action_id': action.action_id,
                    'status': result.status.value,
                    'success': result.status.value == 'success',
                    'result': result.result,
                    'error': result.error,
                    'duration': result.end_time - result.start_time if result.end_time else None
                })
                
                # Stop on first failure if critical
                #TODO: After understanding the working of execute_with_safety, update logic
                if result.status.value == 'failed' and action.risk_level == 'high':
                    logger.error(f"Critical action failed, stopping execution chain")
                    break
                    
            except Exception as e:
                logger.error(f"Failed to execute action {action.action_id}: {e}")
                execution_results.append({
                    'action_id': action.action_id,
                    'status': 'failed',
                    'success': False,
                    'error': str(e)
                })
        
        # Step 5: Return comprehensive result
        return {
            'status': 'executed',
            'error': error_message,
            'matched_error': best_match.error,
            'distance': best_match.distance,
            'confidence': best_match.confidence.value,
            'actions_executed': len(execution_results),
            'execution_results': execution_results,
            'overall_success': all(r['success'] for r in execution_results)
        }
    
    async def execute_with_approval(
        self,
        request_id: str,
        approved_by: str,
        resume: bool = True
    ) -> Dict[str, Any]:
        """
        Execute actions for an approved request with resumable per-action execution
        
        Args:
            request_id: ID of the approval request to execute
            approved_by: Identifier of who approved (user, operator, etc.)
            resume: If True, resume from last checkpoint; if False, start fresh
            
        Returns:
            Execution result or pause-for-approval status
        """
        logger.info(f"Executing approved request: {request_id}")
        
        # Retrieve preserved state
        approval_request = self.approval_manager.get_request(request_id)
        
        if not approval_request:
            return {
                'status': 'not_found',
                'request_id': request_id,
                'message': 'Approval request not found'
            }
        
        if approval_request.status == "rejected":
            return {
                'status': 'invalid_state',
                'request_id': request_id,
                'current_status': approval_request.status,
                'message': f'Request already {approval_request.status}'
            }
        
        # Mark overall request as approved if first time
        if approval_request.status == "pending":
            self.approval_manager.approve_request(request_id, approved_by)
        
        # Update status to executing
        approval_request.status = "executing"
        
        # Execute using preserved state
        error_message = approval_request.error_message
        action_ids = approval_request.action_ids
        
        logger.info(
            f"Executing approved actions for '{error_message}': {action_ids}"
        )
        
        # Get action details
        actions = await self.get_action_details(action_ids)
        
        if not actions:
            return {
                'status': 'actions_not_found',
                'request_id': request_id,
                'error': error_message,
                'message': 'Approved actions not found in registry'
            }
        
        # Update execution state with action details if not already done
        for action in actions:
            if action.action_id not in approval_request.execution_state:
                approval_request.execution_state[action.action_id] = ActionExecutionState(
                    action_id=action.action_id,
                    requires_approval=action.requires_approval
                )
        
        # Execute actions from current checkpoint
        execution_results = []
        paused_for_approval = False
        
        for i in range(approval_request.current_action_index, len(actions)):
            action = actions[i]
            action_state = approval_request.execution_state.get(action.action_id)
            
            # Skip if already executed
            if action_state and action_state.executed:
                execution_results.append({
                    'action_id': action.action_id,
                    'status': 'skipped',
                    'success': action_state.success,
                    'result': action_state.result,
                    'error': action_state.error,
                    'note': 'Already executed'
                })
                approval_request.current_action_index += 1
                continue
            
            # Check if action requires approval
            if action.requires_approval and action_state:
                if not action_state.approved:
                    # PAUSE: This action needs approval
                    logger.info(f"Action {action.action_id} requires approval - pausing execution")
                    paused_for_approval = True
                    
                    return {
                        'status': 'action_approval_required',
                        'request_id': request_id,
                        'error': error_message,
                        'paused_at_action': action.action_id,
                        'action_index': i,
                        'action_definition': action.definition,
                        'action_risk_level': action.risk_level,
                        'actions_executed': len(execution_results),
                        'actions_remaining': len(actions) - i,
                        'execution_results': execution_results,
                        'message': f'Action "{action.action_id}" requires individual approval before execution',
                        'pending_approval_actions': approval_request.get_pending_approval_actions()
                    }
            
            # Execute action
            try:
                logger.info(f"[{i+1}/{len(actions)}] Executing: {action.action_id} ({action.definition})")
                
                exec_action = ExecutionAdapter.to_execution_format(action)
                result = await self.action_executor.execute_with_safety(
                    action=exec_action,
                    allow_rollback=True
                )
                
                success = result.status.value == 'success'
                
                # Update state
                approval_request.mark_action_executed(
                    action.action_id,
                    success=success,
                    result=result.result,
                    error=result.error
                )
                
                execution_results.append({
                    'action_id': action.action_id,
                    'status': result.status.value,
                    'success': success,
                    'result': result.result,
                    'error': result.error
                })
                
                # Move to next action
                approval_request.current_action_index += 1
                
                # Stop on failure if high risk
                if not success and action.risk_level == 'high':
                    logger.error(f"High-risk action failed, stopping execution chain")
                    break
                    
            except Exception as e:
                logger.error(f"Failed to execute action {action.action_id}: {e}")
                
                approval_request.mark_action_executed(
                    action.action_id,
                    success=False,
                    error=str(e)
                )
                
                execution_results.append({
                    'action_id': action.action_id,
                    'status': 'failed',
                    'success': False,
                    'error': str(e)
                })
                
                approval_request.current_action_index += 1
        
        # Mark as completed if all actions processed
        if approval_request.current_action_index >= len(actions):
            approval_request.status = "completed"
        
        return {
            'status': 'executed' if not paused_for_approval else 'paused',
            'request_id': request_id,
            'error': error_message,
            'matched_error': approval_request.best_match.error,
            'distance': approval_request.best_match.distance,
            'confidence': approval_request.best_match.confidence.value,
            'approved_by': approved_by,
            'actions_executed': len(execution_results),
            'execution_results': execution_results,
            'overall_success': all(r['success'] for r in execution_results if r['status'] != 'skipped'),
            'completed': approval_request.status == "completed"
        }
    
    async def approve_action(
        self,
        request_id: str,
        action_id: str,
        approved_by: str
    ) -> Dict[str, Any]:
        """
        Approve a specific action within a request and resume execution
        
        Args:
            request_id: ID of the approval request
            action_id: ID of the action to approve
            approved_by: Identifier of who approved
            
        Returns:
            Result with next action to approve or execution continuing
        """
        approval_request = self.approval_manager.get_request(request_id)
        
        if not approval_request:
            return {
                'status': 'not_found',
                'request_id': request_id,
                'message': 'Approval request not found'
            }
        
        if action_id not in approval_request.execution_state:
            return {
                'status': 'action_not_found',
                'request_id': request_id,
                'action_id': action_id,
                'message': f'Action {action_id} not part of this request'
            }
        
        # Approve the action
        approval_request.approve_action(action_id, approved_by)
        logger.info(f"Action {action_id} approved by {approved_by} in request {request_id}")
        
        # Resume execution - it will continue until next approval needed or completion
        return await self.execute_with_approval(
            request_id=request_id,
            approved_by=approved_by,
            resume=True
        )
    
    async def reject_approval(
        self,
        request_id: str,
        rejected_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject an approval request
        
        Args:
            request_id: ID of the approval request to reject
            rejected_by: Identifier of who rejected
            reason: Optional reason for rejection
            
        Returns:
            Rejection result
        """
        approval_request = self.approval_manager.get_request(request_id)
        
        if not approval_request:
            return {
                'status': 'not_found',
                'request_id': request_id,
                'message': 'Approval request not found'
            }
        
        if approval_request.status != "pending":
            return {
                'status': 'invalid_state',
                'request_id': request_id,
                'current_status': approval_request.status,
                'message': f'Request already {approval_request.status}'
            }
        
        self.approval_manager.reject_request(request_id, rejected_by, reason)
        
        return {
            'status': 'rejected',
            'request_id': request_id,
            'error': approval_request.error_message,
            'rejected_by': rejected_by,
            'reason': reason,
            'message': 'Approval request rejected'
        }
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests"""
        return [req.to_dict() for req in self.approval_manager.list_pending()]
    
    def get_approval_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific approval request"""
        request = self.approval_manager.get_request(request_id)
        return request.to_dict() if request else None
