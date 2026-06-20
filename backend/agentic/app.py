from dotenv import load_dotenv
load_dotenv()
from typing import List, Any, Optional, Dict
from datetime import datetime, timezone
import logging
import os
import asyncio
import json
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from langgraph.graph.state import CompiledStateGraph
from .prompts import AgentPayload
from .workflow import create_workflow, run_agentic_query
from .rca.summarize import init_summarize_agent, summarize, SummarizeRequest
from .alerts import generate_alert, AlertRequest
from .rca.analyse import InitRCA, rca
from .report_generation.api.schemas import (
    IncidentReportRequest, 
    IncidentReportResponse, 
    WeeklyReportRequest, 
    WeeklyReportResponse,
    ErrorResponse
)
from .report_generation.core.report_generator import generate_incident_report
from .report_generation.core.weekly_generator import generate_weekly_report
from postgres_util import postgre_url

logger = logging.getLogger(__name__)
# Runbook imports
try:
    from .runbook_src.core.remediation_orchestrator import RemediationOrchestrator
    from .runbook_src.core.llm_suggestion_service import LLMSuggestionService
    from .runbook_src.execution.execution_engine import ActionExecutor
    from .runbook_src.core.runbook_registry import RunbookRegistry, RemediationAction
    from .runbook_src.execution.safety_validator import SafetyValidator
    from .runbook_src.services.secrets_manager import SecretsManager, get_secrets_manager
    from .runbook_src.services.ssh_client import SSHClientFactory
    from .runbook_src.agents.llm_discovery_agent import LLMDiscoveryAgent, RegistryIntegration

    RUNBOOK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Runbook modules not available: {e}")
    RUNBOOK_AVAILABLE = False

# Configure logging

planner_executor: CompiledStateGraph = None

# Runbook global instances
orchestrator: Optional[Any] = None
discovery_agent: Optional[LLMDiscoveryAgent] = None
registry: Optional[Any] = None
secrets_manager: Optional[SecretsManager] = None

# MongoDB for notifications
mongo_client: Optional[AsyncIOMotorClient] = None
notification_collection: Optional[Any] = None
rca_collection: Optional[Any] = None

# Use OpenAI's o1 reasoning model for complex analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator, discovery_agent, registry, mongo_client, notification_collection, rca_collection, secrets_manager
    
    # Initialize MongoDB for notifications and RCA events
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        mongo_db_name = os.getenv("MONGO_DB", "easyworkflow")
        mongo_client = AsyncIOMotorClient(mongo_uri)
        db = mongo_client[mongo_db_name]
        notification_collection = db["notifications"]
        rca_collection = db["rca_events"]
        logger.info("MongoDB notification and RCA collections initialized")
        
        # Store in app state for access in routes
        app.state.rca_collection = rca_collection
        app.state.notification_collection = notification_collection
    except Exception as e:
        logger.warning(f"Could not initialize MongoDB for notifications/RCA: {e}")
        mongo_client = None
        notification_collection = None
        rca_collection = None
    
    # Initialize existing agentic components
    await init_summarize_agent()
    
    # Initialize runbook components if available
    if RUNBOOK_AVAILABLE:
        try:
            logger.info("Initializing runbook components...")
            
            # Initialize SSH client factory for discovery
            ssh_factory = SSHClientFactory(max_connections_per_host=3)
            
            def ssh_client_factory(host: str, credentials: Dict[str, Any]):
                port = int(credentials.get('port', 22)) if credentials.get('port') else 22
                return ssh_factory.create_client(
                    host=host,
                    credentials=credentials,
                    port=port,
                    timeout=30
                )
            
            # Initialize discovery agent with SSH support
            discovery_agent = LLMDiscoveryAgent(ssh_client_factory=ssh_client_factory)
            logger.info("Discovery agent initialized successfully")
            
            # Initialize secrets manager (uses SQLite, always available)
            secrets_manager = SecretsManager()
            logger.info("Secrets manager initialized successfully")

            # Try to initialize DB components with retry logic
            max_retries = 5
            retry_delay = 3  # seconds
            
            for attempt in range(max_retries):
                try:
                    from postgres_util import postgre_async_url
                    db_url = postgre_async_url
                    
                    logger.info(f"Attempting to initialize database (attempt {attempt + 1}/{max_retries})...")
                    registry = RunbookRegistry(database_url=db_url)
                    await registry.initialize()
                    
                    validator = SafetyValidator(otel_client=None, metrics_client=None)
                    executor = ActionExecutor(validator, secrets_manager, None)
                    
                    try:
                        suggestion_service = LLMSuggestionService()
                        logger.info("LLM suggestion service initialized")
                    except Exception as llm_error:
                        logger.warning(f"Could not initialize LLM suggestion service: {llm_error}")
                        suggestion_service = None
                    
                    pathway_url = os.getenv("PATHWAY_API_URL", "http://localhost:8001")
                    orchestrator = RemediationOrchestrator(
                        pathway_api_url=pathway_url,
                        runbook_registry=registry,
                        action_executor=executor,
                        confidence_thresholds={'high': 0.3, 'medium': 0.5},
                        suggestion_service=suggestion_service
                    )
                    logger.info("Runbook orchestrator initialized successfully")
                    break  # Success, exit retry loop
                    
                except Exception as db_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"DB initialization attempt {attempt + 1} failed: {db_error}")
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.warning(f"Could not initialize orchestrator after {max_retries} attempts: {db_error}")
                        logger.info("Discovery endpoints will still work without orchestrator")
        
        except Exception as e:
            logger.error(f"Failed to initialize runbook components: {e}")
    
    yield
    
    # Cleanup
    if mongo_client:
        mongo_client.close()
    
    logger.info("Shutting down...")


app = FastAPI(title="Agentic API", lifespan=lifespan)

# ============ API Endpoints ============

@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Agentic API is running"}

class InferModel(BaseModel):
    agents: List[AgentPayload]
    pipeline_name: str
@app.post("/build")
async def build(request: InferModel):
    global planner_executor
    planner_executor = create_workflow(request.agents)

    return {"status": "built"}

@app.post("/generate-alert")
async def generate_alert_route(request: AlertRequest):
    return await generate_alert(request)

@app.post("/summarize")
async def summarize_route(request: SummarizeRequest):
    return await summarize(request)

@app.post("/rca")
async def rca_route(request: InitRCA):
    # Get RCA collection from app state (set in lifespan)
    rca_collection = getattr(app.state, 'rca_collection', None)
    response = await rca(request, rca_collection=rca_collection)
    return response

class Prompt(BaseModel):
    role: str
    content: str

@app.post("/infer")
async def infer(prompt: Prompt):
    if not planner_executor:
        raise HTTPException(status_code=502, detail="PIPELINE_ID not set in environment")
    answer = await run_agentic_query(prompt.content, planner_executor)
    return {"status": "ok", **answer}

# ============ Report Generation Endpoints ============

@app.post(
    "/api/v1/reports/incident",
    response_model=IncidentReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Report generation failed"}
    },
    summary="Generate Incident Report",
    description=(
        "Generates a detailed incident report using the LangGraph multi-agent workflow. "
        "Takes RCA output from telemetry analysis and produces a comprehensive "
        "markdown report with analysis and recommendations."
    ),
    tags=["incident-reports"]
)
async def create_incident_report(request: IncidentReportRequest):
    """
    Generate an incident report from telemetry-based RCA output.
    
    The report generation process:
    1. Validates input data structure
    2. Executes multi-agent workflow (Planner -> Drafter)
    3. Saves report to file storage
    4. Returns the complete report with metadata
    
    Expected processing time: 15-25 seconds depending on incident complexity.
    """
    start_time = datetime.now()
    
    try:
        
        logger.info(
            f"Received incident report request"
            f"(severity: {request.rca_output.severity})"
        )
        
        # Convert Pydantic model to dictionary for the core logic
        rca_output = request.rca_output.model_dump(mode='json')
        
        # Generate the report using core business logic
        report_content, metadata = generate_incident_report(
            rca_output=rca_output
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"Successfully generated report {metadata['report_id']} "
            f"in {processing_time:.2f}s"
        )
        
        # Return structured response
        return IncidentReportResponse(
            success=True,
            report_id=metadata["report_id"],
            report_content=report_content,
            severity=metadata["severity"],
            generated_at=metadata["generated_at"],
            processing_time_seconds=processing_time
        )
        
    except ValueError as e:
        # Configuration or validation errors
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "ValidationError",
                "message": str(e),
                "details": None
            }
        )
        
    except Exception as e:
        # Unexpected errors during report generation
        logger.error(f"Report generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_type": "ReportGenerationError",
                "message": "Failed to generate incident report. Please check your input data and try again.",
                "details": {"error": str(e)}
            }
        )


@app.post(
    "/api/v1/reports/weekly",
    response_model=WeeklyReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Report generation failed"}
    },
    summary="Generate Weekly Summary Report",
    description=(
        "Generates a weekly summary report that aggregates all incident reports "
        "from the specified date range. Reads from file storage, calculates "
        "statistics, and produces an executive summary with trends and insights."
    ),
    tags=["weekly-reports"]
)
async def create_weekly_report(request: WeeklyReportRequest):
    """
    Generate a weekly summary report for the specified date range.
    
    The report generation process:
    1. Reads incident reports from file storage in the date range
    2. Calculates severity breakdown and trends
    3. Generates executive summary using LLM
    4. Saves report to weekly_reports/ directory
    
    If no incidents occurred during the period, generates an "all-clear" report.
    
    Expected processing time: 10-20 seconds depending on incident count.
    """
    start_time = datetime.now()
    
    try:
        # Normalize dates to UTC timezone if provided
        start_date = request.start_date
        end_date = request.end_date
        
        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        if start_date and end_date:
            logger.info(
                f"Received weekly report request: {start_date.date()} "
                f"to {end_date.date()}"
            )
            
            # Validate date range
            if end_date < start_date:
                raise ValueError("end_date must be after start_date")
        else:
            logger.info("Received weekly report request for all available reports")
        
        # Generate the weekly report using core business logic
        report_content, metadata = generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            cleanup_after_report=request.cleanup_after_report
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        cleanup_msg = " (cleanup performed)" if metadata.get('cleanup_performed', False) else ""
        logger.info(
            f"Successfully generated weekly report with {metadata['incident_count']} "
            f"incidents in {processing_time:.2f}s{cleanup_msg}"
        )
        
        # Return structured response
        return WeeklyReportResponse(
            success=True,
            report_content=report_content,
            start_date=metadata["start_date"],
            end_date=metadata["end_date"],
            incident_count=metadata["incident_count"],
            generated_at=metadata["generated_at"],
            processing_time_seconds=processing_time
        )
        
    except ValueError as e:
        # Configuration or validation errors
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error_type": "ValidationError",
                "message": str(e),
                "details": None
            }
        )
        
    except Exception as e:
        # Unexpected errors during report generation
        logger.error(f"Weekly report generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_type": "WeeklyReportGenerationError",
                "message": "Failed to generate weekly report. Please check your input data and try again.",
                "details": {"error": str(e)}
            }
        )


# ============ Reports List and Access Endpoints ============
from pathlib import Path
from fastapi.responses import FileResponse, PlainTextResponse

REPORTS_DIR = Path("reports")

@app.get(
    "/api/v1/reports/list",
    summary="List Available Reports",
    description="List all available incident reports with their metadata.",
    tags=["reports"]
)
async def list_reports():
    """
    List all available incident reports from the reports directory.
    Returns report IDs, severity, timestamps and filenames.
    """
    try:
        reports = []
        if REPORTS_DIR.exists():
            # Get all JSON metadata files
            for json_file in REPORTS_DIR.glob("incident_*.json"):
                try:
                    with open(json_file, "r") as f:
                        metadata = json.load(f)
                        report_id = json_file.stem  # filename without extension
                        reports.append({
                            "report_id": report_id,
                            "incident_id": metadata.get("incident_id"),
                            "severity": metadata.get("severity"),
                            "primary_service": metadata.get("primary_service"),
                            "affected_services": metadata.get("affected_services", []),
                            "timestamp": metadata.get("timestamp"),
                            "filename": metadata.get("filename")
                        })
                except Exception as e:
                    logger.warning(f"Failed to read report metadata {json_file}: {e}")
        
        # Sort by timestamp (newest first)
        reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {"success": True, "reports": reports, "count": len(reports)}
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {e}")


@app.get(
    "/api/v1/reports/{report_id}",
    summary="Get Report Content",
    description="Get the content of a specific incident report by ID.",
    tags=["reports"]
)
async def get_report(report_id: str):
    """
    Get the content and metadata of a specific report.
    """
    try:
        # Look for the markdown file
        md_file = REPORTS_DIR / f"{report_id}.md"
        json_file = REPORTS_DIR / f"{report_id}.json"
        
        if not md_file.exists():
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
        
        with open(md_file, "r") as f:
            content = f.read()
        
        metadata = {}
        if json_file.exists():
            with open(json_file, "r") as f:
                metadata = json.load(f)
        
        return {
            "success": True,
            "report_id": report_id,
            "content": content,
            "metadata": metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get report: {e}")


@app.get(
    "/api/v1/reports/{report_id}/download",
    summary="Download Report",
    description="Download the report as a markdown file.",
    tags=["reports"]
)
async def download_report(report_id: str):
    """
    Download the report markdown file.
    """
    try:
        md_file = REPORTS_DIR / f"{report_id}.md"
        
        if not md_file.exists():
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
        
        return FileResponse(
            path=md_file,
            filename=f"{report_id}.md",
            media_type="text/markdown"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {e}")


# ============ Runbook Remediation Endpoints ============

if RUNBOOK_AVAILABLE:
    # Helper function to send approval notifications
    async def send_approval_notification(
        request_id: str,
        error_message: str,
        matched_error: str,
        actions: List[str],
        confidence: str,
        description: str,
        pipeline_id: str = None,
        actions_requiring_individual_approval: List[str] = None,
        approval_reason: str = None
    ) -> bool:
        """
        Send approval request notification to MongoDB
        This will trigger WebSocket broadcast via change stream watcher
        """
        if notification_collection is None:
            logger.warning("Notification collection not initialized, skipping notification")
            return False
        
        try:
            # Determine approval type and build appropriate message
            if actions_requiring_individual_approval:
                approval_type = "per-action"
                approval_details = f"Actions requiring individual approval: {', '.join(actions_requiring_individual_approval)}"
            else:
                approval_type = "request-level"
                approval_details = f"All {len(actions)} action(s) require approval due to {confidence} confidence match"
            
            notification_doc = {
                "pipeline_id": pipeline_id or "runbook-system",
                "title": "Approval Required for Remediation Action",
                "desc": f"Error: {error_message}\nMatched: {matched_error}\nConfidence: {confidence}\n\n{approval_details}",
                "type": "alert",
                "timestamp": datetime.now(timezone.utc),
                "alert": {
                    "actions": actions,
                    "action_taken": None,
                    "taken_at": None,
                    "action_executed_by": None,
                    "action_executed_by_user": None,
                    "status": "pending"
                },
                "remediation_metadata": {
                    "request_id": request_id,
                    "error_message": error_message,
                    "matched_error": matched_error,
                    "confidence": confidence,
                    "description": description,
                    "type": "approval_request",
                    "approval_type": approval_type,
                    "actions_requiring_individual_approval": actions_requiring_individual_approval or [],
                    "all_actions": actions,
                    "approval_reason": approval_reason or f"{confidence} confidence match"
                }
            }
            
            result = await notification_collection.insert_one(notification_doc)
            logger.info(f"Approval notification sent for request {request_id}: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
            return False
    
    async def update_notification_status(
        request_id: str,
        status: str,
        action_taken: str = None,
        executed_by: str = None
    ) -> bool:
        """
        Update notification status when approval is processed
        """
        if notification_collection is None:
            logger.warning("Notification collection not initialized, skipping update")
            return False
        
        try:
            update_doc = {
                "alert.status": status,
                "alert.taken_at": datetime.now(timezone.utc)
            }
            
            if action_taken:
                update_doc["alert.action_taken"] = action_taken
            
            if executed_by:
                update_doc["alert.action_executed_by"] = executed_by
            
            result = await notification_collection.update_one(
                {"remediation_metadata.request_id": request_id},
                {"$set": update_doc}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated notification for request {request_id} to status: {status}")
                return True
            else:
                logger.warning(f"No notification found for request {request_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
            return False
    
    # Runbook Request/Response Models
    class RemediationRequest(BaseModel):
        error_message: str = Field(..., description="Error message to remediate")
        auto_execute: bool = Field(True, description="Auto-execute high confidence matches")
        require_approval_medium: bool = Field(True, description="Require approval for medium confidence")

    class ApprovalRequest(BaseModel):
        request_id: str = Field(..., description="Approval request ID")
        action_id: Optional[str] = Field(None, description="Specific action ID to approve (optional)")
        approved: bool = Field(True, description="True to approve, False to reject")
        approved_by: str = Field(default="api_user", description="Who approved/rejected the request")
        rejection_reason: Optional[str] = Field(None, description="Reason for rejection (optional)")

    class ActionSuggestionItem(BaseModel):
        action_id: str
        reason: str

    class ErrorSuggestion(BaseModel):
        error_name: str
        description: str
        suggested_actions: List[ActionSuggestionItem]
        confidence_reasoning: str
        feasible: bool
        additional_actions_needed: Optional[str] = None

    class RemediationResponse(BaseModel):
        status: str
        error: str
        matched_error: Optional[str] = None
        distance: Optional[float] = None
        confidence: Optional[str] = None
        actions_executed: Optional[int] = None
        execution_results: Optional[List[Dict[str, Any]]] = None
        overall_success: Optional[bool] = None
        message: Optional[str] = None
        request_id: Optional[str] = None
        actions: Optional[List[str]] = None
        description: Optional[str] = None
        suggestion: Optional[ErrorSuggestion] = None
        rejection_reason: Optional[str] = None
        rejected_by: Optional[str] = None

    class RunbookHealthResponse(BaseModel):
        status: str
        pathway_api: str
        timestamp: str

    class ManualActionRequest(BaseModel):
        action_id: str = Field(..., description="Unique action identifier")
        service: str = Field(..., description="Service name")
        method: str = Field(..., description="Execution method")
        definition: str = Field(..., description="Action description")
        risk_level: str = Field(..., description="Risk level")
        requires_approval: bool = Field(False, description="Requires approval")
        execution: Dict[str, Any] = Field(default_factory=dict)
        parameters: Dict[str, Any] = Field(default_factory=dict)
        secrets: List[str] = Field(default_factory=list)
        action_metadata: Dict[str, Any] = Field(default_factory=dict)

    class DiscoverSwaggerRequest(BaseModel):
        swagger_url: Optional[str] = None
        swagger_doc: Optional[Dict[str, Any]] = None
        service_name: str

    class DiscoverScriptsRequest(BaseModel):
        scripts: List[Dict[str, str]]
        service_name: str

    class DiscoverSSHRequest(BaseModel):
        host: str
        scripts_path: str
        credentials: Dict[str, str]
        service_name: str

    class DiscoverDocsRequest(BaseModel):
        documentation: str
        service_name: str

    class SecretDefinition(BaseModel):
        """Definition of a secret that needs to be provisioned"""
        key: str = Field(..., description="Unique secret key")
        description: str = Field(..., description="Description of what this secret is for")
        source: str = Field(..., description="Source of secret (ssh, openapi, script)")
        required: bool = Field(True, description="Whether this secret is required")
        value: Optional[str] = Field(None, description="Secret value (set by user)")

    class SecretsProvisionRequest(BaseModel):
        service_name: str
        secrets: List[SecretDefinition]

    class SecretsProvisionResponse(BaseModel):
        status: str
        secrets_saved: int
        secrets_skipped: int
        errors: Optional[List[str]] = None

    class DiscoveryResponse(BaseModel):
        status: str
        actions_discovered: int
        actions: List[Dict]
        registered: bool
        summary: Dict = {}
        secrets_required: Optional[List[SecretDefinition]] = Field(None, description="Secrets that need user-provided values")
        secrets_stored: Optional[List[str]] = Field(None, description="Secrets that were auto-stored during discovery")

    # Runbook Endpoints
    @app.get("/runbook/health", response_model=RunbookHealthResponse, tags=["runbook"])
    async def runbook_health():
        """Health check for runbook orchestrator"""
        return RunbookHealthResponse(
            status="healthy" if orchestrator else "initializing",
            pathway_api="connected" if orchestrator else "unknown",
            timestamp=datetime.now().isoformat()
        )

    @app.post("/runbook/remediate", response_model=RemediationResponse, tags=["runbook"])
    async def remediate_error(request: RemediationRequest):
        """Execute automated remediation for an error"""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        try:
            logger.info(f"Received remediation request for: {request.error_message}")
            result = await orchestrator.execute_remediation(
                error_message=request.error_message,
                auto_execute_high_confidence=request.auto_execute,
                require_approval_medium=request.require_approval_medium
            )
            
            # Send notification if approval is required
            if result.get("status") == "approval_required":
                await send_approval_notification(
                    request_id=result.get("request_id"),
                    error_message=result.get("error"),
                    matched_error=result.get("best_match", result.get("matched_error", "")),
                    actions=result.get("actions", []),
                    confidence=result.get("confidence", "unknown"),
                    description=result.get("description", ""),
                    pipeline_id=None,  # Could be passed in request if needed
                    actions_requiring_individual_approval=result.get("actions_requiring_individual_approval"),
                    approval_reason=result.get("message")
                )
            
            return RemediationResponse(**result)
        except Exception as e:
            logger.error(f"Remediation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/remediate/approve", response_model=RemediationResponse, tags=["runbook"])
    async def execute_with_approval(request: ApprovalRequest):
        """
        Execute or reject approved actions for medium confidence matches
        
        This endpoint handles:
        - Request-level approval/rejection (when action_id is None)
        - Action-level approval/rejection (when action_id is specified)
        - Resuming execution after per-action approval
        
        Use this endpoint after receiving 'approval_required' status
        from /runbook/remediate endpoint
        """
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        try:
            # Handle rejection - call orchestrator method
            if not request.approved:
                logger.info(
                    f"Rejecting {'action ' + request.action_id if request.action_id else 'request'} "
                    f"{request.request_id}: {request.rejection_reason or 'No reason provided'}"
                )
                
                # Call orchestrator's reject_approval method
                result = await orchestrator.reject_approval(
                    request_id=request.request_id,
                    rejected_by=request.approved_by,
                    reason=request.rejection_reason
                )
                
                # Update notification status to rejected
                await update_notification_status(
                    request_id=request.request_id,
                    status="rejected",
                    action_taken=f"Rejected: {request.rejection_reason or 'No reason'}",
                    executed_by=request.approved_by
                )
                
                return RemediationResponse(**result)
            
            # Handle action-specific approval
            if request.action_id:
                logger.info(f"Approving action {request.action_id} in request {request.request_id}")
                result = await orchestrator.approve_action(
                    request_id=request.request_id,
                    action_id=request.action_id,
                    approved_by=request.approved_by
                )
            else:
                # Handle request-level approval
                logger.info(f"Executing approved request: {request.request_id}")
                result = await orchestrator.execute_with_approval(
                    request_id=request.request_id,
                    approved_by=request.approved_by
                )
            
            # Update notification status based on result
            if result.get("status") in ["executed", "completed"]:
                actions_executed = result.get("actions_executed", 0)
                overall_success = result.get("overall_success", False)
                status = "resolved" if overall_success else "failed"
                action_taken = f"Executed {actions_executed} action(s) - {'Success' if overall_success else 'Failed'}"
                
                await update_notification_status(
                    request_id=request.request_id,
                    status=status,
                    action_taken=action_taken,
                    executed_by=request.approved_by
                )
            
            return RemediationResponse(**result)
            
        except Exception as e:
            logger.error(f"Approval/rejection processing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/runbook/query-errors", tags=["runbook"])
    async def query_errors(error_message: str, k: int = 5):
        """Query Pathway API for matching errors without execution"""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        try:
            matches = await orchestrator.query_error_actions(error_message, k=k)
            return {
                'query': error_message,
                'matches': [
                    {
                        'error': m.error,
                        'actions': m.actions,
                        'description': m.description,
                        'distance': m.distance,
                        'confidence': m.confidence.value,
                        'is_actionable': m.is_actionable
                    }
                    for m in matches
                ]
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/runbook/approvals/pending", tags=["runbook"])
    async def list_pending_approvals():
        """List all pending approval requests"""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        try:
            pending = orchestrator.get_pending_approvals()
            return {
                'status': 'success',
                'pending_approvals': pending,
                'count': len(pending)
            }
        except Exception as e:
            logger.error(f"Failed to list pending approvals: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/runbook/approvals/{request_id}", tags=["runbook"])
    async def get_approval_status(request_id: str):
        """Get status of a specific approval request"""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
        try:
            status = orchestrator.get_approval_status(request_id)
            if not status:
                raise HTTPException(status_code=404, detail="Approval request not found")
            return {
                'status': 'success',
                'approval_request': status
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/runbook/actions", tags=["runbook"])
    async def list_actions(service: Optional[str] = None, method: Optional[str] = None, validated_only: bool = False):
        """List all actions with optional filtering"""
        if not registry:
            raise HTTPException(status_code=503, detail="Registry not initialized")
        
        try:
            if service:
                actions = await registry.get_by_service(service)
            elif method:
                actions = await registry.get_by_method(method)
            else:
                actions = await registry.list_all()
            
            if validated_only:
                actions = [a for a in actions if a.validated]
            
            return {'total': len(actions), 'actions': [a.model_dump() for a in actions]}
        except Exception as e:
            logger.error(f"Failed to list actions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/runbook/actions/{action_id}", tags=["runbook"])
    async def get_action(action_id: str):
        """Get specific action by ID"""
        if not registry:
            raise HTTPException(status_code=503, detail="Registry not initialized")
        
        try:
            action = await registry.get(action_id)
            if not action:
                raise HTTPException(status_code=404, detail="Action not found")
            return action.model_dump()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get action: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/actions/add", tags=["runbook"])
    async def add_manual_action(request: ManualActionRequest):
        """Manually add a remediation action to the registry"""
        if not registry:
            raise HTTPException(status_code=503, detail="Registry not initialized")
        
        try:
            action = RemediationAction(
                action_id=request.action_id,
                service=request.service,
                method=request.method,
                definition=request.definition,
                risk_level=request.risk_level,
                requires_approval=request.requires_approval,
                validated=False,
                execution=request.execution,
                parameters=request.parameters,
                secrets=request.secrets,
                action_metadata=request.action_metadata
            )
            await registry.save(action)
            return {'status': 'success', 'message': f'Successfully added action: {request.action_id}', 'action': action.model_dump()}
        except Exception as e:
            logger.error(f"Failed to add manual action: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/runbook/actions/{action_id}", tags=["runbook"])
    async def delete_action(action_id: str):
        """Delete a specific action by ID"""
        if not registry:
            raise HTTPException(status_code=503, detail="Registry not initialized")
        
        try:
            action = await registry.get(action_id)
            if not action:
                raise HTTPException(status_code=404, detail="Action not found")
            await registry.delete(action_id)
            return {'status': 'success', 'message': f'Successfully deleted action: {action_id}'}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete action: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/runbook/actions/{action_id}", tags=["runbook"])
    async def update_action(action_id: str, request: ManualActionRequest):
        """Update an existing action"""
        if not registry:
            raise HTTPException(status_code=503, detail="Registry not initialized")
        
        try:
            existing = await registry.get(action_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Action not found")
            
            action = RemediationAction(
                action_id=action_id,
                service=request.service,
                method=request.method,
                definition=request.definition,
                risk_level=request.risk_level,
                requires_approval=request.requires_approval,
                validated=existing.validated,
                execution=request.execution,
                parameters=request.parameters,
                secrets=request.secrets,
                action_metadata=request.action_metadata
            )
            await registry.save(action)
            return {'status': 'success', 'message': f'Successfully updated action: {action_id}', 'action': action.model_dump()}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update action: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/discover/swagger", response_model=DiscoveryResponse, tags=["runbook"])
    async def discover_from_swagger(request: DiscoverSwaggerRequest):
        """Discover remediation actions from Swagger/OpenAPI specification"""
        if not discovery_agent:
                raise HTTPException(status_code=503, detail="Discovery agent not initialized")
            
        try:
            # Fetch swagger doc if URL provided
            base_url = None
            if request.swagger_url:
                import aiohttp
                from urllib.parse import urlparse
                
                # Extract base URL from swagger_url
                parsed = urlparse(request.swagger_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(request.swagger_url) as resp:
                        if resp.status != 200:
                            raise HTTPException(status_code=400, detail="Failed to fetch Swagger spec")
                        swagger_doc = await resp.json()
            elif request.swagger_doc:
                swagger_doc = request.swagger_doc
            else:
                raise HTTPException(status_code=400, detail="Provide either swagger_url or swagger_doc")
            
            # Discover actions
            actions = await discovery_agent.discover_from_swagger(swagger_doc, request.service_name, base_url=base_url)
            
            # Try to register in database (optional)
            registered = False
            summary = {}
            if registry:
                try:
                    integration = RegistryIntegration(registry)
                    summary = await integration.register_actions(actions)
                    registered = True
                except Exception as reg_error:
                    logger.warning(f"Could not register actions in DB: {reg_error}")
            
            # Extract unique secrets that need values
            secrets_required = []
            seen_secrets = set()
            for action in actions:
                # Handle new dict structure with secret_references
                if isinstance(action.secrets, dict) and 'secret_references' in action.secrets:
                    secret_refs = action.secrets['secret_references']
                    for ref in secret_refs:
                        secret_name = ref.get('name')
                        if secret_name and secret_name not in seen_secrets:
                            seen_secrets.add(secret_name)
                            # Determine description based on secret name
                            description = f"Secret '{secret_name}' for {action.action_id}"
                            if 'api_key' in secret_name.lower():
                                description = f"API key for {action.service}"
                            elif 'token' in secret_name.lower():
                                description = f"Authentication token for {action.service}"
                            elif 'password' in secret_name.lower():
                                description = f"Password for {action.service}"
                            
                            secrets_required.append(SecretDefinition(
                                key=secret_name,
                                description=description,
                                source="openapi",
                                required=True,
                                value=None
                            ))
                # Handle legacy list structure for backward compatibility
                elif isinstance(action.secrets, list):
                    for secret_name in action.secrets:
                        if secret_name not in seen_secrets:
                            seen_secrets.add(secret_name)
                            description = f"Secret '{secret_name}' for {action.action_id}"
                            if 'api_key' in secret_name.lower():
                                description = f"API key for {action.service}"
                            elif 'token' in secret_name.lower():
                                description = f"Authentication token for {action.service}"
                            elif 'password' in secret_name.lower():
                                description = f"Password for {action.service}"
                            
                            secrets_required.append(SecretDefinition(
                                key=secret_name,
                                description=description,
                                source="openapi",
                                required=True,
                                value=None
                            ))
            
            return DiscoveryResponse(
                status="pending_secrets" if secrets_required else "completed",
                actions_discovered=len(actions),
                actions=[a.model_dump() for a in actions],
                registered=registered,
                summary=summary,
                secrets_required=secrets_required if secrets_required else None,
                secrets_stored=None  # OpenAPI doesn't auto-store secrets
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Swagger discovery failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/discover/scripts", response_model=DiscoveryResponse, tags=["runbook"])
    async def discover_from_scripts(request: DiscoverScriptsRequest):
        """
        Discover remediation actions from script files
        
        Provide list of scripts with path and content
        """
        if not discovery_agent:
            raise HTTPException(status_code=503, detail="Discovery agent not initialized")
        
        try:
            actions = await discovery_agent.discover_from_scripts(
                request.scripts,
                request.service_name
            )
            
            # Try to register in database (optional)
            registered = False
            summary = {}
            if registry:
                try:
                    integration = RegistryIntegration(registry)
                    summary = await integration.register_actions(actions)
                    registered = True
                except Exception as reg_error:
                    logger.warning(f"Could not register actions in DB: {reg_error}")
            
            # Extract unique secrets that need values
            secrets_required = []
            seen_secrets = set()
            for action in actions:
                for secret_name in action.secrets:
                    if secret_name not in seen_secrets:
                        seen_secrets.add(secret_name)
                        description = f"Secret '{secret_name}' for {action.action_id}"
                        secrets_required.append(SecretDefinition(
                            key=secret_name,
                            description=description,
                            source="script",
                            required=True,
                            value=None
                            ))
            
            return DiscoveryResponse(
                status="pending_secrets" if secrets_required else "completed",
                actions_discovered=len(actions),
                actions=[a.model_dump() for a in actions],
                registered=registered,
                summary=summary,
                secrets_required=secrets_required if secrets_required else None,
                secrets_stored=None  # Script discovery doesn't auto-store secrets
            )
        except Exception as e:
            logger.error(f"Script discovery failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/discover/ssh", response_model=DiscoveryResponse, tags=["runbook"])
    async def discover_from_ssh(request: DiscoverSSHRequest):
        """Discover remediation actions via SSH"""
        if not discovery_agent:
            raise HTTPException(status_code=503, detail="Discovery agent not initialized")
        
        try:
            # Pass secrets_manager to auto-store SSH credentials during discovery
            actions = await discovery_agent.discover_from_ssh(
                request.host,
                request.scripts_path,
                request.credentials,
                request.service_name,
                secrets_manager=secrets_manager  # Auto-store SSH credentials
            )
            
            # Try to register in database (optional)
            registered = False
            summary = {}
            if registry:
                try:
                    integration = RegistryIntegration(registry)
                    summary = await integration.register_actions(actions)
                    registered = True
                except Exception as reg_error:
                    logger.warning(f"Could not register actions in DB: {reg_error}")
            
            # Extract unique secrets that need values
            # Check the 'stored' flag in secret_references to determine which secrets need user input
            secrets_required = []
            secrets_stored = []
            seen_secrets = set()
            seen_stored = set()
            
            for action in actions:
                # Handle dict structure with secret_references
                if isinstance(action.secrets, dict) and 'secret_references' in action.secrets:
                    secret_refs = action.secrets['secret_references']
                    for ref in secret_refs:
                        secret_name = ref.get('name')
                        is_stored = ref.get('stored', False)
                        
                        if secret_name:
                            # Track stored secrets
                            if is_stored and secret_name not in seen_stored:
                                seen_stored.add(secret_name)
                                secrets_stored.append(secret_name)
                            # Only add to secrets_required if not already stored
                            elif not is_stored and secret_name not in seen_secrets:
                                seen_secrets.add(secret_name)
                                description = f"Secret '{secret_name}' for {action.action_id}"
                                
                                secrets_required.append(SecretDefinition(
                                    key=secret_name,
                                    description=description,
                                    source="ssh",
                                    required=True,
                                    value=None
                                ))
                # Handle legacy list structure for backward compatibility
                elif isinstance(action.secrets, list):
                    for secret_name in action.secrets:
                        if secret_name not in seen_secrets:
                            seen_secrets.add(secret_name)
                            description = f"Secret for {action.service}"
                            
                            secrets_required.append(SecretDefinition(
                                key=secret_name,
                                description=description,
                                source="ssh",
                                required=True,
                                value=None
                            ))
            
            return DiscoveryResponse(
                status="pending_secrets" if secrets_required else "completed",
                actions_discovered=len(actions),
                actions=[a.dict() for a in actions],
                registered=registered,
                summary=summary,
                secrets_required=secrets_required if secrets_required else None,
                secrets_stored=secrets_stored if secrets_stored else None
            )
        except Exception as e:
            logger.error(f"SSH discovery failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/runbook/discover/documentation", response_model=DiscoveryResponse, tags=["runbook"])
    async def discover_from_documentation(request: DiscoverDocsRequest):
        """Discover remediation actions from operational documentation"""
        if not discovery_agent:
            raise HTTPException(status_code=503, detail="Discovery agent not initialized")
        
        try:
            actions = await discovery_agent.discover_from_documentation(request.documentation, request.service_name)
            
            registered = False
            summary = {}
            if registry:
                try:
                    integration = RegistryIntegration(registry)
                    summary = await integration.register_actions(actions)
                    registered = True
                except Exception as reg_error:
                    logger.warning(f"Could not register actions in DB: {reg_error}")
            
            return DiscoveryResponse(
                status="completed",
                actions_discovered=len(actions),
                actions=[a.model_dump() for a in actions],
                registered=registered,
                summary=summary,
                secrets_required=None,
                secrets_stored=None  # Documentation discovery doesn't handle secrets
            )
        except Exception as e:
            logger.error(f"Documentation discovery failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/runbook/secrets/provision", response_model=SecretsProvisionResponse, tags=["runbook"])
    async def provision_secrets(request: SecretsProvisionRequest):
        """
        Provision secret values for discovered actions
        
        User provides values for secrets identified during discovery.
        Secrets are stored in the secrets manager with uniqueness enforced.
        
        Example request:
        {
            "service_name": "webapp",
            "secrets": [
                {
                    "key": "webapp_prod-server-01_ssh_host",
                    "description": "SSH host",
                    "source": "ssh",
                    "required": true,
                    "value": "prod-server-01.example.com"
                },
                {
                    "key": "webapp_prod-server-01_ssh_password",
                    "description": "SSH password",
                    "source": "ssh", 
                    "required": true,
                    "value": "secure_password_123"
                }
            ]
        }
        """
        secrets_mgr = get_secrets_manager()
        secrets_saved = 0
        secrets_skipped = 0
        errors = []
        
        try:
            for secret in request.secrets:
                # Skip if no value provided
                if secret.value is None or secret.value.strip() == "":
                    if secret.required:
                        errors.append(f"Required secret '{secret.key}' has no value")
                        secrets_skipped += 1
                    else:
                        secrets_skipped += 1
                    continue
                
                try:
                    # Store secret in database (automatically handles uniqueness)
                    secrets_mgr.set_secret(secret.key, secret.value)
                    secrets_saved += 1
                    logger.info(f"Provisioned secret: {secret.key} (source: {secret.source})")
                except Exception as e:
                    error_msg = f"Failed to save secret '{secret.key}': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    secrets_skipped += 1
            
            # Determine overall status
            if secrets_saved == len(request.secrets):
                status = "completed"
            elif secrets_saved > 0:
                status = "partial"
            else:
                status = "failed"
            
            return SecretsProvisionResponse(
                status=status,
                secrets_saved=secrets_saved,
                secrets_skipped=secrets_skipped,
                errors=errors if errors else None
            )
            
        except Exception as e:
            logger.error(f"Secrets provisioning failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
