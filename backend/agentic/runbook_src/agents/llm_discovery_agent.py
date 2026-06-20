"""
Simplified LLM Discovery Agent - Generate RemediationActions using Pydantic

This module provides a clean interface for using LLMs to discover and generate
RemediationAction instances with built-in Pydantic validation.
"""

import asyncio
import json
import textwrap
import uuid
import os
import logging
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from ..core.runbook_registry import RunbookRegistry, RemediationAction
from ..utils.discovery_protocols import ScriptHostClient, DocumentationFetcherProtocol, DefaultDocumentationFetcher
from ..agents.safe_discovery_agent import SafeDiscoveryAgent

load_dotenv()

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security validation fails"""
    pass

class RemediationActions(BaseModel):
    """Container for multiple RemediationAction instances"""
    actions: List[RemediationAction] = Field(
        description="List of discovered remediation actions"
    )


class EndpointCandidate(BaseModel):
    """Candidate endpoint identified by planner"""
    path: str = Field(description="API endpoint path")
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    operation_id: str = Field(description="OpenAPI operation ID")
    is_remediation: bool = Field(description="Whether this is a remediation endpoint")
    reason: str = Field(description="Why this was identified as remediation")


class EndpointCandidates(BaseModel):
    """Container for multiple endpoint candidates"""
    candidates: List[EndpointCandidate] = Field(
        description="List of remediation endpoint candidates"
    )


class SingleActionResponse(BaseModel):
    """Response for single endpoint processing"""
    action: RemediationAction = Field(
        description="Single discovered remediation action"
    )


class LLMDiscoveryAgent:
    """
    Use LLMs with structured Pydantic outputs to discover remediation actions
    
    This agent uses LangChain's with_structured_output() to guarantee that
    LLM responses match the RemediationAction schema.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        safety_agent: Optional[SafeDiscoveryAgent] = None,
        ssh_client_factory: Optional[callable] = None,
        doc_fetcher: Optional[DocumentationFetcherProtocol] = None
    ):
        """
        Initialize the discovery agent
        
        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY from .env)
            model: Model to use (defaults to LLM_MODEL from .env)
            safety_agent: Optional safety validator for commands
            ssh_client_factory: Factory function for SSH clients
            doc_fetcher: Documentation fetcher implementation
        """
        # Use provided values or fall back to env vars
        api_key = api_key or os.getenv('GOOGLE_API_KEY')
        model = model or os.getenv('LLM_MODEL', 'gemini-2.5-pro')
        
        if not api_key:
            raise ValueError(
                "Google AI API key not found. Set GOOGLE_API_KEY in .env file or pass api_key parameter."
            )
        
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.3')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '4096')),
            timeout=int(os.getenv('LLM_TIMEOUT', '120')),
            max_retries=2
        )
        self.safety_agent = safety_agent or SafeDiscoveryAgent()
        self.ssh_client_factory = ssh_client_factory
        self.doc_fetcher = doc_fetcher or DefaultDocumentationFetcher()
    
    def _intelligent_truncate_swagger(self, swagger_doc: Dict[str, Any], max_chars: int = 12000) -> str:
        """Smart truncation that preserves JSON structure"""
        essential = {
            "openapi": swagger_doc.get("openapi"),
            "info": swagger_doc.get("info"),
            "servers": swagger_doc.get("servers", [])[:1],
            "security": swagger_doc.get("security"),
            "paths": {}
        }
        
        paths = swagger_doc.get("paths", {})
        current_size = len(json.dumps(essential))
        
        for path, methods in paths.items():
            path_json = json.dumps({path: methods})
            if current_size + len(path_json) > max_chars:
                break
            essential["paths"][path] = methods
            current_size += len(path_json)
        
        if "components" in swagger_doc:
            essential["components"] = {
                "securitySchemes": swagger_doc["components"].get("securitySchemes", {})
            }
        
        return json.dumps(essential, indent=2)
    
    async def discover_from_swagger(
        self,
        swagger_doc: Dict[str, Any],
        service_name: str,
        use_planner: bool = True,
        base_url: Optional[str] = None
    ) -> List[RemediationAction]:
        """
        Discover remediation actions from an OpenAPI/Swagger specification
        
        Uses planner-subagent architecture:
        1. Planner identifies remediation endpoint candidates
        2. Subagents process each endpoint in parallel
        
        Args:
            swagger_doc: The OpenAPI/Swagger JSON document
            service_name: Name of the service these actions belong to
            use_planner: Use planner-subagent architecture (recommended)
            
        Returns:
            List of validated RemediationAction instances
        """
        if not swagger_doc or not service_name or not service_name.strip():
            return []
        
        if use_planner:
            return await self._discover_with_planner(swagger_doc, service_name, base_url)
        
        # Fallback to monolithic approach
        return await self._discover_monolithic(swagger_doc, service_name, base_url)
    
    async def _discover_with_planner(
        self,
        swagger_doc: Dict[str, Any],
        service_name: str,
        base_url: Optional[str] = None
    ) -> List[RemediationAction]:
        """
        Planner-subagent architecture for Swagger discovery
        
        Step 1: Planner identifies remediation endpoints
        Step 2: Subagents process each endpoint in parallel
        """
        # Step 1: Planner identifies candidates
        candidates = await self._plan_remediation_endpoints(swagger_doc, service_name)
        
        if not candidates:
            return []
        
        # Step 2: Process each endpoint with specialist subagent in parallel
        tasks = []
        for candidate in candidates:
            # Get the operation spec
            path_spec = swagger_doc.get('paths', {}).get(candidate.path, {})
            operation_spec = path_spec.get(candidate.method.lower(), {})
            
            if operation_spec:
                task = self._process_single_endpoint(
                    path=candidate.path,
                    method=candidate.method,
                    operation_spec=operation_spec,
                    service_name=service_name,
                    swagger_context=self._extract_swagger_context(swagger_doc),
                    base_url=base_url
                )
                tasks.append(task)
        
        # Execute all subagents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failures and return actions
        actions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed to process {candidates[i].path}: {result}")
            elif result:
                actions.append(result)
        
        return actions
    
    async def _plan_remediation_endpoints(
        self,
        swagger_doc: Dict[str, Any],
        service_name: str
    ) -> List[EndpointCandidate]:
        """
        Planner: Identify remediation endpoint candidates from Swagger spec
        
        Uses LLM with structured output to identify which endpoints are remediation
        """
        # Create overview of all endpoints
        endpoints_summary = []
        for path, methods in swagger_doc.get('paths', {}).items():
            for method, spec in methods.items():
                endpoints_summary.append({
                    'path': path,
                    'method': method.upper(),
                    'operation_id': spec.get('operationId', ''),
                    'summary': spec.get('summary', ''),
                    'description': spec.get('description', ''),
                    'tags': spec.get('tags', [])
                })
        
        if not endpoints_summary:
            return []
        
        # Truncate if too many endpoints
        if len(endpoints_summary) > 50:
            endpoints_summary = endpoints_summary[:50]
        
        system_prompt = textwrap.dedent(f"""
            You are a planning agent that identifies remediation endpoints from an API specification.
            
            ## Your ONLY Task
            Analyze the list of endpoints and identify which ones are for operational remediation.
            
            ## Remediation Endpoints (INCLUDE)
            - Restart, reset, clear, flush, refresh, rebuild, recreate
            - Scale, heal, rollback, failover, recovery
            - Health checks, diagnostics, troubleshooting
            - Cache/queue management (clear, purge, flush)
            - Admin operations (restart, reset)
            - Pool management (reset, clear)
            
            ## Business Endpoints (EXCLUDE)
            - User CRUD (create, update, delete users)
            - Order CRUD (create, list, update orders)
            - Payment processing (charge, refund)
            - Authentication (login, logout, register)
            - Regular business queries (list, search, filter)
            
            ## Output Format
            For each remediation endpoint, return:
            - path: The endpoint path
            - method: HTTP method
            - operation_id: Operation ID from spec
            - is_remediation: Always true
            - reason: Brief reason (e.g., "Restart operation", "Cache management")
            
            ## Service Context
            Service: {service_name}
            Total endpoints: {len(endpoints_summary)}
        """)
        
        user_prompt = textwrap.dedent(f"""
            Identify remediation endpoints from this list:
            
            {json.dumps(endpoints_summary, indent=2)}
            
            Return ONLY endpoints that are for operational remediation/recovery.
        """)
        
        # Use structured output to guarantee format
        structured_llm = self.llm.with_structured_output(EndpointCandidates)
        
        try:
            result = await asyncio.wait_for(
                structured_llm.ainvoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]),
                timeout=60
            )
            return result.candidates if result else []
        except Exception as e:
            print(f"Planner failed: {e}")
            return []
    
    async def _process_single_endpoint(
        self,
        path: str,
        method: str,
        operation_spec: Dict[str, Any],
        service_name: str,
        swagger_context: Dict[str, Any],
        base_url: Optional[str] = None
    ) -> Optional[RemediationAction]:
        """
        Subagent: Process a single endpoint with full context
        
        This agent focuses ONLY on one endpoint, ensuring complete extraction
        """
        operation_id = operation_spec.get('operationId', f"{method.lower()}_{path.replace('/', '_')}")
        summary = operation_spec.get('summary', '')
        description = operation_spec.get('description', '')
        
        # Extract parameters deterministically
        parameters = self._extract_parameters(operation_spec, swagger_context)
        
        # Identify secrets deterministically
        secrets = self._identify_secrets(parameters, operation_spec)
        
        # Build execution dict (guaranteed)
        execution = {
            'endpoint': path,
            'http_method': method.upper(),
            'content_type': 'application/json',
            'timeout_seconds': 30
        }
        
        # Add base_url if provided
        if base_url:
            execution['base_url'] = base_url
        
        # Build action_metadata
        action_metadata = {
            'operationId': operation_id,
            'summary': summary,
            'description': description,
            'tags': operation_spec.get('tags', []),
            'security': [list(s.keys())[0] for s in operation_spec.get('security', [])] if operation_spec.get('security') else []
        }
        
               
        # Store full security scheme definitions for execution engine
        if operation_spec.get('security') and swagger_context.get('components', {}).get('securitySchemes'):
            components_security = swagger_context['components']['securitySchemes']
            action_metadata['security_schemes'] = {}
            
            for sec_req in operation_spec.get('security', []):
                for scheme_name in sec_req.keys():
                    if scheme_name in components_security:
                        action_metadata['security_schemes'][scheme_name] = \
                            components_security[scheme_name]

        # Use LLM ONLY for: action_id, definition, risk_level, requires_approval
        system_prompt = textwrap.dedent(f"""
            You are a specialist agent processing ONE API endpoint for remediation.
            
            ## Context
            Service: {service_name}
            Endpoint: {method} {path}
            Summary: {summary}
            Description: {description}
            
            ## Your Task
            Generate a SINGLE RemediationAction with:
            
            1. **action_id**: Descriptive ID (format: operation-resource-service)
               Example: "restart-payment-service", "clear-redis-cache"
            
            2. **definition**: Complete sentence with WHAT, WHEN, IMPACT
               Example: "Restart payment service | WHEN: High error rate >5% | IMPACT: 10-30s downtime"
            
            3. **risk_level**: "low", "medium", or "high"
               - low: Read-only, health checks
               - medium: Restarts, cache clears
               - high: Destructive, data deletion
            
            4. **requires_approval**: true for medium/high risk, false for low
            
            ## Pre-filled Fields (DO NOT CHANGE)
            - method: "rpc"
            - service: "{service_name}"
            - validated: false
            - execution: {execution}
            - parameters: {json.dumps(parameters)}
            - secrets: {secrets}
            - action_metadata: {json.dumps(action_metadata)}
        """)
        
        user_prompt = textwrap.dedent(f"""
            Generate a complete RemediationAction for this endpoint.
            
            Endpoint: {method} {path}
            Operation: {operation_id}
            Summary: {summary}
            Description: {description}
            
            Use the pre-filled execution, parameters, secrets, and action_metadata.
            Focus on generating accurate action_id, definition, risk_level, and requires_approval.
        """)
        
        # Use structured output for single action
        structured_llm = self.llm.with_structured_output(RemediationAction)
        
        try:
            action = await asyncio.wait_for(
                structured_llm.ainvoke([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]),
                timeout=30
            )
            
            if action:
                # Guarantee execution, parameters, secrets, action_metadata
                action.method = 'rpc'
                action.service = service_name
                action.validated = False
                action.execution = execution
                action.parameters = parameters
                # Convert secrets list to dict with secret_references for execution engine
                # OpenAPI secrets are never auto-stored, so stored=False for all
                if secrets:
                    action.secrets = {
                        'secret_references': [
                            {
                                'name': f"{service_name}_{secret}",
                                'path': f"{service_name}_{secret}",
                                'stored': False  # OpenAPI secrets need user provisioning
                            }
                            for secret in secrets
                        ]
                    }
                else:
                    action.secrets = {'secret_references': []}
                action.action_metadata = action_metadata
                
                return action
        except Exception as e:
            print(f"Subagent failed for {path}: {e}")
        
        return None
    
    def _extract_swagger_context(self, swagger_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract general context about the API service"""
        return {
            'title': swagger_doc.get('info', {}).get('title', ''),
            'version': swagger_doc.get('info', {}).get('version', ''),
            'description': swagger_doc.get('info', {}).get('description', ''),
            'servers': swagger_doc.get('servers', []),
            'security': swagger_doc.get('security', []),
            'components': swagger_doc.get('components', {})
        }
    
    def _resolve_schema_ref(self, ref: str, swagger_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve a $ref to its schema definition
        
        Example: '#/components/schemas/ServiceActionRequest' -> actual schema
        """
        if not ref or not ref.startswith('#/'):
            return {}
        
        # Parse the reference path
        path_parts = ref[2:].split('/')  # Remove '#/' and split: ['components', 'schemas', 'ServiceActionRequest']
        
        # Start from swagger_context (which contains the 'components' key)
        schema = swagger_context
        for part in path_parts:
            if isinstance(schema, dict):
                schema = schema.get(part, {})
            else:
                return {}
        
        return schema if isinstance(schema, dict) else {}
    
    def _identify_secrets(
        self,
        parameters: Dict[str, Dict[str, Any]],
        operation_spec: Dict[str, Any]
    ) -> List[str]:
        """Identify secret parameters using pattern matching"""
        secret_keywords = [
            'password', 'passwd', 'pwd', 'token', 'bearer', 'secret', 
            'credential', 'api_key', 'apikey', 'api-key', 'private_key',
            'auth_token', 'access_token', 'refresh_token', 'client_secret',
            'certificate', 'cert', 'authorization'
        ]
        
        secrets = []
        for param_name, param_spec in parameters.items():
            param_lower = param_name.lower()
            desc_lower = param_spec.get('description', '').lower()
            
            # Check parameter name
            if any(keyword in param_lower for keyword in secret_keywords):
                secrets.append(param_name)
                continue
            
            # Check description
            if any(keyword in desc_lower for keyword in ['sensitive', 'confidential', 'secret', 'credential']):
                secrets.append(param_name)
               # Check security requirements (API keys, bearer tokens, etc.)
        security_schemes = operation_spec.get('security', [])
        if security_schemes:
            for scheme in security_schemes:
                for scheme_name in scheme.keys():
                    # Add the security scheme name as a secret requirement
                    # e.g., "ApiKeyAuth" -> "api_key_auth"
                    secret_name = scheme_name.lower().replace('-', '_')
                    if secret_name not in secrets:
                        secrets.append(secret_name)
        return secrets
    
    async def _discover_monolithic(
        self,
        swagger_doc: Dict[str, Any],
        service_name: str,
        base_url: Optional[str] = None
    ) -> List[RemediationAction]:
        """
        Original monolithic approach (fallback)
        """
        system_prompt = textwrap.dedent(f"""
            You are an expert at analyzing OpenAPI/Swagger specifications for operational remediation.
            
            ## Your Task
            Extract API endpoints that can be used for automated recovery and system healing.
            
            ## Focus On (Remediation Actions)
            - Restart, reset, clear, flush, refresh, rebuild, recreate endpoints
            - Scale, heal, rollback, failover operations
            - Health check and diagnostics endpoints
            - Cache management, queue management
            
            ## Ignore (Business Logic)
            - Regular CRUD for business data (GET /users, POST /orders)
            - Authentication/authorization endpoints
            
            ## Self-Validation Checklist
            Before returning each action, verify:
            [ ] action_id is descriptive (not generic like "action1")
            [ ] definition explains WHAT, WHEN to use, IMPACT
            [ ] execution contains endpoint, http_method, content_type
            [ ] parameters extracted from spec (not empty {{}})
            [ ] secrets identified (api_key, password, token, etc.)
            [ ] risk_level matches operation (high/medium/low)
            [ ] requires_approval = true for medium/high risk
            [ ] action_metadata has operationId, tags
            
            ## Field Requirements
            
            **action_id**: Format: {{operation}}-{{resource}}-{{service}}
              Example: "restart-payment-service", "clear-redis-cache"
            
            **method**: Always "rpc" for API endpoints
            
            **service**: "{service_name}"
            
            **definition**: Must include:
              - WHAT: What this action does
              - WHEN: When to use it (error conditions, symptoms)
              - IMPACT: Side effects, downtime, affected systems
              Example: "Restart payment service | WHEN: High error rate or memory leak | IMPACT: 10-30s downtime"
            
            **requires_approval**: 
              - true: For destructive ops (delete, terminate, restart production)
              - false: For read-only diagnostics
            
            **risk_level**:
              - "high": Deletes data, terminates processes, affects production
              - "medium": Restarts services, clears caches
              - "low": Read-only diagnostics, health checks
            
            **execution**: MUST contain {{endpoint, http_method, content_type}}
              Example: {{"endpoint": "/admin/restart", "http_method": "POST", "content_type": "application/json"}}
            
            **parameters**: Extract ALL from spec with {{type, required, default, description}}
              Example: {{"timeout": {{"type": "integer", "required": false, "default": 30, "description": "Seconds"}}}}
            
            **secrets**: Identify sensitive parameter names
              Example: ["api_key", "admin_token", "db_password"]
            
            **action_metadata**: Include {{operationId, tags, security, estimated_runtime_seconds}}
              Example: {{"operationId": "restart", "tags": ["admin"], "estimated_runtime_seconds": 30}}
            
            ## Example of EXCELLENT Output
            {{
              "action_id": "restart-payment-worker",
              "method": "rpc",
              "service": "{service_name}",
              "definition": "Restart payment worker process | WHEN: Tasks stuck or memory >80% | IMPACT: Brief task delay",
              "requires_approval": true,
              "risk_level": "medium",
              "validated": false,
              "execution": {{"endpoint": "/admin/restart", "http_method": "POST", "content_type": "application/json"}},
              "parameters": {{"graceful": {{"type": "boolean", "required": false, "default": true, "description": "Graceful shutdown"}}}},
              "secrets": ["api_key"],
              "action_metadata": {{"operationId": "restartWorker", "tags": ["admin"], "estimated_runtime_seconds": 30}}
            }}
            
            ## Example of BAD Output (DON'T DO THIS)
            {{
              "action_id": "action1",  #Too generic
              "definition": "Restarts service",  # No WHEN/IMPACT context
              "execution": {{}},  # Empty!
              "parameters": {{}},  # Not extracted
              "action_metadata": {{}}  # Empty
            }}
        """)
        
        user_prompt = textwrap.dedent(f"""
            Analyze this OpenAPI specification and extract remediation endpoints.
            
            Service: {service_name}
            
            Specification:
            {self._intelligent_truncate_swagger(swagger_doc, 12000)}
            
            Generate COMPLETE RemediationAction instances.
            Follow the self-validation checklist before returning each action.
        """)
        
        result = await self._invoke_structured(system_prompt, user_prompt)
        
        # Post-process: ensure execution, parameters, action_metadata are populated
        # Parse Swagger spec directly to guarantee these fields
        actions = result.actions
        for action in actions:
            # Find matching path in swagger_doc by checking multiple strategies
            matched_path = None
            matched_method = None
            matched_spec = None
            
            # Strategy 1: Match by operationId
            operation_id = action.action_metadata.get('operationId') if action.action_metadata else None
            
            # Strategy 2: Match by path substring in action_id
            # Strategy 3: Match by summary/description
            for path, methods in swagger_doc.get('paths', {}).items():
                for http_method, spec in methods.items():
                    # Match by operationId
                    if operation_id and spec.get('operationId') == operation_id:
                        matched_path = path
                        matched_method = http_method
                        matched_spec = spec
                        break
                    
                    # Match by path in action_id (e.g., "/admin/restart" matches "restart-service")
                    path_parts = path.strip('/').split('/')
                    action_parts = action.action_id.lower().split('-')
                    if any(part in action_parts for part in path_parts):
                        matched_path = path
                        matched_method = http_method
                        matched_spec = spec
                        break
                
                if matched_spec:
                    break
            
            # If we found a match, populate missing fields
            if matched_spec:
                # Populate execution if empty
                if not action.execution or action.execution == {}:
                    action.execution = {
                        'endpoint': matched_path,
                        'http_method': matched_method.upper(),
                        'content_type': 'application/json',
                        'timeout_seconds': 30
                    }
                
                # Populate parameters if empty
                if not action.parameters or action.parameters == {}:
                    action.parameters = self._extract_parameters(matched_spec)
                
                # Populate action_metadata if empty
                if not action.action_metadata or action.action_metadata == {}:
                    action.action_metadata = {
                        'operationId': matched_spec.get('operationId', ''),
                        'summary': matched_spec.get('summary', ''),
                        'tags': matched_spec.get('tags', []),
                        'security': [list(s.keys())[0] for s in matched_spec.get('security', [])] if matched_spec.get('security') else [],
                        'estimated_runtime_seconds': 30
                    }
                        
                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Processing action {action.action_id}, matched_spec security: {matched_spec.get('security')}")
                
                # Store full security scheme definitions for execution engine
                # Always add this regardless of whether action_metadata was empty
                if matched_spec.get('security'):
                    components_security = swagger_doc.get('components', {}).get('securitySchemes', {})
                    if not action.action_metadata:
                        action.action_metadata = {}
                    action.action_metadata['security_schemes'] = {}
                    
                    logger.info(f"Matched spec has security: {matched_spec.get('security')}")
                    logger.info(f"Components security: {list(components_security.keys())}")
                    
                    for sec_req in matched_spec.get('security', []):
                        for scheme_name in sec_req.keys():
                            if scheme_name in components_security:
                                action.action_metadata['security_schemes'][scheme_name] = \
                                    components_security[scheme_name]
                                logger.info(f"Added security scheme {scheme_name}: {components_security[scheme_name]}")
        return actions
    
    async def discover_from_scripts(
        self,
        script_listings: List[Dict[str, str]],
        service_name: str
    ) -> List[RemediationAction]:
        """
        Discover remediation actions from script files
        
        Args:
            script_listings: List of {"path": str, "content": str} dicts
            service_name: Service these scripts belong to
            
        Returns:
            List of validated RemediationAction instances
        """
        if not script_listings or not service_name or not service_name.strip():
            return []
        scripts_text = "\n\n".join([
            f"Script: {s['path']}\n```\n{s['content'][:2000]}\n```"
            for s in script_listings[:10]  # Limit to avoid token overflow
        ])
        
        system_prompt = textwrap.dedent(f"""
            You analyze operational scripts and generate RemediationAction definitions.
            
            **CRITICAL: execution field is REQUIRED and must contain:**
            - script_path: Full path to the script
            - command: Full command with interpreter (e.g., "bash /path/script.sh")
            - timeout_seconds: Estimated timeout (default 300)
            
            **CRITICAL: parameters field must extract ALL script arguments:**
            - Parse $1, $2, ${{VAR}} from script
            - Include type, required, default, description
            - Example: {{"service_name": {{"type": "string", "required": true, "description": "Service to restart"}}}}
            
            **For each script, generate:**
            - action_id: Unique ID from script name (e.g., "restart-service", "clear-cache")
            - method: "script"
            - service: "{service_name}"
            - definition: What script does + WHEN to use + IMPACT
            - requires_approval: true for destructive ops (restart, delete), false for diagnostics
            - risk_level: "high" for production changes, "medium" for service restarts, "low" for queries
            - validated: false
            - execution: {{"script_path": "/full/path/script.sh", "command": "bash /full/path/script.sh", "timeout_seconds": 300}}
            - parameters: Extract ALL from script args with full details
            - secrets: Identify sensitive params (passwords, API keys, tokens)
            - action_metadata: {{"interpreter": "bash", "estimated_runtime": 30, "requires_ssh": true}}
        """)
        
        user_prompt = textwrap.dedent(f"""
            Analyze these operational scripts and generate RemediationAction instances.
            
            Scripts:
            {scripts_text}
        """)
        
        result = await self._invoke_structured(system_prompt, user_prompt)
        
        # Post-process: ensure execution details are populated
        for i, action in enumerate(result.actions):
            script_info = script_listings[i] if i < len(script_listings) else None
            if script_info:
                # Ensure execution has script_path and command
                if not action.execution or not action.execution.get('script_path'):
                    action.execution = action.execution or {}
                    action.execution['script_path'] = script_info['path']
                    action.execution['command'] = f"bash {script_info['path']}"
                    action.execution['timeout_seconds'] = 300
                
                # Extract parameters from script content if empty
                if not action.parameters or action.parameters == {}:
                    action.parameters = self._extract_script_parameters(script_info['content'])
        
        return result.actions
    
    async def discover_from_ssh(
        self,
        host: str,
        scripts_path: str,
        credentials: Dict[str, Any],
        service_name: str,
        secrets_manager = None
    ) -> List[RemediationAction]:
        """
        Discover scripts via SSH and analyze them
        
        Args:
            host: SSH host to connect to
            scripts_path: Directory path containing scripts
            credentials: SSH credentials dict
            service_name: Service name
            secrets_manager: Optional SecretsManager instance to store credentials
            
        Returns:
            List of RemediationAction instances
        """
        if not self.ssh_client_factory:
            raise RuntimeError("SSH client factory not configured")
        
        # Validate list command for safety
        list_cmd = f"find {scripts_path} -type f -executable"
        validation = self.safety_agent.validate_command(list_cmd)
        if not validation.safe:
            raise SecurityError(f"Unsafe discovery command: {validation.reason}")
        
        # Connect and list scripts
        ssh_client = self.ssh_client_factory(host, credentials)
        script_paths = await ssh_client.list_scripts(scripts_path)
        
        # Read and analyze each script
        script_listings = []
        logger.info(f"SSH Discovery: Found {len(script_paths)} scripts in {scripts_path}")
        for path in script_paths[:20]:  # Limit to first 20 scripts
            # Validate read operation
            read_cmd = f"cat {path}"
            validation = self.safety_agent.validate_command(read_cmd)
            if not validation.safe:
                logger.warning(f"SSH Discovery: Skipping {path} - failed safety validation: {validation.reason}")
                continue
            
            try:
                content = await ssh_client.read_file(path)
                logger.info(f"SSH Discovery: Read {len(content)} bytes from {path}")
                script_listings.append({"path": path, "content": content})
            except Exception as e:
                logger.error(f"SSH Discovery: Failed to read {path}: {e}")
                continue  # Skip files we can't read
        
        if not script_listings:
            logger.warning(f"SSH Discovery: No readable scripts found in {scripts_path}")
            return []
        
        logger.info(f"SSH Discovery: Analyzing {len(script_listings)} scripts with LLM")
        # Analyze with LLM and pass SSH connection info
        actions = await self.discover_from_scripts(script_listings, service_name)
        
        # Generate unique secret keys based on host and service
        # This ensures credentials for different hosts/services don't conflict
        secret_prefix = f"{service_name}_{host.replace('.', '_')}"
        ssh_host_key = f"{secret_prefix}_ssh_host"
        ssh_username_key = f"{secret_prefix}_ssh_username"
        ssh_password_key = f"{secret_prefix}_ssh_password"
        ssh_port_key = f"{secret_prefix}_ssh_port"
        
        # Store SSH credentials in secrets manager if provided
        if secrets_manager:
            try:
                secrets_manager.set_secret(ssh_host_key, host)
                secrets_manager.set_secret(ssh_username_key, credentials.get('username', 'root'))
                if credentials.get('password'):
                    secrets_manager.set_secret(ssh_password_key, credentials.get('password'))
                secrets_manager.set_secret(ssh_port_key, str(credentials.get('port', 22)))
                logger.info(f"SSH Discovery: Stored credentials in secrets manager with prefix '{secret_prefix}'")
            except Exception as e:
                logger.warning(f"SSH Discovery: Failed to store credentials in secrets manager: {e}")
        
                # Generate unique secret keys based on host and service
        # This ensures credentials for different hosts/services don't conflict
        secret_prefix = f"{service_name}_{host.replace('.', '_')}"
        ssh_host_key = f"{secret_prefix}_ssh_host"
        ssh_username_key = f"{secret_prefix}_ssh_username"
        ssh_password_key = f"{secret_prefix}_ssh_password"
        ssh_port_key = f"{secret_prefix}_ssh_port"
        
        # Store SSH credentials in secrets manager if provided
        if secrets_manager:
            try:
                logger.info(f"SSH Discovery: Attempting to store credentials with secrets_manager={secrets_manager}")
                secrets_manager.set_secret(ssh_host_key, host)
                secrets_manager.set_secret(ssh_username_key, credentials.get('username', 'root'))
                if credentials.get('password'):
                    secrets_manager.set_secret(ssh_password_key, credentials.get('password'))
                secrets_manager.set_secret(ssh_port_key, str(credentials.get('port', 22)))
                logger.info(f"SSH Discovery: Stored credentials in secrets manager with prefix '{secret_prefix}'")
            except Exception as e:
                logger.warning(f"SSH Discovery: Failed to store credentials in secrets manager: {e}")
        else:
            logger.warning(f"SSH Discovery: secrets_manager is None, cannot auto-store credentials")
        
        # Add SSH credential secret references to each action
        ssh_credentials_stored = secrets_manager is not None
        
        for action in actions:
            secret_references = [
            {'name': ssh_host_key, 'path': ssh_host_key, 'stored': ssh_credentials_stored},
            {'name': ssh_username_key, 'path': ssh_username_key, 'stored': ssh_credentials_stored},
            {'name': ssh_password_key, 'path': ssh_password_key, 'stored': ssh_credentials_stored},
            {'name': ssh_port_key, 'path': ssh_port_key, 'stored': ssh_credentials_stored}
            ]
            if isinstance(action.secrets, list) and action.secrets:
                for secret_name in action.secrets:
                    secret_references.append({
                        'name': f"{service_name}_{secret_name}",
                        'path': f"{service_name}_{secret_name}",
                        'stored': False  # Application secrets need user provisioning
                    })
            
            # Set secrets as dict with secret_references array for execution engine
            action.secrets = {'secret_references': secret_references}
            if not action.action_metadata:
                action.action_metadata = {}
            action.action_metadata['ssh_secret_mapping'] = {
                'ssh_host': ssh_host_key,
                'ssh_username': ssh_username_key,
                'ssh_password': ssh_password_key,
                'ssh_port': ssh_port_key
            }
        
        return actions
    
    async def discover_from_documentation(
        self,
        documentation: str,
        service_name: str
    ) -> List[RemediationAction]:
        """
        Discover remediation actions from operational documentation
        
        Args:
            documentation: Operational runbook or documentation text
            service_name: Service these actions belong to
            
        Returns:
            List of validated RemediationAction instances
        """
        if not documentation or not documentation.strip() or not service_name or not service_name.strip():
            return []
        system_prompt = textwrap.dedent(f"""
            You convert operational runbooks into structured RemediationAction definitions.
            
            **CRITICAL: execution field is REQUIRED based on method:**
            
            For method="command":
            {{"command": "systemctl restart service", "timeout_seconds": 30}}
            
            For method="k8s":
            {{"command": "kubectl rollout restart deployment/name", "namespace": "default", "timeout_seconds": 60}}
            
            For method="api":
            {{"endpoint": "/admin/restart", "http_method": "POST", "content_type": "application/json"}}
            
            For method="script":
            {{"script_path": "/path/to/script.sh", "command": "bash /path/to/script.sh", "timeout_seconds": 300}}
            
            **CRITICAL: parameters must include ALL variables mentioned:**
            - Extract from HOW section (curl parameters, script args, kubectl flags)
            - Include type, required, default, description
            - Example: {{"force": {{"type": "boolean", "required": false, "default": false, "description": "Force restart"}}}}
            
            **For each action, generate:**
            - action_id: Descriptive unique ID (e.g., "restart-payment-service", "clear-redis-cache")
            - method: "command", "k8s", "api", or "script" (based on HOW section)
            - service: "{service_name}"
            - definition: WHAT it does + WHEN to use + IMPACT on system
            - requires_approval: true if documentation mentions "approval" or high risk
            - risk_level: "high"/"medium"/"low" based on RISK section
            - validated: false
            - execution: COMPLETE execution details (see format above)
            - parameters: Extract ALL parameters with full details
            - secrets: Identify sensitive params from SECRETS section
            - action_metadata: {{"source": "runbook", "section": "Emergency Procedures"}}
        """)
        
        user_prompt = textwrap.dedent(f"""
            Analyze this operational documentation and extract remediation actions.
            
            Documentation:
            {documentation[:15000]}
        """)
        
        result = await self._invoke_structured(system_prompt, user_prompt)
        
        # Post-process: ensure execution details are populated by parsing documentation
        import re
        for action in result.actions:
            # If execution is empty, try to extract from documentation
            if not action.execution or action.execution == {}:
                # Find HOW section related to this action
                action_context = self._find_action_context(documentation, action.action_id)
                
                if action.method == "api":
                    # Extract API endpoint from HOW section
                    endpoint_match = re.search(r'(POST|GET|PUT|DELETE|PATCH)\s+([/\w\-]+)', action_context, re.IGNORECASE)
                    if endpoint_match:
                        action.execution = {
                            'endpoint': endpoint_match.group(2),
                            'http_method': endpoint_match.group(1).upper(),
                            'content_type': 'application/json',
                            'timeout_seconds': 30
                        }
                
                elif action.method == "command":
                    # Extract command from HOW section
                    command_match = re.search(r'(?:HOW:|Run|Execute)[:\s]+([\w\s\-/\.]+(?:restart|start|stop|kill|systemctl)[\w\s\-/\.]*)', action_context, re.IGNORECASE)
                    if command_match:
                        action.execution = {
                            'command': command_match.group(1).strip(),
                            'timeout_seconds': 30
                        }
                
                elif action.method == "script":
                    # Extract script path from HOW section
                    script_match = re.search(r'(?:Run|Execute)[:\s]+([\w\-/\.]+\.sh)', action_context, re.IGNORECASE)
                    if script_match:
                        script_path = script_match.group(1).strip()
                        action.execution = {
                            'script_path': script_path,
                            'command': f"bash {script_path}",
                            'timeout_seconds': 300
                        }
                
                elif action.method == "k8s":
                    # Extract kubectl command
                    k8s_match = re.search(r'(kubectl[\w\s\-/\.]+)', action_context, re.IGNORECASE)
                    if k8s_match:
                        action.execution = {
                            'command': k8s_match.group(1).strip(),
                            'namespace': 'default',
                            'timeout_seconds': 60
                        }
            
            # Extract parameters from HOW section if empty
            if not action.parameters or action.parameters == {}:
                action_context = self._find_action_context(documentation, action.action_id)
                action.parameters = self._extract_doc_parameters(action_context)
        
        return result.actions
    
    async def discover_from_documentation_sources(
        self,
        sources: List[Dict[str, Any]],
        service_name: str
    ) -> List[RemediationAction]:
        """
        Fetch and discover from multiple documentation sources
        
        Args:
            sources: List of source dicts (type, url/content, etc.)
            service_name: Service name
            
        Returns:
            List of RemediationAction instances
        """
        documents = []
        for source in sources:
            try:
                fetched = await self.doc_fetcher.fetch(source)
                documents.extend(fetched)
            except Exception:
                continue  # Skip sources that fail to fetch
        
        if not documents:
            return []
        
        combined_docs = "\n\n".join(documents)
        return await self.discover_from_documentation(combined_docs, service_name)
    
    def _extract_parameters(self, operation_spec: Dict[str, Any], swagger_context: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameters from OpenAPI operation spec
        
        Returns dict: {param_name: {type, required, default, description}}
        """
        params = {}
        
        # Extract query/path/header parameters
        for param in operation_spec.get('parameters', []):
            param_name = param.get('name')
            param_schema = param.get('schema', {})
            
            params[param_name] = {
                'type': param_schema.get('type', 'string'),
                'required': param.get('required', False),
                'default': param_schema.get('default'),
                'description': param.get('description', '')
            }
        
        # Extract requestBody parameters
        request_body = operation_spec.get('requestBody', {})
        if request_body:
            content = request_body.get('content', {})
            json_content = content.get('application/json', {})
            schema = json_content.get('schema', {})
            
            # Resolve $ref if present
            if '$ref' in schema and swagger_context:
                schema = self._resolve_schema_ref(schema.get('$ref'), swagger_context)
            
            properties = schema.get('properties', {})
            required_fields = schema.get('required', [])
            
            for prop_name, prop_schema in properties.items():
                params[prop_name] = {
                    'type': prop_schema.get('type', 'string'),
                    'required': prop_name in required_fields,
                    'default': prop_schema.get('default'),
                    'description': prop_schema.get('description', '')
                }
        
        return params
    
    def _extract_script_parameters(self, script_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameters from script content
        
        Looks for:
        - Positional args: $1, $2, etc.
        - Named vars: ${VAR_NAME}
        - Environment vars: ${ENV_VAR:-default}
        
        Returns dict: {param_name: {type, required, default, description}}
        """
        import re
        params = {}
        
        # Find positional arguments ($1, $2, etc.)
        positional_pattern = r'\$(\d+)'
        positionals = set(re.findall(positional_pattern, script_content))
        for pos in positionals:
            param_name = f"arg{pos}"
            # Try to infer meaning from nearby comments
            context_pattern = rf'#.*\n.*\${pos}'
            context_match = re.search(context_pattern, script_content)
            description = ""
            if context_match:
                comment = context_match.group(0).split('\n')[0].strip('# ')
                description = comment
            
            params[param_name] = {
                'type': 'string',
                'required': True,
                'default': None,
                'description': description or f'Positional argument {pos}'
            }
        
        # Find environment variables with defaults
        env_pattern = r'\$\{([A-Z_]+)(?::[-=]([^\}]+))?\}'
        env_vars = re.findall(env_pattern, script_content)
        for var_name, default_value in env_vars:
            if var_name not in params:
                params[var_name.lower()] = {
                    'type': 'string',
                    'required': not bool(default_value),
                    'default': default_value if default_value else None,
                    'description': f'Environment variable {var_name}'
                }
        
        return params
    
    def _find_action_context(self, documentation: str, action_id: str) -> str:
        """
        Find the section of documentation related to this action
        
        Looks for sections containing keywords from action_id
        """
        import re
        
        # Extract keywords from action_id (e.g., "restart-payment-service" -> ["restart", "payment", "service"])
        keywords = action_id.lower().replace('-', ' ').replace('_', ' ').split()
        
        # Split documentation into sections (by headers ## or ###)
        sections = re.split(r'\n#{2,3}\s+', documentation)
        
        best_section = ""
        max_matches = 0
        
        for section in sections:
            # Count keyword matches in this section
            section_lower = section.lower()
            matches = sum(1 for keyword in keywords if keyword in section_lower)
            
            if matches > max_matches:
                max_matches = matches
                best_section = section
        
        # Return best match or first 1000 chars if no good match
        return best_section if best_section else documentation[:1000]
    
    def _extract_doc_parameters(self, context: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameters from documentation context
        
        Looks for:
        - Query parameters in URLs: ?force=false&timeout=30
        - Script arguments: script.sh <arg1> <arg2>
        - kubectl flags: --replicas=3
        - Command options: -f, --force
        """
        import re
        params = {}
        
        # Find query parameters in URLs (?param=value or ?param)
        query_pattern = r'\?([a-zA-Z_]+)(?:=([\w\-\.]+))?'
        query_params = re.findall(query_pattern, context)
        for param_name, default_value in query_params:
            if param_name not in params:
                params[param_name] = {
                    'type': 'boolean' if default_value.lower() in ['true', 'false'] else 'string' if default_value else 'string',
                    'required': not bool(default_value),
                    'default': default_value.lower() == 'true' if default_value.lower() in ['true', 'false'] else default_value if default_value else None,
                    'description': f'Query parameter {param_name}'
                }
        
        # Find kubectl/command flags (--flag=value or --flag)
        flag_pattern = r'--([a-zA-Z][a-zA-Z0-9-]*)(?:=([^\s\)]+))?'
        flags = re.findall(flag_pattern, context)
        for flag_name, flag_value in flags:
            param_key = flag_name.replace('-', '_')
            if param_key not in params:
                # Infer type from value
                param_type = 'string'
                processed_value = flag_value if flag_value else None
                if flag_value:
                    if flag_value.lower() in ['true', 'false']:
                        param_type = 'boolean'
                        processed_value = flag_value.lower() == 'true'
                    elif flag_value.isdigit():
                        param_type = 'integer'
                        processed_value = int(flag_value)
                
                params[param_key] = {
                    'type': param_type,
                    'required': not bool(flag_value),
                    'default': processed_value,
                    'description': f'Flag {flag_name}'
                }
        
        # Find script arguments in angle brackets: <arg_name>
        arg_pattern = r'<([a-zA-Z_][a-zA-Z0-9_]*)>'
        args = re.findall(arg_pattern, context)
        for arg_name in args:
            if arg_name not in params and arg_name not in ['optional', 'required']:  # Skip common placeholders
                params[arg_name] = {
                    'type': 'string',
                    'required': True,
                    'default': None,
                    'description': f'Argument {arg_name}'
                }
        
        # Find positional script args: $1, $2
        positional_pattern = r'\$(\d+)'
        positionals = set(re.findall(positional_pattern, context))
        for pos in positionals:
            param_name = f'arg{pos}'
            if param_name not in params:
                params[param_name] = {
                    'type': 'string',
                    'required': True,
                    'default': None,
                    'description': f'Positional argument {pos}'
                }
        
        return params
    
    async def _invoke_structured(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> RemediationActions:
        """
        Invoke LLM with structured output validation
        
        Returns validated RemediationActions instance
        """
        structured_llm = self.llm.with_structured_output(RemediationActions)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Retry logic with timeout
        retries = 3
        timeout = 120  # seconds per attempt (increased for complex prompts)
        
        for attempt in range(retries):
            try:
                result = await asyncio.wait_for(
                    structured_llm.ainvoke(full_prompt),
                    timeout=timeout
                )
                if result is None:
                    print(f"WARNING: Attempt {attempt + 1}: LLM returned None, retrying...")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                return result
            except asyncio.TimeoutError:
                print(f"WARNING: Attempt {attempt + 1}: Timeout after {timeout}s")
                if attempt == retries - 1:
                    raise RuntimeError(f"LLM invocation timed out after {retries} attempts ({timeout}s each)")
                await asyncio.sleep(1.5 * (attempt + 1))
            except Exception as exc:
                print(f"WARNING: Attempt {attempt + 1}: Error - {exc}")
                if attempt == retries - 1:
                    raise RuntimeError(f"LLM invocation failed after {retries} attempts: {exc}")
                await asyncio.sleep(1.5 * (attempt + 1))
        
        # If we exhaust retries and only got None results
        raise RuntimeError("LLM consistently returned None - may need to adjust prompt or model parameters")


class RegistryIntegration:
    """Helper to integrate discovered actions with the RunbookRegistry"""
    
    def __init__(self, registry: RunbookRegistry):
        self.registry = registry
    
    async def register_actions(
        self,
        actions: List[RemediationAction],
        validate: bool = False
    ) -> Dict[str, Any]:
        """
        Register discovered actions in the registry
        
        Args:
            actions: List of RemediationAction instances
            validate: Whether to mark actions as validated
            
        Returns:
            Summary dict with counts
        """
        if validate:
            for action in actions:
                action.validated = True
        
        # Bulk save to registry
        await self.registry.bulk_save(actions)
        
        return {
            'registered': len(actions),
            'services': list(set(a.service for a in actions)),
            'methods': list(set(a.method for a in actions)),
            'risk_levels': {
                'high': sum(1 for a in actions if a.risk_level == 'high'),
                'medium': sum(1 for a in actions if a.risk_level == 'medium'),
                'low': sum(1 for a in actions if a.risk_level == 'low')
            }
        }


# =============================================================================
# Example Usage
# =============================================================================

async def example_usage():
    """Example of how to use the discovery agent"""
    
    # Initialize agent (uses env vars automatically)
    agent = LLMDiscoveryAgent()
    
    # Initialize registry (uses DATABASE_URL from env)
    db_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./runbook.db')
    registry = RunbookRegistry(database_url=db_url)
    await registry.initialize()
    
    print(f" Connected to database: {db_url.split(':/')[0]}")
    
    # Discover from Swagger - comprehensive example with multiple endpoints
    swagger_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Payment Service Admin API",
            "version": "1.0.0"
        },
        "paths": {
            "/admin/restart": {
                "post": {
                    "operationId": "restartService",
                    "summary": "Restart the payment processing service",
                    "description": "Performs a graceful restart of the payment service with optional drain period",
                    "parameters": [
                        {
                            "name": "graceful",
                            "in": "query",
                            "schema": {"type": "boolean", "default": True},
                            "description": "Whether to drain connections before restart"
                        },
                        {
                            "name": "drain_timeout",
                            "in": "query",
                            "schema": {"type": "integer", "default": 30},
                            "description": "Seconds to wait for connection drain"
                        }
                    ],
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {"200": {"description": "Service restarted successfully"}}
                }
            },
            "/admin/database/pool/reset": {
                "post": {
                    "operationId": "resetDatabasePool",
                    "summary": "Reset database connection pool",
                    "description": "Clears and reinitializes the database connection pool to fix stale connections",
                    "parameters": [
                        {
                            "name": "force",
                            "in": "query",
                            "schema": {"type": "boolean", "default": False},
                            "description": "Force kill active connections"
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "api_key": {"type": "string", "description": "Admin API key"},
                                        "database_password": {"type": "string", "description": "Database admin password"}
                                    },
                                    "required": ["api_key", "database_password"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Pool reset successfully"}}
                }
            },
            "/admin/cache/clear": {
                "post": {
                    "operationId": "clearCache",
                    "summary": "Clear Redis cache",
                    "description": "Flushes all cached data from Redis",
                    "parameters": [
                        {
                            "name": "pattern",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Key pattern to clear (e.g., 'user:*')"
                        }
                    ],
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {"200": {"description": "Cache cleared"}}
                }
            },
            "/admin/queue/purge": {
                "delete": {
                    "operationId": "purgeQueue",
                    "summary": "Purge dead letter queue",
                    "description": "Removes all messages from the dead letter queue - DESTRUCTIVE",
                    "parameters": [
                        {
                            "name": "queue_name",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Name of the queue to purge"
                        },
                        {
                            "name": "confirmation_token",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Confirmation token for destructive operation"
                        }
                    ],
                    "responses": {"200": {"description": "Queue purged"}}
                }
            },
            "/admin/scale": {
                "post": {
                    "operationId": "scaleService",
                    "summary": "Scale service replicas",
                    "description": "Adjusts the number of running service instances",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "replicas": {"type": "integer", "minimum": 1, "maximum": 10},
                                        "service_token": {"type": "string", "description": "Service authentication token"}
                                    },
                                    "required": ["replicas", "service_token"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Scaling initiated"}}
                }
            },
            "/admin/rollback": {
                "post": {
                    "operationId": "rollbackDeployment",
                    "summary": "Rollback to previous version",
                    "description": "Rolls back the service to the last stable deployment - HIGH RISK",
                    "parameters": [
                        {
                            "name": "version",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Specific version to rollback to (optional)"
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "admin_token": {"type": "string", "description": "Admin authorization token"},
                                        "approval_code": {"type": "string", "description": "Manager approval code"}
                                    },
                                    "required": ["admin_token", "approval_code"]
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "Rollback completed"}}
                }
            },
            "/health": {
                "get": {
                    "operationId": "healthCheck",
                    "summary": "Health check endpoint",
                    "description": "Returns service health status - read-only",
                    "responses": {"200": {"description": "Service is healthy"}}
                }
            },
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List all users",
                    "description": "Regular CRUD operation - should be ignored",
                    "responses": {"200": {"description": "User list"}}
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create new user",
                    "description": "Regular CRUD operation - should be ignored",
                    "responses": {"201": {"description": "User created"}}
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }
    actions = await agent.discover_from_swagger(swagger_doc, service_name="payment-service")
    
    print(actions)
    # Register discovered actions
    integration = RegistryIntegration(registry)
    summary = await integration.register_actions(actions)
    
    print(f"\n Registered {summary['registered']} actions")
    print(f"  Services: {summary['services']}")
    print(f"  Risk breakdown: {summary['risk_levels']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
