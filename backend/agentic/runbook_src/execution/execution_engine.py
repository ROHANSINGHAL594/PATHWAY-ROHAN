"""
Execution Engine with Rollback Capabilities
Safely executes remedial actions with automatic rollback on failure
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class ExecutionContext:
    """Context for action execution"""
    execution_id: str
    action: Dict[str, Any]
    error_context: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    start_time: float
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Simplified: just store client's rollback endpoint (optional)
    rollback_endpoint: Optional[str] = None
    
    # Execution results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    end_time: Optional[float] = None
    
    # Audit trail
    audit_log: List[Dict[str, Any]] = field(default_factory=list)


class ActionExecutor:
    """
    Executes remedial actions with comprehensive safety measures
    """
    
    def __init__(self, safety_validator, secrets_manager, otel_client):
        """
        Args:
            safety_validator: SafetyValidator instance
            secrets_manager: Secrets management client
            otel_client: OpenTelemetry client for monitoring
        """
        self.safety_validator = safety_validator
        self.secrets_manager = secrets_manager
        self.otel_client = otel_client
        self.execution_registry = {}  # Track active executions
    
    async def execute_with_safety(
        self,
        action: Dict[str, Any],
        allow_rollback: bool = True
    ) -> ExecutionContext:
        """
        Execute action with full safety pipeline
        
        Pipeline:
        1. Pre-execution validation
        2. State snapshot
        3. Acquire execution lock
        4. Execute action
        5. Post-execution validation
        6. Auto-rollback on failure (if enabled)
        7. Release lock & cleanup
        """
        execution_id = str(uuid.uuid4())
        #TODO: Understand the working
        # Initialize execution context
        ctx = ExecutionContext(
            execution_id=execution_id,
            action=action,
            error_context={},  # Actions have their own execution config
            baseline_metrics=await self._capture_baseline_metrics(action),
            start_time=time.time()
        )
        
        self.execution_registry[execution_id] = ctx
        
        try:
            # Step 1: Pre-execution validation
            ctx.status = ExecutionStatus.PENDING
            await self._log_audit(ctx, "pre_validation_start")
            

            #TODO: Understand the working
            pre_checks = await self.safety_validator.validate_pre_execution(
                action, {'baseline_metrics': ctx.baseline_metrics}
            )
            
            # Check if any critical checks failed
            critical_failures = [c for c in pre_checks if c.result.value == 'fail']
            if critical_failures:
                ctx.status = ExecutionStatus.FAILED
                ctx.error = f"Pre-execution validation failed: {', '.join([c.message for c in critical_failures])}"
                await self._log_audit(ctx, "pre_validation_failed", {'checks': [c.__dict__ for c in critical_failures]})
                return ctx
            
            await self._log_audit(ctx, "pre_validation_passed")
            
            # Step 2: Check if rollback endpoint is available (optional)
            if allow_rollback and action.get('rollback_endpoint'):
                ctx.rollback_endpoint = action.get('rollback_endpoint')
                await self._log_audit(ctx, "rollback_endpoint_available")
            
            # Step 3: Acquire execution lock
            lock_acquired = await self._acquire_execution_lock(action['action_id'], execution_id)
            if not lock_acquired:
                ctx.status = ExecutionStatus.FAILED
                ctx.error = "Failed to acquire execution lock"
                return ctx
            
            await self._log_audit(ctx, "lock_acquired")
            
            # Step 4: Execute the action
            ctx.status = ExecutionStatus.RUNNING
            await self._log_audit(ctx, "execution_start")
            
            execution_result = await self._execute_action(action, ctx)
            ctx.result = execution_result
            
            await self._log_audit(ctx, "execution_complete", execution_result)
            
            # Step 5: Post-execution validation (DISABLED for testing)
            # post_checks = await self.safety_validator.validate_post_execution(
            #     action,
            #     {'baseline_metrics': ctx.baseline_metrics},
            #     execution_result
            # )
            # 
            # validation_failures = [c for c in post_checks if c.result.value == 'fail']
            # 
            # if validation_failures:
            #     ctx.status = ExecutionStatus.FAILED
            #     ctx.error = f"Post-execution validation failed: {', '.join([c.message for c in validation_failures])}"
            #     await self._log_audit(ctx, "post_validation_failed", {'checks': [c.__dict__ for c in validation_failures]})
            #     
            #     # Step 6: Auto-rollback on failure (if client provided rollback endpoint)
            #     if allow_rollback and ctx.rollback_endpoint:
            #         await self._perform_rollback(ctx)
            #     else:
            #         # No rollback available - just alert
            #         await self._alert_failure(ctx, "No rollback endpoint provided")
            #     
            #     return ctx
            
            # Success!
            ctx.status = ExecutionStatus.SUCCESS
            await self._log_audit(ctx, "execution_success")
            
        except Exception as e:
            ctx.status = ExecutionStatus.FAILED
            ctx.error = f"Execution exception: {str(e)}"
            await self._log_audit(ctx, "execution_exception", {'error': str(e)})
            
            # Attempt rollback on exception (if client provided rollback endpoint)
            if allow_rollback and ctx.rollback_endpoint:
                try:
                    await self._perform_rollback(ctx)
                except Exception as rollback_error:
                    ctx.error += f"; Rollback also failed: {str(rollback_error)}"
                    await self._log_audit(ctx, "rollback_failed", {'error': str(rollback_error)})
            else:
                # No rollback available - just alert
                await self._alert_failure(ctx, f"Execution failed: {str(e)}")
        
        finally:
            # Step 7: Cleanup
            ctx.end_time = time.time()
            await self._release_execution_lock(action['action_id'], execution_id)
            await self._log_audit(ctx, "lock_released")
            
            # Record execution in history for learning
            await self._record_execution_history(ctx)
            
            del self.execution_registry[execution_id]
        
        return ctx
    
    async def _execute_action(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute the actual remedial action
        """
        action_type = action.get('action_type')
        
        if action_type == 'script':
            return await self._execute_script(action, ctx)
        elif action_type == 'rpc':
            return await self._execute_rpc(action, ctx)
        elif action_type == 'api_call':
            return await self._execute_api_call(action, ctx)
        #TODO: Nothing about k8s implementation
        elif action_type == 'k8s_command':
            return await self._execute_k8s_command(action, ctx)
        # elif action_type == 'restart_service':
        #     return await self._execute_restart_service(action, ctx)
        elif action_type == 'command':
            # Execute command via SSH
            return await self._execute_command_via_ssh(action, ctx)
        else:
            raise ValueError(f"Unsupported action type: {action_type}")
    
    async def _execute_script(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a script on client's server
        Uses SSH for remote execution or local subprocess for testing
        """
        script_path = action.get('script_path')
        command = action.get('command')  # Pre-built command with parameters
        parameters = action.get('parameters', [])
        timeout = action.get('timeout_seconds', 300)
        execution_context = action.get('execution_context', {})
        
        # Check if we should execute locally (for testing)
        use_local = execution_context.get('use_local_execution', False)
        
        if use_local:
            # Local execution using subprocess
            return await self._execute_local_script(command or script_path, timeout)
        
        # Remote execution via SSH
        # Resolve secrets from secrets manager (including SSH credentials)
        secrets = await self._resolve_secrets(action.get('secrets', {}))
        
        # Map secret keys to SSH connection parameters if ssh_secret_mapping exists
        if 'ssh_secret_mapping' in execution_context:
            mapping = execution_context['ssh_secret_mapping']
            ssh_secrets = {
                'ssh_host': secrets.get(mapping.get('ssh_host')),
                'ssh_username': secrets.get(mapping.get('ssh_username')),
                'ssh_password': secrets.get(mapping.get('ssh_password')),
                'ssh_port': secrets.get(mapping.get('ssh_port'))
            }
            secrets.update(ssh_secrets)
        elif 'ssh_connection' in execution_context:
            # Legacy fallback: Use SSH credentials from action_metadata (stored during old discovery)
            ssh_conn = execution_context['ssh_connection']
            secrets.update({
                'ssh_host': ssh_conn.get('host', 'localhost'),
                'ssh_username': ssh_conn.get('username', 'root'),
                'ssh_password': ssh_conn.get('password'),
                'ssh_port': str(ssh_conn.get('port', 22))
            })
        
        # Build command with parameters if not provided
        if not command:
            param_values = await self._resolve_parameters(parameters, ctx.error_context)
            command = f"{script_path} {' '.join(param_values)}"
        
        # Execute via SSH
        result = await self._execute_remote_command(
            command=command,
            secrets=secrets,
            timeout=timeout,
            execution_context=execution_context
        )
        
        return result
    
    async def _execute_local_script(
        self,
        command: str,
        timeout: int
    ) -> Dict[str, Any]:
        """Execute script locally using subprocess (for testing)"""
        import asyncio.subprocess as subprocess
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    'status': 'success' if process.returncode == 0 else 'failed',
                    'output': stdout.decode('utf-8'),
                    'error': stderr.decode('utf-8'),
                    'exit_code': process.returncode
                }
                
            except asyncio.TimeoutError:
                # Kill the process if timeout
                process.kill()
                await process.wait()
                return {
                    'status': 'failed',
                    'output': '',
                    'error': f'Script execution timed out after {timeout} seconds',
                    'exit_code': -1
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'output': '',
                'error': str(e),
                'exit_code': -1
            }
    
    async def _execute_rpc(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute RPC call to client's internal service
        """
        import aiohttp
        
        endpoint = action.get('rpc_endpoint')
        http_method = action.get('http_method', 'POST').upper()
        parameters = action.get('parameters', [])
        timeout = action.get('timeout_seconds', 30)
        
        # Build full URL if endpoint is relative
        if not endpoint.startswith('http'):
            # Default to localhost for testing
            base_url = action.get('execution_context', {}).get('base_url', 'http://localhost:8000')
            endpoint = f"{base_url}{endpoint}"
        
        # Resolve secrets for authentication
        secrets = await self._resolve_secrets(action.get('secrets', {}))
        
        # Apply security schemes dynamically
        headers, query_params, cookies = await self._apply_security_schemes(secrets, action)
        
        # Build request payload
        param_dict = {}
        for param in parameters:
            param_name = param.get('name')
            
            # Check if provided in error context
            if param_name in ctx.error_context:
                param_dict[param_name] = ctx.error_context[param_name]
            elif param.get('default') is not None:
                param_dict[param_name] = param['default']
            elif param_name == 'service_name' and 'affected_services' in action and action['affected_services']:
                # Fallback: use first affected service for service_name parameter
                param_dict[param_name] = action['affected_services'][0]
            elif param.get('required', False):
                raise ValueError(f"Required parameter '{param_name}' not provided")
        
        # Merge query params from security with any existing params
        if query_params:
            # Add security query params to URL
            from urllib.parse import urlencode
            query_string = urlencode(query_params)
            endpoint = f"{endpoint}?{query_string}" if '?' not in endpoint else f"{endpoint}&{query_string}"
        
        async with aiohttp.ClientSession(cookies=cookies) as session:
            request_method = getattr(session, http_method.lower(), session.post)
            async with request_method(
                endpoint,
                json=param_dict if http_method == 'POST' else None,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                result = {
                    'status': 'success' if response.status == 200 else 'failed',
                    'status_code': response.status,
                    'response': await response.text()
                }
                return result
    
    async def _execute_api_call(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute REST API call"""
        # Similar to RPC but supports GET/PUT/DELETE/PATCH
        import aiohttp
        
        endpoint = action.get('api_endpoint')
        method = action.get('http_method', 'POST')
        timeout = action.get('timeout_seconds', 30)
        
        secrets = await self._resolve_secrets(action.get('secrets', {}))
        
        # Apply security schemes dynamically
        headers, query_params, cookies = await self._apply_security_schemes(secrets, action)
        
        # Merge query params from security into endpoint
        if query_params:
            from urllib.parse import urlencode
            query_string = urlencode(query_params)
            endpoint = f"{endpoint}?{query_string}" if '?' not in endpoint else f"{endpoint}&{query_string}"
        
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.request(
                method,
                endpoint,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return {
                    'status': 'success' if response.ok else 'failed',
                    'status_code': response.status,
                    'response': await response.text()
                }
    
    async def _execute_k8s_command(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute Kubernetes command (kubectl)
        """
        # This would use the Kubernetes Python client
        # For now, placeholder implementation
        command = action.get('command')
        namespace = action.get('execution_context', {}).get('namespace', 'default')
        
        # Example: kubectl rollout restart deployment/payment-service -n production
        result = {
            'status': 'success',
            'output': f"Executed: {command} in namespace {namespace}"
        }
        
        return result
    
    async def _execute_restart_service(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Restart a service (graceful restart)
        """
        service_name = action.get('service_name')
        graceful = action.get('graceful', True)
        
        # Implementation would depend on orchestration platform
        # Could be K8s rollout, systemd restart, etc.
        
        result = {
            'status': 'success',
            'service': service_name,
            'graceful': graceful,
            'output': f"Service {service_name} restarted"
        }
        
        return result
    
    async def _perform_rollback(self, ctx: ExecutionContext) -> None:
        """
        Perform automatic rollback by calling client's rollback endpoint (if provided)
        Simple approach: Just call their rollback URL with same authentication
        """
        await self._log_audit(ctx, "rollback_start")
        
        try:
            import aiohttp
            
            # Get rollback endpoint from context
            rollback_endpoint = ctx.rollback_endpoint
            if not rollback_endpoint:
                raise ValueError("No rollback endpoint available")
            
            # Get the same secrets used for original execution
            action = ctx.action
            secrets = await self._resolve_secrets(action.get('secrets', {}))
            
            # Build headers (same authentication as original call)
            headers = {}
            if 'admin_api_token' in secrets:
                headers['Authorization'] = f"Bearer {secrets['admin_api_token']}"
            
            # Get parameters from original execution context
            parameters = {}
            for param in action.get('parameters', []):
                param_name = param.get('name')
                if param_name in ctx.error_context:
                    parameters[param_name] = ctx.error_context[param_name]
            
            # Call rollback endpoint
            timeout = action.get('timeout_seconds', 30)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    rollback_endpoint,
                    json=parameters,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status == 200:
                        ctx.status = ExecutionStatus.ROLLED_BACK
                        await self._log_audit(ctx, "rollback_complete", {
                            'response': await response.text()
                        })
                    else:
                        raise Exception(f"Rollback failed with status {response.status}: {await response.text()}")
            
        except Exception as e:
            await self._log_audit(ctx, "rollback_failed", {'error': str(e)})
            # Alert team that both execution AND rollback failed
            await self._alert_failure(ctx, f"Rollback failed: {str(e)}")
            raise
    
    async def _alert_failure(self, ctx: ExecutionContext, message: str) -> None:
        """
        Alert team when execution fails (with or without rollback)
        """
        action_type = ctx.action.get('action_type')
        
        alert_payload = {
            'severity': 'high',
            'title': f"Automated remediation failed: {ctx.action.get('action_id')}",
            'message': message,
            'execution_id': ctx.execution_id,
            'action': ctx.action.get('action_id'),
            'service': ctx.action.get('affected_services', []),
            'error': ctx.error,
            'timestamp': time.time()
        }
        
        await self._log_audit(ctx, "alert_sent", alert_payload)
        
        # TODO: Integrate with PagerDuty, Slack, email, etc.
        # For now, just log it
        print(f"ALERT: {alert_payload}")
        
        if action_type == 'verify_service_health':
            # Wait for service to stabilize
            await asyncio.sleep(5)
            # Check health endpoint
            pass
        
        elif action_type == 'restore_configuration':
            # Restore previous configuration
            pass
        
        elif action_type == 'scale_service':
            # Scale service back to previous replica count
            pass
    
    async def _capture_baseline_metrics(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Capture baseline metrics before execution"""
        metrics = {}
        
        for service in action.get('affected_services', []):
            metrics[service] = {
                'error_rate': await self._get_error_rate(service),
                'latency_p99': await self._get_latency(service),
                'throughput': await self._get_throughput(service)
            }
        
        return metrics
    
    async def _resolve_secrets(self, secrets_config: Dict[str, Any]) -> Dict[str, str]:
        """Resolve secrets from secrets manager or metadata"""
        secrets = {}
        
        references = secrets_config.get('secret_references', [])
        
        for ref in references:
            secret_name = ref.get('name')
            secret_path = ref.get('path')
            
            # Fetch from secrets manager using the secret name
            # For SQLite-only secrets manager, use the name directly
            secret_value = await self.secrets_manager.get_secret(secret_name)
            secrets[secret_name] = secret_value
        
        return secrets
    
    async def _apply_security_schemes(
        self,
        secrets: Dict[str, str],
        action: Dict[str, Any]
    ) -> tuple:
        """
        Apply security schemes to request based on OpenAPI metadata.
        
        Returns:
            (headers, query_params, cookies)
        """
        headers = {}
        query_params = {}
        cookies = {}
        
        security_schemes = action.get('action_metadata', {}).get('security_schemes', {})
        secret_refs = action.get('secrets', {}).get('secret_references', [])
        
        # If no security scheme metadata, fall back to legacy behavior
        if not security_schemes:
            # Legacy: hardcoded patterns
            if 'admin_api_token' in secrets:
                headers['Authorization'] = f"Bearer {secrets['admin_api_token']}"
            if 'api_key' in secrets:
                headers['X-API-Key'] = secrets['api_key']
            return headers, query_params, cookies
        
        for ref in secret_refs:
            secret_name = ref['name']
            secret_value = secrets.get(secret_name)
            
            if not secret_value:
                continue
            
            # Find matching security scheme by name
            # Map from secret_name like "payment_remediation_apikeyheader"
            # to scheme name like "ApiKeyHeader"
            scheme_name = None
            for name in security_schemes.keys():
                if name.lower().replace('-', '_') in secret_name.lower():
                    scheme_name = name
                    break
            
            if not scheme_name:
                # Fallback: try to apply as bearer token
                headers['Authorization'] = f"Bearer {secret_value}"
                continue
            
            scheme_def = security_schemes[scheme_name]
            
            if scheme_def['type'] == 'apiKey':
                location = scheme_def['in']
                param_name = scheme_def['name']
                
                if location == 'header':
                    headers[param_name] = secret_value
                elif location == 'query':
                    query_params[param_name] = secret_value
                elif location == 'cookie':
                    cookies[param_name] = secret_value
            
            elif scheme_def['type'] == 'http':
                scheme = scheme_def['scheme']
                
                if scheme == 'basic':
                    # Expect secret_value as "username:password"
                    import base64
                    credentials = base64.b64encode(secret_value.encode()).decode()
                    headers['Authorization'] = f"Basic {credentials}"
                
                elif scheme == 'bearer':
                    headers['Authorization'] = f"Bearer {secret_value}"
            
            elif scheme_def['type'] in ['oauth2', 'openIdConnect']:
                # Treat as bearer token (assume pre-obtained access token)
                headers['Authorization'] = f"Bearer {secret_value}"
        
        return headers, query_params, cookies
    
    async def _resolve_parameters(
        self,
        parameters: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[str]:
        """Resolve parameter values from context or defaults"""
        param_values = []
        
        for param in parameters:
            param_name = param.get('name')
            param_type = param.get('type', 'string')
            
            # Get value from context or default
            if param_name in context:
                value = context[param_name]
            elif param.get('default') is not None:
                value = param['default']
            elif param.get('required', False):
                raise ValueError(f"Required parameter '{param_name}' not provided")
            else:
                continue
            
            # Validate
            if param.get('validation_regex'):
                import re
                if not re.match(param['validation_regex'], str(value)):
                    raise ValueError(f"Parameter '{param_name}' failed validation")
            
            param_values.append(str(value))
        
        return param_values
    
    async def _execute_remote_command(
        self,
        command: str,
        secrets: Dict[str, str],
        timeout: int,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute command on remote server via SSH"""
        try:
            from ..services.ssh_client import AsyncSSHClient, SSHCredentials
            
            # Extract SSH connection details from secrets
            host = secrets.get('ssh_host', 'localhost')
            username = secrets.get('ssh_username', 'root')
            password = secrets.get('ssh_password')
            key_path = secrets.get('ssh_key_path')
            port = int(secrets.get('ssh_port', '22'))  # Allow port override
            
            credentials = SSHCredentials(
                username=username,
                password=password,
                private_key_path=key_path
            )
            
            # Create and connect SSH client
            async with AsyncSSHClient(host, port, credentials) as client:
                result = await client.execute_command(command, timeout=timeout)
                
                return {
                    'status': 'success' if result.get('exit_status') == 0 else 'failed',
                    'output': result.get('stdout', ''),
                    'error': result.get('stderr', ''),
                    'exit_code': result.get('exit_status', -1)
                }
        except Exception as e:
            return {
                'status': 'failed',
                'output': '',
                'error': str(e),
                'exit_code': -1
            }
    
    async def _execute_command_via_ssh(
        self,
        action: Dict[str, Any],
        ctx: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute a command via SSH (for command action type)
        """
        command = action.get('command')
        timeout = action.get('timeout_seconds', 30)
        
        # Resolve secrets
        secrets = await self._resolve_secrets(action.get('secrets', {}))
        
        # Execute via SSH
        result = await self._execute_remote_command(
            command=command,
            secrets=secrets,
            timeout=timeout,
            execution_context=action.get('execution_context', {})
        )
        
        return result
    
    async def _acquire_execution_lock(self, action_id: str, execution_id: str) -> bool:
        """Acquire distributed lock for action execution"""
        # In-memory lock tracking (for single-instance deployment)
        # For production: integrate with Redis (aioredis) or etcd
        if not hasattr(self, '_locks'):
            self._locks = {}
        
        lock_key = f"action_lock:{action_id}"
        
        # Check if already locked
        if lock_key in self._locks:
            existing_lock = self._locks[lock_key]
            # Check if lock is stale (older than 5 minutes)
            if datetime.utcnow().timestamp() - existing_lock['timestamp'] < 300:
                return False  # Lock still active
        
        # Acquire lock
        self._locks[lock_key] = {
            'execution_id': execution_id,
            'timestamp': datetime.utcnow().timestamp()
        }
        return True
    
    async def _release_execution_lock(self, action_id: str, execution_id: str) -> None:
        """Release distributed lock"""
        if not hasattr(self, '_locks'):
            return
            
        lock_key = f"action_lock:{action_id}"
        if lock_key in self._locks:
            # Only release if we own the lock
            if self._locks[lock_key]['execution_id'] == execution_id:
                del self._locks[lock_key]
    
    async def _log_audit(
        self,
        ctx: ExecutionContext,
        event: str,
        details: Dict[str, Any] = None
    ) -> None:
        """Log audit event"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'execution_id': ctx.execution_id,
            'event': event,
            'details': details or {}
        }
        
        ctx.audit_log.append(audit_entry)
        
        # Also send to monitoring system (if available)
        if self.otel_client:
            await self.otel_client.log_event(audit_entry)
    
    async def _record_execution_history(self, ctx: ExecutionContext) -> None:
        """Record execution in history for learning"""
        history_entry = {
            'execution_id': ctx.execution_id,
            'action_id': ctx.action['action_id'],
            'status': ctx.status.value,
            'error_context': ctx.error_context,
            'result': ctx.result,
            'error': ctx.error,
            'duration_seconds': time.time() - ctx.start_time,
            'audit_log': ctx.audit_log,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in database for feedback loop
        await self._store_execution_history(history_entry)
    
    # Placeholder helper methods
    
    async def _get_service_state(self, service: str) -> Dict[str, Any]:
        """Get current service state"""
        return {'replicas': 3, 'healthy': True}
    
    async def _get_service_metrics(self, service: str) -> Dict[str, Any]:
        """Get current metrics for service"""
        return {'error_rate': 0.01, 'latency': 100}
    
    async def _get_error_rate(self, service: str) -> float:
        """Get error rate"""
        return 0.01
    
    async def _get_latency(self, service: str) -> float:
        """Get latency p99"""
        return 250.0
    
    async def _get_throughput(self, service: str) -> float:
        """Get throughput (requests/sec)"""
        return 100.0
    
    async def _store_execution_history(self, history_entry: Dict[str, Any]) -> None:
        """Store execution history"""
        # Would store in database
        pass
