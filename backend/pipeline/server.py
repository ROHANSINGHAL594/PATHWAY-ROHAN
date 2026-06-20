import os
import json
import subprocess
from fastapi import FastAPI, Request, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List
import csv
import logging
import httpx
load_dotenv()
# if load_dotenv() below the setup_logging import, then we will need to ourself provide the env variables.
from lib.logger import custom_logger
from postgres_util import postgre_engine
from sqlalchemy import text

# Import Error Registry
try:
    from .Error_registry.error_action_registry import ErrorActionRegistry
    from .Error_registry.error_registry_models import (
        ErrorMapping,
        ErrorMappingResponse,
        BulkMappingsRequest,
        BulkMappingsResponse,
        DeleteResponse,
        SyncResponse
    )
    ERROR_REGISTRY_AVAILABLE = True
except ImportError as e:
    custom_logger.warning(f"Error Registry not available: {e}")
    ERROR_REGISTRY_AVAILABLE = False

logger = logging.getLogger(__name__)


MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "db")
WORKFLOW_COLLECTION = os.getenv("WORKFLOW_COLLECTION", "workflows")
VERSION_COLLECTION = os.getenv("VERSION_COLLECTION", "versions")

mongo_client = None
db = None
workflow_collection = None
version_collection = None
error_registry = None

PROMPTS_FILE = "prompts.csv"
FLOWCHART_FILE = os.getenv("FLOWCHART_FILE", "flowchart.json")

def create_prompts_file():
    with open(PROMPTS_FILE, "w") as f:
        f.write("")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, workflow_collection, version_collection, error_registry

    # ---- STARTUP ----
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI not set in environment")

    try:
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        db = mongo_client[MONGO_DB]
        workflow_collection = db[WORKFLOW_COLLECTION]
        version_collection = db[VERSION_COLLECTION]
        custom_logger.info(f"Connected to Database, DB: {MONGO_DB}")
    except Exception as e:
        custom_logger.error(f"Failed to connect to database: {e}")
        raise
    
    # Initialize Error Registry
    if ERROR_REGISTRY_AVAILABLE:
        try:
            logger.info("="*60)
            logger.info("Initializing Error Registry...")
            logger.info("="*60)
            
            mongodb_uri = os.getenv("MONGODB_URI", MONGO_URI)
            database_name = os.getenv("MONGODB_DATABASE", "runbook")
            local_file_path = os.getenv("ERRORS_JSON_PATH", "/app/pipeline/Error_registry/Errors.json")
            
            logger.info(f"MongoDB URI: {mongodb_uri}")
            logger.info(f"Database: {database_name}")
            logger.info(f"Local file: {local_file_path}")
            
            error_registry = ErrorActionRegistry(
                mongodb_uri=mongodb_uri,
                database_name=database_name,
                local_file_path=local_file_path
            )
            await error_registry.connect()
            logger.info("Error registry initialized and connected")
            
            # Initial sync to ensure local file is up to date
            await error_registry.force_sync()
            logger.info("Initial sync completed")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Failed to initialize error registry: {e}")
            error_registry = None

    # Hand over control to FastAPI runtime
    yield

    # ---- SHUTDOWN ----
    if error_registry:
        await error_registry.close()
        logger.info("Error registry connection closed")
    
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed.")

app = FastAPI(title="Pipeline API", lifespan=lifespan)


# ============ Pipeline Process Handling ============
pipeline_process: subprocess.Popen | None = None
pipeline_log_file = None


def stop_pipeline():
    global pipeline_process, pipeline_log_file
    if pipeline_process and pipeline_process.poll() is None:
        print("Stopping running pipeline...")
        pipeline_process.terminate()
        try:
            pipeline_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pipeline_process.kill()
    if pipeline_log_file:
        try:
            pipeline_log_file.close()
        except Exception:
            pass
        pipeline_log_file = None
    custom_logger.critical("Pipeline stopped.")
    pipeline_process = None


def run_pipeline():
    global pipeline_process, pipeline_log_file
    stop_pipeline()
    custom_logger.critical("Re-starting pipeline...")
    pipeline_log_file = open("pipeline.log", "w")
    pipeline_process = subprocess.Popen(
        ["python3", "-m", "pipeline"], 
        stdout=pipeline_log_file, 
        stderr=subprocess.STDOUT
    )


# ============ API Endpoints ============

@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Pipeline API is running"}


@app.post("/trigger")
async def trigger_pipeline(request: Request):
    """
    Webhook trigger endpoint.
    Reads the pipeline record with _id = PIPELINE_ID from MongoDB,
    saves it as FLOWCHART_FILE, and runs `python3 -m pipeline`.
    """
    pipeline_id = os.getenv("PIPELINE_ID")
    create_prompts_file()
    if not pipeline_id:
        raise HTTPException(status_code=400, detail="PIPELINE_ID not set in environment")

    # Fetch workflow and version
    workflow = await workflow_collection.find_one({"_id": ObjectId(pipeline_id)})
    if not workflow:
        raise HTTPException(status_code=404, detail=f"No workflow found with id={pipeline_id}")

    if "current_version_id" not in workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {pipeline_id} has no current_version_id")

    version = await version_collection.find_one({"_id": ObjectId(workflow["current_version_id"])})
    if not version:
        raise HTTPException(status_code=404, detail=f"No version found with id={workflow['current_version_id']}")


    # Write FLOWCHART_FILE
    with open(FLOWCHART_FILE, "w") as f:
        json.dump(version["pipeline"], f, indent=2)

    # Run pipeline
    run_pipeline()

    return {"status": "started", "id": pipeline_id}

class PromptIn(BaseModel):
    prompt: str

# Agentic container URL (set by dockerScript when spinning up containers)
AGENTIC_URL = os.getenv("AGENTIC_URL", "http://localhost:9000")

@app.post("/prompt")
async def prompt(body: PromptIn):
    file_path = PROMPTS_FILE

    # Append prompt to CSV (single column "prompts")
    with open(file_path, "a", newline="") as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(["prompt"])  # header only if file does not exist
        writer.writerow([body.prompt])

    # Call the agentic container's /infer endpoint to get AI response
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{AGENTIC_URL}/infer",
                json={"role": "user", "content": body.prompt}
            )
            
            if response.status_code == 502:
                # Workflow not built yet
                return {
                    "status": "ok",
                    "saved": body.prompt,
                    "message": "Your prompt has been saved. The AI workflow hasn't been built yet. Please configure agents in the workflow settings first."
                }
            
            response.raise_for_status()
            result = response.json()
            
            # Extract answer from agentic response
            answer = result.get("answer", {})
            if isinstance(answer, dict):
                final_answer = answer.get("answer", str(answer))
            else:
                final_answer = str(answer)
            
            return {
                "status": "ok",
                "saved": body.prompt,
                "message": final_answer
            }
            
    except httpx.ConnectError:
        custom_logger.warning(f"Could not connect to agentic container at {AGENTIC_URL}")
        return {
            "status": "ok",
            "saved": body.prompt,
            "message": "Your prompt has been saved. The AI assistant is currently unavailable. Please ensure the workflow is running."
        }
    except httpx.HTTPStatusError as e:
        custom_logger.error(f"Agentic container returned error: {e.response.status_code} - {e.response.text}")
        return {
            "status": "ok",
            "saved": body.prompt,
            "message": f"Your prompt has been saved but the AI couldn't process it: {e.response.text}"
        }
    except Exception as e:
        custom_logger.error(f"Error calling agentic container: {e}")
        return {
            "status": "ok",
            "saved": body.prompt,
            "message": f"Your prompt has been saved but an error occurred: {str(e)}"
        }


@app.post("/stop")
def stop_endpoint():
    """
    Manually stop the running pipeline.
    """
    stop_pipeline()
    return {"status": "stopped"}


class GetTable(BaseModel):
    table_name: str
    start: Optional[int] = 0
    limit: Optional[int] = 10

@app.post("/data")
def get_table(body: GetTable):
    """
    Get table data from (start) to (start + limit) with table_name
    """
    try:
        with postgre_engine.connect() as conn:
            # Get total count
            count_query = text(f"SELECT COUNT(*) FROM \"{body.table_name}\"")
            total = conn.execute(count_query).scalar()

            # Get paginated data - order by timestamp DESC for logs table
            if body.table_name == "logs":
                data_query = text(f"SELECT * FROM \"{body.table_name}\" ORDER BY timestamp DESC LIMIT :limit OFFSET :start")
            else:
                data_query = text(f"SELECT * FROM \"{body.table_name}\" LIMIT :limit OFFSET :start")
            result = conn.execute(data_query, {"limit": body.limit, "start": body.start})

            # Convert rows to list of dicts
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]

            custom_logger.debug(f"Fetched {len(rows)} rows from table {body.table_name}")
            return {
                "status": "ok",
                "table_name": body.table_name,
                "total": total,
                "start": body.start,
                "limit": body.limit,
                "has_more": (body.start + body.limit) < total,
                "data": rows
            }
    except Exception as e:
        custom_logger.error(f"Error fetching table data from {body.table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching table data: {str(e)}")


# ============ Error Registry Endpoints ============

if ERROR_REGISTRY_AVAILABLE:
    @app.post(
        "/error-registry/mappings",
        response_model=ErrorMappingResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Error-Registry"]
    )
    async def add_error_mapping(mapping: ErrorMapping):
        """
        Add or update an error-to-actions mapping.
        Automatically syncs to local Errors.json file.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            result = await error_registry.add_error_mapping(
                error=mapping.error,
                actions=mapping.actions,
                description=mapping.description
            )
            return result
        except Exception as e:
            logger.error(f"Failed to add mapping: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add mapping: {str(e)}"
            )

    @app.get(
        "/error-registry/mappings/{error}",
        response_model=ErrorMappingResponse,
        tags=["Error-Registry"]
    )
    async def get_error_mapping(error: str):
        """
        Get actions for a specific error identifier.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            mapping = await error_registry.get_error_mapping(error)
            if not mapping:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No mapping found for error: {error}"
                )
            return mapping
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get mapping: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get mapping: {str(e)}"
            )

    @app.get(
        "/error-registry/mappings",
        response_model=List[ErrorMappingResponse],
        tags=["Error-Registry"]
    )
    async def list_all_mappings():
        """
        List all error-action mappings.
        Returns all mappings sorted by error identifier.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            mappings = await error_registry.list_all_mappings()
            return mappings
        except Exception as e:
            logger.error(f"Failed to list mappings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list mappings: {str(e)}"
            )

    @app.delete(
        "/error-registry/mappings/{error}",
        response_model=DeleteResponse,
        tags=["Error-Registry"]
    )
    async def delete_error_mapping(error: str):
        """
        Delete an error mapping.
        Automatically syncs to local Errors.json file.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            deleted = await error_registry.delete_error_mapping(error)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No mapping found for error: {error}"
                )
            return {
                "success": True,
                "message": f"Successfully deleted mapping for error: {error}"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete mapping: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete mapping: {str(e)}"
            )

    @app.post(
        "/error-registry/mappings/bulk",
        response_model=BulkMappingsResponse,
        tags=["Error-Registry"]
    )
    async def bulk_add_mappings(request: BulkMappingsRequest):
        """
        Bulk add or update multiple error mappings.
        Automatically syncs to local Errors.json file after all operations.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            mappings_dicts = [mapping.model_dump() for mapping in request.mappings]
            count = await error_registry.bulk_add_mappings(mappings_dicts)
            return {
                "count": count,
                "message": f"Successfully added/updated {count} mappings"
            }
        except Exception as e:
            logger.error(f"Failed to bulk add mappings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to bulk add mappings: {str(e)}"
            )

    @app.post(
        "/error-registry/sync",
        response_model=SyncResponse,
        tags=["Error-Registry"]
    )
    async def force_sync():
        """
        Force synchronization from MongoDB to local Errors.json file.
        Use this to manually refresh the local file.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            await error_registry.force_sync()
            mappings = await error_registry.list_all_mappings()
            return {
                "success": True,
                "count": len(mappings),
                "message": f"Successfully synced {len(mappings)} mappings to Errors.json"
            }
        except Exception as e:
            logger.error(f"Failed to sync: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to sync: {str(e)}"
            )

    @app.get(
        "/error-registry/local",
        response_model=List[ErrorMappingResponse],
        tags=["Error-Registry"]
    )
    async def load_from_local_file():
        """
        Load error mappings from local Errors.json file.
        Useful for checking local file contents without querying MongoDB.
        """
        if not error_registry:
            raise HTTPException(status_code=503, detail="Error registry not initialized")
        
        try:
            mappings = error_registry.load_from_local_file()
            return mappings
        except Exception as e:
            logger.error(f"Failed to load from local file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load from local file: {str(e)}"
            )
