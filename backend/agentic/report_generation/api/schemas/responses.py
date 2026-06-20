"""
Response schemas for the report generation API.
Defines the structure of successful and error responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class IncidentReportResponse(BaseModel):
    """Response containing the generated incident report."""
    success: bool = Field(..., description="Whether report generation was successful")
    report_id: str = Field(..., description="Unique identifier for the generated report")
    report_content: str = Field(..., description="Full markdown content of the report")
    severity: str = Field(..., description="Severity level of the incident")
    generated_at: datetime = Field(..., description="Timestamp when the report was generated")
    processing_time_seconds: float = Field(..., description="Time taken to generate the report")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "report_id": "report_001_critical",
                "report_content": "# Incident Report\\n\\n## Summary\\n...",
                "severity": "critical",
                "generated_at": "2024-03-15T14:35:00Z",
                "processing_time_seconds": 12.5
            }
        }


class WeeklyReportResponse(BaseModel):
    """Response containing the generated weekly summary report."""
    success: bool = Field(..., description="Whether report generation was successful")
    report_content: str = Field(..., description="Full markdown content of the weekly summary")
    start_date: str = Field(..., description="Start date of the report period (ISO format)")
    end_date: str = Field(..., description="End date of the report period (ISO format)")
    incident_count: int = Field(..., description="Number of incidents included in the summary")
    generated_at: str = Field(..., description="Timestamp when the report was generated (ISO format)")
    processing_time_seconds: float = Field(..., description="Time taken to generate the report")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "report_content": "# Weekly Summary Report\\n\\n## Overview\\n...",
                "start_date": "2024-03-10T00:00:00Z",
                "end_date": "2024-03-17T00:00:00Z",
                "incident_count": 5,
                "generated_at": "2024-03-17T10:00:00Z",
                "processing_time_seconds": 15.3
            }
        }


class ErrorResponse(BaseModel):
    """Response returned when an error occurs."""
    success: bool = Field(False, description="Always False for error responses")
    error_type: str = Field(..., description="Type of error that occurred")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_type": "ValidationError",
                "message": "Invalid request data provided",
                "details": {
                    "field": "severity",
                    "issue": "Must be one of: critical, high, medium, low"
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Current server timestamp")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-03-15T14:30:00Z",
                "version": "1.0.0"
            }
        }
