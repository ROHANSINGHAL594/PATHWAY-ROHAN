import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

from .error_action_registry import ErrorActionRegistry

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global registry instance
registry: Optional[ErrorActionRegistry] = None


class ErrorMapping(BaseModel):
    """Model for error-action mapping"""
    error: str = Field(..., description="Error identifier/pattern")
    actions: List[str] = Field(..., description="Ordered list of action IDs to execute")
    description: str = Field(..., description="Human-readable description of the error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "DatabaseConnectionTimeout",
                "actions": ["check-db-health", "restart-db-connection-pool", "restart-db-service"],
                "description": "Database connection pool exhausted or database is unresponsive"
            }
        }


class ErrorMappingResponse(ErrorMapping):
    """Response model with additional metadata"""
    pass


class BulkMappingsRequest(BaseModel):
    """Request model for bulk adding mappings"""
    mappings: List[ErrorMapping] = Field(..., description="List of error mappings to add")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mappings": [
                    {
                        "error": "HighMemoryUsage",
                        "actions": ["clear-cache", "restart-service", "scale-up-instances"],
                        "description": "Service memory usage exceeded 90% threshold"
                    },
                    {
                        "error": "DiskSpaceFull",
                        "actions": ["clear-temp-files", "archive-old-logs", "expand-disk-volume"],
                        "description": "Disk usage at 95%, no space left on device"
                    }
                ]
            }
        }


class BulkMappingsResponse(BaseModel):
    """Response model for bulk operations"""
    count: int = Field(..., description="Number of mappings added/updated")
    message: str = Field(..., description="Operation result message")


class DeleteResponse(BaseModel):
    """Response model for delete operations"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Operation result message")


class SyncResponse(BaseModel):
    """Response model for sync operations"""
    success: bool = Field(..., description="Whether sync was successful")
    count: int = Field(..., description="Number of mappings synced")
    message: str = Field(..., description="Operation result message")

