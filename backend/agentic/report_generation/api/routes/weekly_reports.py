"""
Weekly report API endpoints.
Handles requests to generate weekly summary reports.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Add parent directories to path for imports
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from report_generation.api.schemas import WeeklyReportRequest, WeeklyReportResponse, ErrorResponse
from report_generation.core.weekly_generator import generate_weekly_report

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/reports", tags=["weekly-reports"])


@router.post(
    "/weekly",
    response_model=WeeklyReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        500: {"model": ErrorResponse, "description": "Report generation failed"}
    },
    summary="Generate Weekly Summary Report",
    description=(
        "Generates a weekly summary report that aggregates all incident reports "
        "from the specified date range. Queries the document store, calculates "
        "statistics, and produces an executive summary with trends and insights."
    )
)
async def create_weekly_report(request: WeeklyReportRequest):
    """
    Generate a weekly summary report for the specified date range.
    
    The report generation process:
    1. Queries document store for incidents in the date range
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
        
        # Return structured response with properly serialized dates
        return WeeklyReportResponse(
            success=True,
            report_content=report_content,
            start_date=metadata["start_date"].isoformat(),
            end_date=metadata["end_date"].isoformat(),
            incident_count=metadata["incident_count"],
            generated_at=metadata["generated_at"].isoformat(),
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
                "error_type": "ReportGenerationError",
                "message": "Failed to generate weekly report. Please check your date range and try again.",
                "details": {"error": str(e)}
            }
        )
