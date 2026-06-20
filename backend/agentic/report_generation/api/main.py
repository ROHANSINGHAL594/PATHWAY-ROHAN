"""
FastAPI application entry point.
Configures and runs the report generation API service.
"""

import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directories to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import from report_generation package
from report_generation.api.routes import incident_reports, weekly_reports
from report_generation.api.schemas import HealthCheckResponse

# Load environment variables from backend/agentic/.env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configure basic console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Report Generation API",
    description=(
        "REST API for generating incident reports and weekly summaries "
        "using LangGraph multi-agent workflow and LLM analysis. "
        "Now with span topology visualization and financial impact tracking."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Register route handlers
app.include_router(incident_reports.router)
app.include_router(weekly_reports.router)


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health Check",
    description="Check if the API service is running and healthy."
)
async def health_check():
    """
    Health check endpoint to verify service availability.
    Returns basic service status and version information.
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="2.0.0"
    )


@app.get(
    "/",
    tags=["info"],
    summary="API Information",
    description="Get basic information about the API service."
)
async def root():
    """
    Root endpoint providing API information and navigation.
    """
    return {
        "service": "Report Generation API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Span topology visualization with mermaid diagrams",
            "Financial impact tracking (demo values)",
            "Multi-agent LangGraph workflow",
            "Comprehensive incident reports"
        ],
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "incident_reports": "/api/v1/reports/incident",
            "weekly_reports": "/api/v1/reports/weekly"
        }
    }


# Startup and shutdown event handlers
@app.on_event("startup")
async def startup_event():
    """
    Execute tasks on application startup.
    """
    logger.info("=" * 60)
    logger.info("Starting Report Generation API v2.0")
    logger.info("Features: Span Topology + Financial Impact Tracking")
    logger.info("=" * 60)
    logger.info("Server running on http://0.0.0.0:8085")
    logger.info("Swagger UI: http://localhost:8085/docs")
    logger.info("ReDoc: http://localhost:8085/redoc")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute cleanup tasks on application shutdown.
    """
    logger.info("Shutting down Report Generation API")


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8085,
        reload=True,
        log_level="info"
    )
