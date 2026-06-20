"""
Incident report API endpoints.
Handles requests to generate incident reports from RCA output.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Add parent directories to path for imports
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from report_generation.api.schemas import IncidentReportRequest, IncidentReportResponse, ErrorResponse
from report_generation.core.report_generator import generate_incident_report

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/reports", tags=["incident-reports"])


@router.post(
    "/incident",
    response_model=IncidentReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Report generation failed"}
    },
    summary="Generate Incident Report",
    description=(
        "Generates a detailed incident report using the LangGraph multi-agent workflow. "
        "Takes pipeline topology and RCA output as input and produces a comprehensive "
        "markdown report with analysis, charts, and recommendations."
    )
)
async def create_incident_report(request: IncidentReportRequest):
    """
    Generate an incident report from pipeline topology and RCA output.
    
    The report generation process:
    1. Validates input data structure
    2. Executes multi-agent workflow (Planner -> ChartGen -> Drafter)
    3. Saves and indexes the report in the document store
    4. Returns the complete report with metadata
    
    Expected processing time: 8-15 seconds depending on incident complexity.
    """
    start_time = datetime.now()
    
    try:
        # Get primary affected service for logging
        primary_service = (request.rca_output.affected_services[0] 
                          if request.rca_output.affected_services 
                          else "unknown")
        
        logger.info(
            f"Received incident report request for service: {primary_service} "
            f"(severity: {request.rca_output.severity})"
        )
        
        # Convert Pydantic model to dictionary for the core logic
        # Use mode='json' to serialize datetime objects to ISO strings
        rca_output = request.rca_output.model_dump(mode='json')
        
        # Generate the report using core business logic (telemetry-based RCA only)
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
