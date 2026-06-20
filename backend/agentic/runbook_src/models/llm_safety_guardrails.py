"""
LLM Safety Guardrails - Security layer between LLM agents and execution
Prevents hallucinations, prompt injection, unauthorized actions
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationAction(Enum):
    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


@dataclass
class ValidationResult:
    safe: bool
    action: ValidationAction
    reason: str
    safety_score: float  # 0.0 to 1.0
    concerns: List[str]
    recommendations: List[str]


class LLMSafetyGuardrails:
    """
    Multi-layer security validation for LLM-generated plans
    Prevents:
    - Hallucinations (invented endpoints/parameters)
    - Prompt injection attacks
    - Unauthorized actions
    - Excessive blast radius
    - Suspicious parameter values
    """
    
    def __init__(self, runbook_registry, security_policies):
        """
        Args:
            runbook_registry: Registry of allowed endpoints/scripts
            security_policies: Security policy configuration
        """
        self.registry = runbook_registry
        self.policies = security_policies
        
        # Suspicious patterns for prompt injection detection
        self.injection_patterns = [
            # Command injection
            r';\s*rm\s+-rf',
            r'&&\s*curl',
            r'\|\s*bash',
            r'`[^`]*`',  # Backticks
            r'\$\([^)]*\)',  # Command substitution
            
            # SQL injection
            r';\s*DROP\s+TABLE',
            r"'\s*OR\s+'1'\s*=\s*'1",
            r'--\s*$',  # SQL comments
            
            # Path traversal
            r'\.\./\.\.',
            r'/etc/passwd',
            r'/etc/shadow',
            
            # LLM prompt injection
            r'ignore\s+previous\s+instructions',
            r'system:',
            r'assistant:',
            r'<\|.*?\|>',  # Special tokens
            
            # Code injection
            r'__import__',
            r'exec\s*\(',
            r'eval\s*\(',
            r'compile\s*\(',
            
            # Script injection
            r'<script[^>]*>',
            r'javascript:',
            r'onerror\s*=',
        ]
        
        self.injection_regex = re.compile('|'.join(self.injection_patterns), re.IGNORECASE)
    
    async def validate_plan(
        self,
        plan: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Comprehensive validation of LLM-generated plan
        
        Args:
            plan: Remediation plan from LLM
            context: Error context and current system state
            
        Returns:
            ValidationResult with decision (auto/approval/block)
        """
        
        concerns = []
        recommendations = []
        safety_score = 1.0  # Start at 100%, deduct for issues
        
        # Layer 1: Endpoint Whitelist Check
        endpoint_check = await self._validate_endpoint(plan)
        if not endpoint_check.valid:
            return ValidationResult(
                safe=False,
                action=ValidationAction.BLOCK,
                reason=endpoint_check.reason,
                safety_score=0.0,
                concerns=[endpoint_check.reason],
                recommendations=["Use only whitelisted endpoints from runbook registry"]
            )
        
        # Layer 2: Parameter Validation
        param_check = await self._validate_parameters(plan)
        if not param_check.valid:
            return ValidationResult(
                safe=False,
                action=ValidationAction.BLOCK,
                reason=param_check.reason,
                safety_score=0.0,
                concerns=[param_check.reason],
                recommendations=["Fix parameter validation errors"]
            )
        
        # Layer 3: Prompt Injection Detection
        injection_check = self._detect_prompt_injection(plan)
        if injection_check.detected:
            return ValidationResult(
                safe=False,
                action=ValidationAction.BLOCK,
                reason="Potential prompt injection detected",
                safety_score=0.0,
                concerns=[injection_check.details],
                recommendations=["Review and sanitize parameters"]
            )
        
        # Layer 4: Blast Radius Check
        blast_radius = plan.get('risk_assessment', {}).get('blast_radius', [])
        if len(blast_radius) > self.policies.get('max_blast_radius', 5):
            concerns.append(f"Large blast radius: {len(blast_radius)} services")
            safety_score -= 0.2
            recommendations.append("Consider more targeted remediation")
        
        # Layer 5: Risk Level Assessment
        risk_level = plan.get('risk_assessment', {}).get('level', 'medium')
        if risk_level in ['high', 'critical']:
            concerns.append(f"High risk action: {risk_level}")
            safety_score -= 0.3
            recommendations.append("Requires human approval due to high risk")
            
            return ValidationResult(
                safe=True,
                action=ValidationAction.REQUIRE_APPROVAL,
                reason=f"High risk action ({risk_level}) requires human approval",
                safety_score=safety_score,
                concerns=concerns,
                recommendations=recommendations
            )
        
        # Layer 6: Confidence Threshold
        confidence = plan.get('confidence', 0.0)
        min_confidence = self.policies.get('min_confidence_auto_execute', 0.85)
        
        if confidence < min_confidence:
            concerns.append(f"Low confidence: {confidence:.2f} < {min_confidence}")
            safety_score -= 0.2
            
            if confidence < 0.65:
                return ValidationResult(
                    safe=True,
                    action=ValidationAction.REQUIRE_APPROVAL,
                    reason=f"Low confidence ({confidence:.2f}) requires human review",
                    safety_score=safety_score,
                    concerns=concerns,
                    recommendations=["Human review recommended"] + recommendations
                )
        
        # Layer 7: Business Hours Check
        current_time = context.get('current_time', {})
        is_business_hours = current_time.get('is_business_hours', True)
        is_peak_hours = current_time.get('is_peak_hours', False)
        
        if is_peak_hours:
            concerns.append("Executing during peak hours")
            safety_score -= 0.15
        
        # Layer 8: Service Criticality
        service_name = context.get('service_name')
        service_criticality = await self._get_service_criticality(service_name)
        
        if service_criticality == 'critical' and is_business_hours:
            concerns.append("Critical service during business hours")
            safety_score -= 0.1
            recommendations.append("Consider quick human approval")
        
        # Layer 9: Reversibility Check
        reversibility = plan.get('risk_assessment', {}).get('reversibility', 'no')
        if reversibility == 'no' and risk_level != 'low':
            concerns.append("Irreversible action")
            safety_score -= 0.2
            recommendations.append("Ensure rollback plan is available")
        
        # Layer 10: Execution History
        action_id = plan.get('selected_remediation')
        history = await self._get_recent_executions(action_id)
        
        # Check if recently executed (prevent too frequent execution)
        recent_execution_minutes = self.policies.get('min_minutes_between_executions', 30)
        if history.get('last_execution_minutes_ago', 999) < recent_execution_minutes:
            return ValidationResult(
                safe=True,
                action=ValidationAction.REQUIRE_APPROVAL,
                reason=f"Action executed recently ({history['last_execution_minutes_ago']}m ago)",
                safety_score=safety_score,
                concerns=concerns + ["Too frequent execution"],
                recommendations=["Wait or get approval"] + recommendations
            )
        
        # Check recent failure rate
        recent_failure_rate = history.get('failure_rate_last_24h', 0.0)
        if recent_failure_rate > 0.3:  # >30% failure rate
            concerns.append(f"High recent failure rate: {recent_failure_rate*100:.1f}%")
            safety_score -= 0.25
            recommendations.append("Investigate recent failures before proceeding")
        
        # Decision Logic
        if safety_score >= 0.8 and risk_level == 'low' and confidence >= min_confidence:
            # AUTO-EXECUTE: Low risk, high confidence, good safety score
            return ValidationResult(
                safe=True,
                action=ValidationAction.AUTO_EXECUTE,
                reason="All safety checks passed - safe for auto-execution",
                safety_score=safety_score,
                concerns=concerns,
                recommendations=recommendations
            )
        elif safety_score >= 0.6:
            # REQUIRE APPROVAL: Medium risk/confidence
            return ValidationResult(
                safe=True,
                action=ValidationAction.REQUIRE_APPROVAL,
                reason="Medium risk/confidence - requires human approval",
                safety_score=safety_score,
                concerns=concerns,
                recommendations=["Quick human review recommended"] + recommendations
            )
        else:
            # BLOCK: Too many concerns
            return ValidationResult(
                safe=False,
                action=ValidationAction.BLOCK,
                reason=f"Safety score too low: {safety_score:.2f}",
                safety_score=safety_score,
                concerns=concerns,
                recommendations=["Address safety concerns before proceeding"] + recommendations
            )
    
    async def _validate_endpoint(self, plan: Dict[str, Any]) -> Any:
        """Validate endpoint is in whitelist"""
        
        action_id = plan.get('selected_remediation')
        endpoint = plan.get('execution_plan', {}).get('endpoint')
        
        # Check if action exists in registry
        registry_action = await self.registry.get_action(action_id)
        
        if not registry_action:
            return type('obj', (object,), {
                'valid': False,
                'reason': f"Action '{action_id}' not found in runbook registry (possible hallucination)"
            })()
        
        # Check if endpoint matches registry
        registry_endpoint = (
            registry_action.get('rpc_endpoint') or
            registry_action.get('script_path') or
            registry_action.get('command')
        )
        
        if endpoint != registry_endpoint:
            return type('obj', (object,), {
                'valid': False,
                'reason': f"Endpoint mismatch. Registry: {registry_endpoint}, Plan: {endpoint} (possible tampering)"
            })()
        
        return type('obj', (object,), {'valid': True, 'reason': 'OK'})()
    
    async def _validate_parameters(self, plan: Dict[str, Any]) -> Any:
        """Validate all parameters against schema"""
        
        action_id = plan.get('selected_remediation')
        parameters = plan.get('execution_plan', {}).get('parameters', {})
        
        # Get parameter schema from registry
        registry_action = await self.registry.get_action(action_id)
        param_schemas = {p['name']: p for p in registry_action.get('parameters', [])}
        
        errors = []
        
        # Check each parameter
        for param_name, param_value in parameters.items():
            if param_name not in param_schemas:
                errors.append(f"Unknown parameter: {param_name}")
                continue
            
            schema = param_schemas[param_name]
            
            # Type validation
            expected_type = schema.get('type', 'string')
            if expected_type == 'string' and not isinstance(param_value, str):
                errors.append(f"{param_name}: expected string, got {type(param_value).__name__}")
            elif expected_type == 'int' and not isinstance(param_value, int):
                errors.append(f"{param_name}: expected int, got {type(param_value).__name__}")
            elif expected_type == 'boolean' and not isinstance(param_value, bool):
                errors.append(f"{param_name}: expected boolean, got {type(param_value).__name__}")
            
            # Regex validation
            if 'validation_regex' in schema:
                if not re.match(schema['validation_regex'], str(param_value)):
                    errors.append(f"{param_name}: failed regex validation")
            
            # Allowed values
            if 'allowed_values' in schema:
                if param_value not in schema['allowed_values']:
                    errors.append(f"{param_name}: value not in allowed list")
            
            # Min/max validation
            if expected_type == 'int':
                if 'min_value' in schema and param_value < schema['min_value']:
                    errors.append(f"{param_name}: below minimum {schema['min_value']}")
                if 'max_value' in schema and param_value > schema['max_value']:
                    errors.append(f"{param_name}: above maximum {schema['max_value']}")
        
        # Check required parameters
        for param_name, schema in param_schemas.items():
            if schema.get('required', False) and param_name not in parameters:
                if 'default' not in schema:
                    errors.append(f"{param_name}: required parameter missing")
        
        if errors:
            return type('obj', (object,), {
                'valid': False,
                'reason': f"Parameter validation failed: {', '.join(errors)}"
            })()
        
        return type('obj', (object,), {'valid': True, 'reason': 'OK'})()
    
    def _detect_prompt_injection(self, plan: Dict[str, Any]) -> Any:
        """Detect prompt injection attempts"""
        
        # Convert plan to string for pattern matching
        plan_str = json.dumps(plan).lower()
        
        # Check for suspicious patterns
        if self.injection_regex.search(plan_str):
            # Find which pattern matched
            for pattern in self.injection_patterns:
                if re.search(pattern, plan_str, re.IGNORECASE):
                    return type('obj', (object,), {
                        'detected': True,
                        'details': f"Suspicious pattern detected: {pattern}"
                    })()
        
        # Check for excessive special characters (obfuscation attempt)
        special_char_count = sum(1 for c in plan_str if c in '<>|&;`$(){}[]\\')
        if special_char_count > 20:
            return type('obj', (object,), {
                'detected': True,
                'details': f"Excessive special characters: {special_char_count}"
            })()
        
        return type('obj', (object,), {'detected': False, 'details': ''})()
    
    async def _get_service_criticality(self, service_name: str) -> str:
        """Get service criticality level"""
        # Query service catalog
        service_info = await self.registry.get_service_info(service_name)
        return service_info.get('criticality', 'medium')
    
    async def _get_recent_executions(self, action_id: str) -> Dict[str, Any]:
        """Get recent execution history for action"""
        # Query execution history database or in-memory tracking
        try:
            if hasattr(self, '_execution_history'):
                # Filter executions for this action in last 24 hours
                import time
                current_time = time.time()
                recent = [
                    e for e in self._execution_history
                    if e.get('action_id') == action_id
                    and current_time - e.get('timestamp', 0) < 86400
                ]
                
                failures = sum(1 for e in recent if not e.get('success', False))
                failure_rate = failures / len(recent) if recent else 0.0
                
                # Find most recent execution
                if recent:
                    most_recent = max(recent, key=lambda x: x.get('timestamp', 0))
                    minutes_ago = (current_time - most_recent.get('timestamp', 0)) / 60
                else:
                    minutes_ago = 999
                
                return {
                    'last_execution_minutes_ago': int(minutes_ago),
                    'failure_rate_last_24h': failure_rate,
                    'total_executions': len(recent)
                }
            
            # Fallback if no history available
            return {
                'last_execution_minutes_ago': 999,
                'failure_rate_last_24h': 0.0,
                'total_executions': 0
            }
        except Exception:
            return {
                'last_execution_minutes_ago': 999,
                'failure_rate_last_24h': 0.0,
                'total_executions': 0
            }
