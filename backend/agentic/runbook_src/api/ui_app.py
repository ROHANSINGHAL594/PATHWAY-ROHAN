"""
Gradio UI for Runbook Action Registry Management
Provides interface to view, add, modify, and delete remediation actions
"""
import gradio as gr
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from ..core.runbook_registry import RunbookRegistry, RemediationAction
from ..agents.llm_discovery_agent import LLMDiscoveryAgent

load_dotenv()


class RunbookUI:
    """Main UI application for managing runbook actions"""
    
    def __init__(self):
        self.registry = None
        self.discovery_agent = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
    async def _init_async(self):
        """Initialize async components"""
        self.registry = RunbookRegistry(database_url=self.config.database_url)
        await self.registry.initialize()
        self.discovery_agent = LLMDiscoveryAgent()
        
    def init(self):
        """Initialize the application"""
        self.loop.run_until_complete(self._init_async())
        
    async def _get_all_actions(self) -> pd.DataFrame:
        """Fetch all actions from registry and format as DataFrame"""
        try:
            actions = await self.registry.list_all()
            
            if not actions:
                return pd.DataFrame(columns=[
                    "Action ID", "Service", "Method", "Description", 
                    "Risk Level", "Requires Approval", "Execution Details", "Secrets"
                ])
            
            data = []
            for action in actions:
                # Convert Pydantic model to dict
                action_dict = action.model_dump() if hasattr(action, 'model_dump') else action
                
                # Format execution details as JSON string
                exec_details = json.dumps(action_dict.get('execution', {}), indent=2)
                
                # Format secrets as comma-separated list
                secrets_list = ', '.join(action_dict.get('secrets', []))
                
                data.append({
                    "Action ID": action_dict.get('action_id', ''),
                    "Service": action_dict.get('service', ''),
                    "Method": action_dict.get('method', ''),
                    "Description": action_dict.get('definition', ''),
                    "Risk Level": action_dict.get('risk_level', ''),
                    "Requires Approval": "Yes" if action_dict.get('requires_approval', False) else "No",
                    "Execution Details": exec_details,
                    "Secrets": secrets_list
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error fetching actions: {e}")
            return pd.DataFrame(columns=[
                "Action ID", "Service", "Method", "Description", 
                "Risk Level", "Requires Approval", "Execution Details", "Secrets"
            ])
    
    def get_all_actions(self) -> pd.DataFrame:
        """Sync wrapper for getting all actions"""
        return self.loop.run_until_complete(self._get_all_actions())
    
    async def _get_action_details(self, action_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific action"""
        if not action_id:
            return {}
        
        try:
            action = await self.registry.get(action_id)
            if action:
                return action.model_dump()
            return {}
        except Exception as e:
            print(f"Error fetching action details: {e}")
            return {}
    
    def get_action_details(self, action_id: str) -> Dict[str, Any]:
        """Sync wrapper for getting action details"""
        return self.loop.run_until_complete(self._get_action_details(action_id))
    
    async def _add_manual_action(
        self,
        action_id: str,
        service: str,
        method: str,
        definition: str,
        risk_level: str,
        requires_approval: bool,
        execution_json: str,
        parameters_json: str,
        secrets_list: str,
        metadata_json: str
    ) -> tuple[str, pd.DataFrame]:
        """Add a new action manually"""
        try:
            # Parse JSON fields
            execution = json.loads(execution_json) if execution_json.strip() else {}
            parameters = json.loads(parameters_json) if parameters_json.strip() else {}
            metadata = json.loads(metadata_json) if metadata_json.strip() else {}
            
            # Parse secrets list
            secrets = [s.strip() for s in secrets_list.split(',') if s.strip()]
            
            # Create action
            action = RemediationAction(
                action_id=action_id,
                service=service,
                method=method,
                definition=definition,
                risk_level=risk_level,
                requires_approval=requires_approval,
                validated=False,
                execution=execution,
                parameters=parameters,
                secrets=secrets,
                action_metadata=metadata
            )
            
            # Save to registry
            await self.registry.save(action)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully added action: {action_id}", df
            
        except json.JSONDecodeError as e:
            return f"ERROR: JSON parsing error: {str(e)}", await self._get_all_actions()
        except Exception as e:
            return f"ERROR: Error adding action: {str(e)}", await self._get_all_actions()
    
    def add_manual_action(self, *args) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for adding manual action"""
        return self.loop.run_until_complete(self._add_manual_action(*args))
    
    async def _discover_from_swagger(
        self,
        swagger_url: str,
        service_name: str
    ) -> tuple[str, pd.DataFrame]:
        """Discover actions from Swagger/OpenAPI spec"""
        try:
            if not swagger_url or not service_name:
                return "ERROR: Please provide both Swagger URL and service name", await self._get_all_actions()
            
            # Fetch swagger spec
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(swagger_url) as response:
                    if response.status != 200:
                        return f"ERROR: Failed to fetch Swagger spec: HTTP {response.status}", await self._get_all_actions()
                    swagger_doc = await response.json()
            
            # Use discovery planner, TODO: error here not defined
            from discovery_planner import CoordinatedDiscoveryAgent
            agent = CoordinatedDiscoveryAgent()
            
            actions = await agent.discover_from_swagger(swagger_doc, service_name)
            
            if not actions:
                return "WARNING: No actions discovered from Swagger spec", await self._get_all_actions()
            
            # Save all discovered actions
            await self.registry.bulk_save(actions)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully discovered and saved {len(actions)} actions from Swagger", df
            
        except Exception as e:
            return f"ERROR: Error discovering from Swagger: {str(e)}", await self._get_all_actions()
    
    def discover_from_swagger(self, *args) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for Swagger discovery"""
        return self.loop.run_until_complete(self._discover_from_swagger(*args))
    
    async def _discover_from_script(
        self,
        script_path: str,
        service_name: str,
        use_ssh: bool,
        ssh_host: str,
        ssh_username: str,
        ssh_password: str,
        ssh_key_path: str
    ) -> tuple[str, pd.DataFrame]:
        """Discover actions from script file"""
        try:
            if not script_path or not service_name:
                return "ERROR: Please provide both script path and service name", await self._get_all_actions()
            
            if use_ssh:
                # SSH-based discovery
                if not ssh_host or not ssh_username:
                    return "ERROR: SSH host and username required for SSH discovery", await self._get_all_actions()
                
                credentials = {
                    'username': ssh_username,
                    'password': ssh_password if ssh_password else None,
                    'private_key_path': ssh_key_path if ssh_key_path else None
                }
                
                actions = await self.discovery_agent.discover_from_ssh(
                    host=ssh_host,
                    scripts_path=script_path,
                    credentials=credentials,
                    service_name=service_name
                )
            else:
                # Local file discovery
                import os
                if not os.path.exists(script_path):
                    return f"ERROR: Script file not found: {script_path}", await self._get_all_actions()
                
                with open(script_path, 'r') as f:
                    script_content = f.read()
                
                script_listings = [{
                    "path": script_path,
                    "content": script_content
                }]
                
                actions = await self.discovery_agent.discover_from_scripts(
                    script_listings=script_listings,
                    service_name=service_name
                )
            
            if not actions:
                return "WARNING: No actions discovered from script", await self._get_all_actions()
            
            # Post-process: Ensure execution details are set
            for action in actions:
                if action.execution is None or not action.execution.get('command'):
                    operation_name = action.action_id.replace('-', '_').replace(' ', '_')
                    action.execution = {
                        "script_path": script_path,
                        "command": f"{script_path} {operation_name}",
                        "timeout_seconds": 30
                    }
                if not action.secrets:
                    action.secrets = ["ssh_host", "ssh_username", "ssh_password"]
            
            # Save all discovered actions
            await self.registry.bulk_save(actions)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully discovered and saved {len(actions)} actions from script", df
            
        except Exception as e:
            return f"ERROR: Error discovering from script: {str(e)}", await self._get_all_actions()
    
    def discover_from_script(self, *args) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for script discovery"""
        return self.loop.run_until_complete(self._discover_from_script(*args))
    
    async def _discover_from_documentation(
        self,
        documentation: str,
        service_name: str
    ) -> tuple[str, pd.DataFrame]:
        """Discover actions from documentation text"""
        try:
            if not documentation or not service_name:
                return "ERROR: Please provide both documentation and service name", await self._get_all_actions()
            
            actions = await self.discovery_agent.discover_from_documentation(
                documentation=documentation,
                service_name=service_name
            )
            
            if not actions:
                return "WARNING: No actions discovered from documentation", await self._get_all_actions()
            
            # Save all discovered actions
            await self.registry.bulk_save(actions)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully discovered and saved {len(actions)} actions from documentation", df
            
        except Exception as e:
            return f"ERROR: Error discovering from documentation: {str(e)}", await self._get_all_actions()
    
    def discover_from_documentation(self, *args) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for documentation discovery"""
        return self.loop.run_until_complete(self._discover_from_documentation(*args))
    
    async def _delete_action(self, action_id: str) -> tuple[str, pd.DataFrame]:
        """Delete an action from registry"""
        try:
            if not action_id:
                return "ERROR: Please provide an action ID", await self._get_all_actions()
            
            # Check if action exists
            action = await self.registry.get(action_id)
            if not action:
                return f"ERROR: Action not found: {action_id}", await self._get_all_actions()
            
            # Delete action
            await self.registry.delete(action_id)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully deleted action: {action_id}", df
            
        except Exception as e:
            return f"ERROR: Error deleting action: {str(e)}", await self._get_all_actions()
    
    def delete_action(self, action_id: str) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for deleting action"""
        return self.loop.run_until_complete(self._delete_action(action_id))
    
    async def _update_action(
        self,
        action_id: str,
        service: str,
        method: str,
        definition: str,
        risk_level: str,
        requires_approval: bool,
        execution_json: str,
        parameters_json: str,
        secrets_list: str,
        metadata_json: str
    ) -> tuple[str, pd.DataFrame]:
        """Update an existing action"""
        try:
            # Check if action exists
            existing = await self.registry.get(action_id)
            if not existing:
                return f"ERROR: Action not found: {action_id}", await self._get_all_actions()
            
            # Parse JSON fields
            execution = json.loads(execution_json) if execution_json.strip() else {}
            parameters = json.loads(parameters_json) if parameters_json.strip() else {}
            metadata = json.loads(metadata_json) if metadata_json.strip() else {}
            
            # Parse secrets list
            secrets = [s.strip() for s in secrets_list.split(',') if s.strip()]
            
            # Create updated action
            action = RemediationAction(
                action_id=action_id,
                service=service,
                method=method,
                definition=definition,
                risk_level=risk_level,
                requires_approval=requires_approval,
                validated=existing.validated,  # Keep validation status
                execution=execution,
                parameters=parameters,
                secrets=secrets,
                action_metadata=metadata
            )
            
            # Save to registry (will update existing)
            await self.registry.save(action)
            
            # Refresh table
            df = await self._get_all_actions()
            return f"Successfully updated action: {action_id}", df
            
        except json.JSONDecodeError as e:
            return f"ERROR: JSON parsing error: {str(e)}", await self._get_all_actions()
        except Exception as e:
            return f"ERROR: Error updating action: {str(e)}", await self._get_all_actions()
    
    def update_action(self, *args) -> tuple[str, pd.DataFrame]:
        """Sync wrapper for updating action"""
        return self.loop.run_until_complete(self._update_action(*args))
    
    def load_action_for_edit(self, df: pd.DataFrame, evt: gr.SelectData) -> tuple:
        """Load action details when row is selected"""
        if df is None or df.empty or evt.index[0] >= len(df):
            return ("", "", "", "", "", False, "{}", "{}", "", "{}")
        
        row = df.iloc[evt.index[0]]
        
        return (
            row["Action ID"],
            row["Service"],
            row["Method"],
            row["Description"],
            row["Risk Level"],
            row["Requires Approval"] == "Yes",
            row["Execution Details"],
            "{}",  # Parameters - need to fetch from registry
            row["Secrets"],
            "{}"  # Metadata - need to fetch from registry
        )


def create_ui():
    """Create and launch the Gradio UI"""
    
    # Initialize UI application
    ui_app = RunbookUI()
    ui_app.init()
    
    # Custom CSS for better styling
    custom_css = """
    .action-table {
        font-size: 14px;
    }
    .status-message {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    """
    
    with gr.Blocks(title="Runbook Action Registry") as app:
        gr.Markdown("# Runbook Action Registry Management")
        gr.Markdown("Manage remediation actions with LLM-powered discovery")
        
        with gr.Tabs():
            # Tab 1: View All Actions
            with gr.Tab("View Actions"):
                gr.Markdown("### All Registered Actions")
                refresh_btn = gr.Button("Refresh", variant="secondary")
                actions_table = gr.Dataframe(
                    value=ui_app.get_all_actions(),
                    label="Actions Registry",
                    interactive=False,
                    wrap=True
                )
                
                refresh_btn.click(
                    fn=ui_app.get_all_actions,
                    outputs=actions_table
                )
            
            # Tab 2: Add Action Manually
            with gr.Tab("Add Action Manually"):
                gr.Markdown("### Create New Action")
                
                with gr.Row():
                    with gr.Column():
                        manual_action_id = gr.Textbox(label="Action ID*", placeholder="restart-nginx-service")
                        manual_service = gr.Textbox(label="Service Name*", placeholder="nginx-server")
                        manual_method = gr.Dropdown(
                            label="Execution Method*",
                            choices=["rpc", "api", "script", "command", "k8s"],
                            value="rpc"
                        )
                        manual_definition = gr.Textbox(
                            label="Description*",
                            placeholder="Restart nginx web server",
                            lines=2
                        )
                    
                    with gr.Column():
                        manual_risk = gr.Dropdown(
                            label="Risk Level*",
                            choices=["low", "medium", "high"],
                            value="medium"
                        )
                        manual_approval = gr.Checkbox(label="Requires Approval", value=False)
                        manual_secrets = gr.Textbox(
                            label="Secrets (comma-separated)",
                            placeholder="ssh_host, ssh_username, ssh_password",
                            lines=2
                        )
                
                with gr.Row():
                    manual_execution = gr.Code(
                        label="Execution Details (JSON)",
                        language="json",
                        value='{\n  "command": "systemctl restart nginx",\n  "timeout_seconds": 30\n}'
                    )
                    manual_parameters = gr.Code(
                        label="Parameters (JSON)",
                        language="json",
                        value='{}'
                    )
                
                manual_metadata = gr.Code(
                    label="Metadata (JSON)",
                    language="json",
                    value='{\n  "tags": ["systemctl", "nginx"]\n}'
                )
                
                manual_add_btn = gr.Button("Add Action", variant="primary")
                manual_status = gr.Markdown()
                manual_result_table = gr.Dataframe(label="Updated Registry")
                
                manual_add_btn.click(
                    fn=ui_app.add_manual_action,
                    inputs=[
                        manual_action_id, manual_service, manual_method,
                        manual_definition, manual_risk, manual_approval,
                        manual_execution, manual_parameters, manual_secrets,
                        manual_metadata
                    ],
                    outputs=[manual_status, manual_result_table]
                )
            
            # Tab 3: Discover from Swagger
            with gr.Tab("Discover from Swagger/OpenAPI"):
                gr.Markdown("### LLM-Powered API Discovery")
                
                swagger_url = gr.Textbox(
                    label="Swagger/OpenAPI URL*",
                    placeholder="http://localhost:8000/openapi.json",
                    lines=1
                )
                swagger_service = gr.Textbox(
                    label="Service Name*",
                    placeholder="payment-service"
                )
                
                swagger_discover_btn = gr.Button("Discover Actions", variant="primary")
                swagger_status = gr.Markdown()
                swagger_result_table = gr.Dataframe(label="Discovered Actions")
                
                swagger_discover_btn.click(
                    fn=ui_app.discover_from_swagger,
                    inputs=[swagger_url, swagger_service],
                    outputs=[swagger_status, swagger_result_table]
                )
            
            # Tab 4: Discover from Script
            with gr.Tab("Discover from Script"):
                gr.Markdown("### LLM-Powered Script Discovery")
                
                with gr.Row():
                    with gr.Column():
                        script_path = gr.Textbox(
                            label="Script Path*",
                            placeholder="/path/to/script.sh or /var/scripts/",
                            lines=1
                        )
                        script_service = gr.Textbox(
                            label="Service Name*",
                            placeholder="payment-service"
                        )
                        script_use_ssh = gr.Checkbox(label="Access via SSH", value=False)
                    
                    with gr.Column(visible=True) as ssh_fields:
                        script_ssh_host = gr.Textbox(
                            label="SSH Host",
                            placeholder="server.example.com"
                        )
                        script_ssh_user = gr.Textbox(
                            label="SSH Username",
                            placeholder="admin"
                        )
                        script_ssh_pass = gr.Textbox(
                            label="SSH Password (optional)",
                            type="password"
                        )
                        script_ssh_key = gr.Textbox(
                            label="SSH Key Path (optional)",
                            placeholder="/home/user/.ssh/id_rsa"
                        )
                
                def toggle_ssh_fields(use_ssh):
                    return gr.update(visible=use_ssh)
                
                script_use_ssh.change(
                    fn=toggle_ssh_fields,
                    inputs=script_use_ssh,
                    outputs=ssh_fields
                )
                
                script_discover_btn = gr.Button("Discover Actions", variant="primary")
                script_status = gr.Markdown()
                script_result_table = gr.Dataframe(label="Discovered Actions")
                
                script_discover_btn.click(
                    fn=ui_app.discover_from_script,
                    inputs=[
                        script_path, script_service, script_use_ssh,
                        script_ssh_host, script_ssh_user, script_ssh_pass,
                        script_ssh_key
                    ],
                    outputs=[script_status, script_result_table]
                )
            
            # Tab 5: Discover from Documentation
            with gr.Tab("Discover from Documentation"):
                gr.Markdown("### LLM-Powered Documentation Discovery")
                
                doc_text = gr.Textbox(
                    label="Infrastructure Documentation*",
                    placeholder="Paste your runbook or operational documentation here...",
                    lines=10
                )
                doc_service = gr.Textbox(
                    label="Service Name*",
                    placeholder="payment-service"
                )
                
                doc_discover_btn = gr.Button("Discover Actions", variant="primary")
                doc_status = gr.Markdown()
                doc_result_table = gr.Dataframe(label="Discovered Actions")
                
                doc_discover_btn.click(
                    fn=ui_app.discover_from_documentation,
                    inputs=[doc_text, doc_service],
                    outputs=[doc_status, doc_result_table]
                )
            
            # Tab 6: Modify/Delete Actions
            with gr.Tab("Modify/Delete Actions"):
                gr.Markdown("### Edit or Remove Actions")
                gr.Markdown("**Select a row from the table below to load it for editing**")
                
                modify_table = gr.Dataframe(
                    value=ui_app.get_all_actions(),
                    label="Select Action to Modify",
                    interactive=False
                )
                
                gr.Markdown("---")
                
                with gr.Row():
                    with gr.Column():
                        edit_action_id = gr.Textbox(label="Action ID (read-only)", interactive=False)
                        edit_service = gr.Textbox(label="Service Name*")
                        edit_method = gr.Dropdown(
                            label="Execution Method*",
                            choices=["rpc", "api", "script", "command", "k8s"]
                        )
                        edit_definition = gr.Textbox(label="Description*", lines=2)
                    
                    with gr.Column():
                        edit_risk = gr.Dropdown(
                            label="Risk Level*",
                            choices=["low", "medium", "high"]
                        )
                        edit_approval = gr.Checkbox(label="Requires Approval")
                        edit_secrets = gr.Textbox(
                            label="Secrets (comma-separated)",
                            lines=2
                        )
                
                with gr.Row():
                    edit_execution = gr.Code(label="Execution Details (JSON)", language="json")
                    edit_parameters = gr.Code(label="Parameters (JSON)", language="json")
                
                edit_metadata = gr.Code(label="Metadata (JSON)", language="json")
                
                with gr.Row():
                    update_btn = gr.Button("Update Action", variant="primary")
                    delete_btn = gr.Button("Delete Action", variant="stop")
                
                modify_status = gr.Markdown()
                modify_result_table = gr.Dataframe(label="Updated Registry")
                
                # Load action when row is selected
                modify_table.select(
                    fn=ui_app.load_action_for_edit,
                    inputs=modify_table,
                    outputs=[
                        edit_action_id, edit_service, edit_method,
                        edit_definition, edit_risk, edit_approval,
                        edit_execution, edit_parameters, edit_secrets,
                        edit_metadata
                    ]
                )
                
                # Update action
                update_btn.click(
                    fn=ui_app.update_action,
                    inputs=[
                        edit_action_id, edit_service, edit_method,
                        edit_definition, edit_risk, edit_approval,
                        edit_execution, edit_parameters, edit_secrets,
                        edit_metadata
                    ],
                    outputs=[modify_status, modify_result_table]
                )
                
                # Delete action
                delete_btn.click(
                    fn=ui_app.delete_action,
                    inputs=edit_action_id,
                    outputs=[modify_status, modify_result_table]
                )
        
        gr.Markdown("---")
        gr.Markdown("**Tips:** Use LLM discovery for automatic action extraction from APIs, scripts, or documentation. Manual mode allows full control over action configuration.")
    
    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
