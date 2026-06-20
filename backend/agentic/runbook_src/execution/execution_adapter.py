"""
Execution Adapter - Bridge between RunbookRegistry and ExecutionEngine
Transforms RemediationAction (registry schema) to ExecutionEngine action format
"""

from typing import Dict, Any, List, Optional
from ..core.runbook_registry import RemediationAction


class ExecutionAdapter:
    """
    Adapts RemediationAction from registry to execution engine format
    """
    
    @staticmethod
    def to_execution_format(action: RemediationAction) -> Dict[str, Any]:
        """
        Transform RemediationAction to execution engine format
        
        Args:
            action: RemediationAction from registry
            
        Returns:
            Dict compatible with execution_engine.ActionExecutor
        """
        # Map method to action_type
        action_type_map = {
            'rpc': 'rpc',
            'script': 'script',
            'api': 'api_call',
            'k8s': 'k8s_command',
            'command': 'command'  # Map command to command action_type
        }
        
        action_type = action_type_map.get(action.method, 'command')
        
        # Base action structure
        exec_action = {
            'action_id': action.action_id,
            'action_type': action_type,
            'timeout_seconds': action.action_metadata.get('timeout', 30),
            'affected_services': [action.service],
            'execution_context': action.action_metadata.copy()
        }
        
        # Add method-specific fields
        if action.method == 'rpc':
            exec_action.update({
                'rpc_endpoint': action.execution.get('endpoint', ''),
                'http_method': action.execution.get('http_method', 'POST'),
                'parameters': ExecutionAdapter._transform_parameters(action.parameters),
                'secrets': ExecutionAdapter._transform_secrets(action.secrets, action.action_metadata),
                'rollback_endpoint': action.execution.get('rollback_endpoint')
            })
            # Add base_url to execution_context if present
            if 'base_url' in action.execution:
                exec_action['execution_context']['base_url'] = action.execution['base_url']
        
        elif action.method == 'script':
            exec_action.update({
                'script_path': action.execution.get('script_path', ''),
                'command': action.execution.get('command', ''),
                'parameters': ExecutionAdapter._transform_parameters(action.parameters),
                'secrets': ExecutionAdapter._transform_secrets(action.secrets, action.action_metadata),
                'execution_context': {
                    'use_local_execution': action.execution.get('use_local_execution', False)
                }
            })
            # Add SSH secret mapping if present in action_metadata (new approach)
            if 'ssh_secret_mapping' in action.action_metadata:
                exec_action['execution_context']['ssh_secret_mapping'] = action.action_metadata['ssh_secret_mapping']
            # Legacy: Add SSH connection info if present in action_metadata
            elif 'ssh_connection' in action.action_metadata:
                exec_action['execution_context']['ssh_connection'] = action.action_metadata['ssh_connection']
        
        elif action.method == 'api':
            exec_action.update({
                'api_endpoint': action.execution.get('endpoint', ''),
                'http_method': action.execution.get('http_method', 'POST'),
                'parameters': ExecutionAdapter._transform_parameters(action.parameters),
                'secrets': ExecutionAdapter._transform_secrets(action.secrets, action.action_metadata)
            })
        
        elif action.method == 'k8s':
            exec_action.update({
                'command': action.execution.get('command', ''),
                'namespace': action.execution.get('namespace', 'default'),
                'parameters': ExecutionAdapter._transform_parameters(action.parameters),
                'secrets': ExecutionAdapter._transform_secrets(action.secrets, action.action_metadata)
            })
        
        elif action.method == 'command':
            exec_action.update({
                'command': action.execution.get('command', ''),
                'parameters': ExecutionAdapter._transform_parameters(action.parameters),
                'secrets': ExecutionAdapter._transform_secrets(action.secrets, action.action_metadata)
            })
        
        return exec_action
    
    @staticmethod
    def _transform_parameters(params: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform parameter dict to list format expected by execution engine
        
        Registry format:
        {
            "param_name": {"type": "string", "required": true, "default": null}
        }
        
        Execution engine format:
        [
            {"name": "param_name", "type": "string", "required": true, "default": null}
        ]
        """
        param_list = []
        for name, spec in params.items():
            param_dict = spec.copy()
            param_dict['name'] = name
            param_list.append(param_dict)
        
        return param_list
    
    @staticmethod
    def _transform_secrets(
        secret_names: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform secret names to secrets config expected by execution engine
        
        Registry format: "secret_references": [{"name": "api_key", "path": "secret/api_key", ...}]}
        
        
        """
        return secret_names
    
    @staticmethod
    def from_execution_result(
        action_id: str,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform execution result back to registry-compatible format for history
        
        Args:
            action_id: ID of the executed action
            execution_context: ExecutionContext from execution engine
            
        Returns:
            Dict suitable for storing in execution history
        """
        return {
            'action_id': action_id,
            'execution_id': execution_context.get('execution_id'),
            'status': execution_context.get('status'),
            'result': execution_context.get('result'),
            'error': execution_context.get('error'),
            'audit_log': execution_context.get('audit_log', []),
            'duration_seconds': execution_context.get('duration_seconds'),
            'timestamp': execution_context.get('timestamp')
        }
