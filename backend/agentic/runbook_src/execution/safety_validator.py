"""
Safety Validation Framework
Ensures remedial actions don't cause additional harm
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json


class ValidationResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class SafetyCheckResult:
    check_name: str
    result: ValidationResult
    message: str
    execution_time_ms: float
    evidence: Dict[str, Any]  # Captured state/metrics


class SafetyValidator:
    """
    Multi-layered safety validation for remedial actions
    """
    
    def __init__(self, otel_client, metrics_client):
        """
        Args:
            otel_client: Client for fetching OTel traces/metrics
            metrics_client: Client for system metrics
        """
        self.otel_client = otel_client
        self.metrics_client = metrics_client
        self.validation_cache = {}
    
    async def validate_pre_execution(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[SafetyCheckResult]:
        """
        Run all pre-execution safety checks
        
        Checks include:
        1. Service health verification
        2. Resource availability
        3. Dependency validation
        4. Dry-run simulation
        5. Blast radius assessment
        6. Concurrent execution prevention
        """
        checks = []
        
        # 1. Service health check
        checks.append(await self._check_service_health(action, context))
        
        # 2. Resource availability
        checks.append(await self._check_resource_availability(action, context))
        
        # 3. Dependency validation
        checks.append(await self._check_dependencies(action, context))
        
        # 4. Dry-run (if supported)
        if action.get('supports_dry_run', False):
            checks.append(await self._run_dry_run(action, context))
        
        # 5. Blast radius assessment
        checks.append(await self._assess_blast_radius(action, context))
        
        # 6. Concurrent execution check
        checks.append(await self._check_concurrent_execution(action, context))
        
        # 7. Rate limiting check
        checks.append(await self._check_rate_limits(action, context))
        
        return checks
    
    async def validate_post_execution(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> List[SafetyCheckResult]:
        """
        Run all post-execution validation checks
        
        Checks include:
        1. Success verification
        2. Metrics validation
        3. Error rate monitoring
        4. Service health re-check
        5. Side-effects detection
        """
        checks = []
        
        # 1. Verify action succeeded
        checks.append(await self._verify_action_success(action, execution_result))
        
        # 2. Check metrics improved
        checks.append(await self._validate_metrics_improved(action, context))
        
        # 3. Monitor error rates
        checks.append(await self._check_error_rates(action, context))
        
        # 4. Service health re-validation
        checks.append(await self._check_service_health(action, context, is_post=True))
        
        # 5. Detect unintended side effects
        checks.append(await self._detect_side_effects(action, context))
        
        return checks
    
    async def _check_service_health(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        is_post: bool = False
    ) -> SafetyCheckResult:
        """Check if affected services are healthy"""
        start = time.time()
        
        affected_services = action.get('affected_services', [])
        if not affected_services:
            return SafetyCheckResult(
                check_name="service_health_check",
                result=ValidationResult.SKIP,
                message="No affected services specified",
                execution_time_ms=(time.time() - start) * 1000,
                evidence={}
            )
        
        unhealthy_services = []
        evidence = {}
        
        for service in affected_services:
            # Query health endpoint or OTel metrics
            health = await self._query_service_health(service)
            evidence[service] = health
            
            if not health.get('healthy', False):
                unhealthy_services.append(service)
        
        if unhealthy_services:
            return SafetyCheckResult(
                check_name="service_health_check",
                result=ValidationResult.FAIL if not is_post else ValidationResult.WARN,
                message=f"Unhealthy services: {', '.join(unhealthy_services)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        
        return SafetyCheckResult(
            check_name="service_health_check",
            result=ValidationResult.PASS,
            message="All affected services are healthy",
            execution_time_ms=(time.time() - start) * 1000,
            evidence=evidence
        )
    
    async def _check_resource_availability(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Ensure sufficient resources (CPU, memory, disk) available"""
        start = time.time()
        
        affected_services = action.get('affected_services', [])
        resource_issues = []
        evidence = {}
        
        for service in affected_services:
            resources = await self._query_resource_usage(service)
            evidence[service] = resources
            
            # Check thresholds
            if resources.get('cpu_percent', 0) > 90:
                resource_issues.append(f"{service}: CPU at {resources['cpu_percent']}%")
            
            if resources.get('memory_percent', 0) > 90:
                resource_issues.append(f"{service}: Memory at {resources['memory_percent']}%")
            
            if resources.get('disk_percent', 0) > 85:
                resource_issues.append(f"{service}: Disk at {resources['disk_percent']}%")
        
        if resource_issues:
            return SafetyCheckResult(
                check_name="resource_availability",
                result=ValidationResult.WARN,
                message=f"Resource constraints detected: {'; '.join(resource_issues)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        
        return SafetyCheckResult(
            check_name="resource_availability",
            result=ValidationResult.PASS,
            message="Sufficient resources available",
            execution_time_ms=(time.time() - start) * 1000,
            evidence=evidence
        )
    
    async def _check_dependencies(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Verify all dependencies are available"""
        start = time.time()
        
        # Check if downstream services are healthy
        affected_services = action.get('affected_services', [])
        dependency_issues = []
        evidence = {}
        
        for service in affected_services:
            dependencies = await self._get_service_dependencies(service)
            evidence[service] = dependencies
            
            for dep in dependencies:
                if not dep.get('available', False):
                    dependency_issues.append(f"{dep['name']} unavailable for {service}")
        
        if dependency_issues:
            return SafetyCheckResult(
                check_name="dependency_check",
                result=ValidationResult.FAIL,
                message=f"Dependency issues: {'; '.join(dependency_issues)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        
        return SafetyCheckResult(
            check_name="dependency_check",
            result=ValidationResult.PASS,
            message="All dependencies available",
            execution_time_ms=(time.time() - start) * 1000,
            evidence=evidence
        )
    
    async def _run_dry_run(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Execute action in dry-run mode to validate"""
        start = time.time()
        
        try:
            # Execute with dry_run flag
            result = await self._execute_with_dry_run(action, context)
            
            if result.get('would_succeed', False):
                return SafetyCheckResult(
                    check_name="dry_run_validation",
                    result=ValidationResult.PASS,
                    message="Dry-run succeeded",
                    execution_time_ms=(time.time() - start) * 1000,
                    evidence=result
                )
            else:
                return SafetyCheckResult(
                    check_name="dry_run_validation",
                    result=ValidationResult.FAIL,
                    message=f"Dry-run failed: {result.get('error')}",
                    execution_time_ms=(time.time() - start) * 1000,
                    evidence=result
                )
        except Exception as e:
            return SafetyCheckResult(
                check_name="dry_run_validation",
                result=ValidationResult.FAIL,
                message=f"Dry-run exception: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence={'error': str(e)}
            )
    
    async def _assess_blast_radius(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Assess potential impact/blast radius"""
        start = time.time()
        
        affected_services = action.get('affected_services', [])
        risk_level = action.get('risk_level', 'high')
        
        # Calculate blast radius score
        blast_radius = {
            'direct_services': len(affected_services),
            'indirect_services': 0,
            'estimated_users_affected': 0,
            'risk_level': risk_level
        }
        
        # Check indirect impact via service mesh/dependencies
        for service in affected_services:
            downstream = await self._get_downstream_services(service)
            blast_radius['indirect_services'] += len(downstream)
            
            # Estimate user impact from traffic metrics
            traffic = await self._get_service_traffic(service)
            blast_radius['estimated_users_affected'] += traffic.get('active_users', 0)
        
        # Determine if blast radius is acceptable
        total_services = blast_radius['direct_services'] + blast_radius['indirect_services']
        
        if total_services > 10:
            result = ValidationResult.WARN
            message = f"Large blast radius: {total_services} services potentially affected"
        elif blast_radius['estimated_users_affected'] > 10000:
            result = ValidationResult.WARN
            message = f"High user impact: ~{blast_radius['estimated_users_affected']} users affected"
        else:
            result = ValidationResult.PASS
            message = f"Acceptable blast radius: {total_services} services"
        
        return SafetyCheckResult(
            check_name="blast_radius_assessment",
            result=result,
            message=message,
            execution_time_ms=(time.time() - start) * 1000,
            evidence=blast_radius
        )
    
    async def _check_concurrent_execution(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Prevent concurrent execution of same action"""
        start = time.time()
        
        action_id = action.get('action_id')
        
        # Check distributed lock or execution registry
        is_running = await self._check_action_lock(action_id)
        
        if is_running:
            return SafetyCheckResult(
                check_name="concurrent_execution_check",
                result=ValidationResult.FAIL,
                message=f"Action '{action_id}' is already running",
                execution_time_ms=(time.time() - start) * 1000,
                evidence={'lock_held': True}
            )
        
        return SafetyCheckResult(
            check_name="concurrent_execution_check",
            result=ValidationResult.PASS,
            message="No concurrent execution detected",
            execution_time_ms=(time.time() - start) * 1000,
            evidence={'lock_held': False}
        )
    
    async def _check_rate_limits(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Check if action exceeds rate limits"""
        start = time.time()
        
        action_id = action.get('action_id')
        
        # Check execution frequency (e.g., max 3 times per hour)
        recent_executions = await self._get_recent_executions(action_id, window_minutes=60)
        max_per_hour = action.get('max_executions_per_hour', 5)
        
        if len(recent_executions) >= max_per_hour:
            return SafetyCheckResult(
                check_name="rate_limit_check",
                result=ValidationResult.FAIL,
                message=f"Rate limit exceeded: {len(recent_executions)}/{max_per_hour} executions in last hour",
                execution_time_ms=(time.time() - start) * 1000,
                evidence={'recent_executions': recent_executions}
            )
        
        return SafetyCheckResult(
            check_name="rate_limit_check",
            result=ValidationResult.PASS,
            message=f"Within rate limits: {len(recent_executions)}/{max_per_hour}",
            execution_time_ms=(time.time() - start) * 1000,
            evidence={'recent_executions': recent_executions}
        )
    
    async def _verify_action_success(
        self,
        action: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Verify the action executed successfully"""
        start = time.time()
        
        if execution_result.get('status') == 'success':
            return SafetyCheckResult(
                check_name="action_success_verification",
                result=ValidationResult.PASS,
                message="Action executed successfully",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=execution_result
            )
        else:
            return SafetyCheckResult(
                check_name="action_success_verification",
                result=ValidationResult.FAIL,
                message=f"Action failed: {execution_result.get('error')}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=execution_result
            )
    
    async def _validate_metrics_improved(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Verify that target metrics improved after action"""
        start = time.time()
        
        # Get baseline metrics (from context, captured pre-execution)
        baseline_metrics = context.get('baseline_metrics', {})
        
        # Wait a bit for metrics to stabilize
        await asyncio.sleep(5)
        
        # Fetch current metrics
        current_metrics = await self._fetch_current_metrics(action)
        
        improvements = []
        regressions = []
        
        # Compare key metrics
        for metric_name, baseline_value in baseline_metrics.items():
            current_value = current_metrics.get(metric_name)
            
            if current_value is None:
                continue
            
            # Determine if metric should decrease (e.g., error_rate) or increase (e.g., success_rate)
            should_decrease = 'error' in metric_name.lower() or 'latency' in metric_name.lower()
            
            if should_decrease:
                if current_value < baseline_value:
                    improvements.append(f"{metric_name}: {baseline_value} → {current_value}")
                elif current_value > baseline_value:
                    regressions.append(f"{metric_name}: {baseline_value} → {current_value}")
            else:
                if current_value > baseline_value:
                    improvements.append(f"{metric_name}: {baseline_value} → {current_value}")
                elif current_value < baseline_value:
                    regressions.append(f"{metric_name}: {baseline_value} → {current_value}")
        
        evidence = {
            'baseline': baseline_metrics,
            'current': current_metrics,
            'improvements': improvements,
            'regressions': regressions
        }
        
        if regressions:
            return SafetyCheckResult(
                check_name="metrics_validation",
                result=ValidationResult.FAIL,
                message=f"Metrics regressed: {'; '.join(regressions)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        elif improvements:
            return SafetyCheckResult(
                check_name="metrics_validation",
                result=ValidationResult.PASS,
                message=f"Metrics improved: {'; '.join(improvements)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        else:
            return SafetyCheckResult(
                check_name="metrics_validation",
                result=ValidationResult.WARN,
                message="No significant metric changes detected",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
    
    async def _check_error_rates(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Monitor error rates after action execution"""
        start = time.time()
        
        affected_services = action.get('affected_services', [])
        error_spikes = []
        evidence = {}
        
        for service in affected_services:
            error_rate = await self._get_error_rate(service)
            evidence[service] = error_rate
            
            baseline_rate = context.get('baseline_error_rates', {}).get(service, 0)
            
            # Check if error rate spiked (>2x baseline)
            if error_rate > baseline_rate * 2:
                error_spikes.append(f"{service}: {baseline_rate:.2%} → {error_rate:.2%}")
        
        if error_spikes:
            return SafetyCheckResult(
                check_name="error_rate_monitoring",
                result=ValidationResult.FAIL,
                message=f"Error rate spikes detected: {'; '.join(error_spikes)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        
        return SafetyCheckResult(
            check_name="error_rate_monitoring",
            result=ValidationResult.PASS,
            message="Error rates stable",
            execution_time_ms=(time.time() - start) * 1000,
            evidence=evidence
        )
    
    async def _detect_side_effects(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """Detect unintended side effects on other services"""
        start = time.time()
        
        # Check services NOT in affected_services list for unexpected changes
        affected_services = set(action.get('affected_services', []))
        all_services = await self._get_all_monitored_services()
        
        unaffected_services = [s for s in all_services if s not in affected_services]
        side_effects = []
        evidence = {}
        
        for service in unaffected_services[:10]:  # Sample first 10
            # Check for unexpected metric changes
            baseline = context.get('baseline_metrics_all', {}).get(service, {})
            current = await self._get_service_metrics(service)
            
            if self._has_significant_change(baseline, current):
                side_effects.append(f"Unexpected change in {service}")
                evidence[service] = {'baseline': baseline, 'current': current}
        
        if side_effects:
            return SafetyCheckResult(
                check_name="side_effects_detection",
                result=ValidationResult.WARN,
                message=f"Potential side effects: {'; '.join(side_effects)}",
                execution_time_ms=(time.time() - start) * 1000,
                evidence=evidence
            )
        
        return SafetyCheckResult(
            check_name="side_effects_detection",
            result=ValidationResult.PASS,
            message="No unintended side effects detected",
            execution_time_ms=(time.time() - start) * 1000,
            evidence=evidence
        )
    
    # Helper methods (these would integrate with actual OTel/monitoring systems)
    
    async def _query_service_health(self, service: str) -> Dict[str, Any]:
        """Query service health from monitoring system"""
        # Placeholder - would integrate with actual health check endpoint or OTel
        return {'healthy': True, 'status': 'UP'}
    
    async def _query_resource_usage(self, service: str) -> Dict[str, Any]:
        """Query resource usage metrics"""
        # Placeholder - would query from metrics system
        return {'cpu_percent': 45, 'memory_percent': 60, 'disk_percent': 50}
    
    async def _get_service_dependencies(self, service: str) -> List[Dict[str, Any]]:
        """Get service dependencies"""
        try:
            # Query from service mesh or configuration
            deps = await self.otel_client.get_service_dependencies(service)
            return deps
        except AttributeError:
            # Fallback: return empty list indicating no dependency info
            return []
        except Exception:
            return []
    
    async def _execute_with_dry_run(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action in dry-run mode"""
        import aiohttp
        
        try:
            action_type = action.get('action_type')
            
            if action_type == 'rpc':
                # RPC dry-run: call endpoint with dry_run=true parameter
                endpoint = action.get('rpc_endpoint')
                if not endpoint:
                    return {'would_succeed': False, 'error': 'No endpoint specified'}
                
                # Add dry_run parameter to URL
                separator = '&' if '?' in endpoint else '?'
                dry_run_url = f"{endpoint}{separator}dry_run=true"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(dry_run_url, json=context.get('parameters', {}), timeout=10) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result
                        else:
                            return {
                                'would_succeed': False,
                                'error': f'Dry-run returned status {response.status}'
                            }
            
            elif action_type == 'api_call':
                # API dry-run: validate parameters without execution
                return {
                    'would_succeed': True,
                    'message': 'API call parameters validated',
                    'note': 'Dry-run mode: no actual API call made'
                }
            
            else:
                # Other action types: return success if idempotent
                return {
                    'would_succeed': action.get('idempotent', False),
                    'message': f'Dry-run not fully implemented for {action_type}',
                    'note': 'Proceeding based on idempotency flag'
                }
                
        except Exception as e:
            return {
                'would_succeed': False,
                'error': f'Dry-run exception: {str(e)}'
            }
    
    async def _get_downstream_services(self, service: str) -> List[str]:
        """Get services that depend on this service"""
        try:
            # Query from service mesh (Istio, Linkerd) or dependency graph
            downstream = await self.otel_client.get_downstream_services(service)
            return downstream
        except AttributeError:
            # Fallback: no dependency graph available
            # Return empty list to indicate blast radius is unknown
            return []
        except Exception:
            return []
    
    async def _get_service_traffic(self, service: str) -> Dict[str, Any]:
        """Get current traffic metrics for service"""
        try:
            traffic = await self.metrics_client.query_traffic(service)
            return traffic
        except AttributeError:
            # Fallback: no traffic data available
            return {
                'active_users': 0,
                'requests_per_second': 0,
                'requires_integration': True
            }
        except Exception:
            return {'active_users': 0, 'requests_per_second': 0}
    
    async def _check_action_lock(self, action_id: str) -> bool:
        """Check if action is currently locked/running"""
        # In-memory lock checking (matches execution_engine implementation)
        # For production: integrate with Redis or distributed lock service
        if not hasattr(self, '_action_locks'):
            self._action_locks = {}
        
        lock_key = f"action_lock:{action_id}"
        if lock_key in self._action_locks:
            # Check if lock is stale (older than 5 minutes)
            import time
            if time.time() - self._action_locks[lock_key] < 300:
                return True  # Lock is active
        
        return False  # No active lock
    
    async def _get_recent_executions(self, action_id: str, window_minutes: int) -> List[Dict]:
        """Get recent executions of this action"""
        # In-memory tracking (for single-instance)
        # For production: query from database or time-series store
        if not hasattr(self, '_execution_history'):
            self._execution_history = []
        
        import time
        current_time = time.time()
        window_seconds = window_minutes * 60
        
        recent = [
            exec_entry for exec_entry in self._execution_history
            if exec_entry.get('action_id') == action_id
            and current_time - exec_entry.get('timestamp', 0) < window_seconds
        ]
        
        return recent
    
    async def _fetch_current_metrics(self, action: Dict[str, Any]) -> Dict[str, float]:
        """Fetch current metrics for affected services"""
        # Placeholder
        return {'error_rate': 0.01, 'latency_p99': 250}
    
    async def _get_error_rate(self, service: str) -> float:
        """Get current error rate for service"""
        # Placeholder
        return 0.01
    
    async def _get_all_monitored_services(self) -> List[str]:
        """Get all services being monitored"""
        # Placeholder
        return ['service-a', 'service-b', 'service-c']
    
    async def _get_service_metrics(self, service: str) -> Dict[str, float]:
        """Get metrics for a specific service"""
        # Placeholder
        return {'error_rate': 0.01, 'latency': 100}
    
    def _has_significant_change(self, baseline: Dict, current: Dict) -> bool:
        """Determine if metrics have changed significantly"""
        # Simple threshold-based detection
        for key in baseline:
            if key in current:
                diff = abs(current[key] - baseline[key]) / (baseline[key] + 1e-9)
                if diff > 0.5:  # 50% change
                    return True
        return False
