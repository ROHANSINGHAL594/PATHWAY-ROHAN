from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Request, Depends, Header
from pydantic import BaseModel
from .version_manager.routes import serialize_mongo
from backend.api.routers.auth.models import User
from backend.api.routers.auth.routes import get_current_user


router = APIRouter()


class RCAEvent(BaseModel):
    """Schema for RCA (Root Cause Analysis) events"""
    pipeline_id: str
    title: str
    description: Optional[str] = None
    triggered_at: Optional[datetime] = None
    trace_ids: Optional[list] = None
    metadata: Optional[Any] = None


class RCAUpdate(BaseModel):
    """Schema for updating RCA events"""
    title: Optional[str] = None
    description: Optional[str] = None
    trace_ids: Optional[list] = None
    metadata: Optional[Any] = None
    status: Optional[str] = None  # in_progress, completed, failed


@router.post("/add_rca_event")
async def add_rca_event(
    data: RCAEvent,
    request: Request,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")
):
    '''
    Route to add an RCA (Root Cause Analysis) event.
    Can only be called by an agent (via X-Agent-Token header).
    The change stream watcher will automatically send Slack notifications.
    '''
    rca_collection = request.app.state.rca_collection
    
    # Convert to dict and ensure timestamp is set
    rca_data = data.model_dump()
    if "triggered_at" not in rca_data or not rca_data["triggered_at"]:
        rca_data["triggered_at"] = datetime.now()
    
    # Initialize metadata if not present
    if not rca_data.get("metadata"):
        rca_data["metadata"] = {}
    
    # Set initial status
    if isinstance(rca_data["metadata"], dict):
        rca_data["metadata"]["status"] = rca_data["metadata"].get("status", "in_progress")
    
    # Insert RCA event into database
    # The watch_rca change stream will automatically notify via Slack
    result = await rca_collection.insert_one(rca_data)

    return serialize_mongo({
        "status": "success",
        "inserted_id": str(result.inserted_id),
        "inserted_data": rca_data
    })


@router.patch("/rca_event/{rca_id}")
async def update_rca_event(
    rca_id: str,
    data: RCAUpdate,
    request: Request,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")
):
    '''
    Update an existing RCA event.
    Used by agents to update progress, add PDF paths, etc.
    The change stream watcher will automatically send Slack notifications.
    '''
    from bson.objectid import ObjectId
    
    rca_collection = request.app.state.rca_collection
    
    try:
        rca_obj_id = ObjectId(rca_id)
    except Exception:
        return {"status": "error", "message": "Invalid RCA ID format"}
    
    # Build update dict with only provided fields
    update_data = {}
    data_dict = data.model_dump(exclude_unset=True)
    
    for key, value in data_dict.items():
        if value is not None:
            if key == "status":
                # Status goes in metadata
                update_data["metadata.status"] = value
            else:
                update_data[key] = value
    
    if not update_data:
        return {"status": "error", "message": "No update data provided"}
    
    update_data["updated_at"] = datetime.now()
    
    result = await rca_collection.update_one(
        {"_id": rca_obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        return {"status": "error", "message": "RCA event not found"}
    
    # Fetch updated document
    updated_doc = await rca_collection.find_one({"_id": rca_obj_id})
    
    return serialize_mongo({
        "status": "success",
        "message": "RCA event updated",
        "updated_data": updated_doc
    })


@router.post("/rca_event/{rca_id}/add_pdf")
async def add_pdf_to_rca(
    rca_id: str,
    request: Request,
    pdf_path: str,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token")
):
    '''
    Add a PDF report path to an RCA event.
    The PDF will be attached to the Slack notification on next update.
    '''
    from bson.objectid import ObjectId
    
    rca_collection = request.app.state.rca_collection
    
    try:
        rca_obj_id = ObjectId(rca_id)
    except Exception:
        return {"status": "error", "message": "Invalid RCA ID format"}
    
    result = await rca_collection.update_one(
        {"_id": rca_obj_id},
        {
            "$set": {
                "metadata.pdf_path": pdf_path,
                "updated_at": datetime.now()
            }
        }
    )
    
    if result.matched_count == 0:
        return {"status": "error", "message": "RCA event not found"}
    
    return serialize_mongo({
        "status": "success",
        "message": "PDF path added to RCA event",
        "pdf_path": pdf_path
    })


@router.get("/rca_events")
async def get_rca_events(
    request: Request,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50
):
    '''
    Get RCA events for the current user's workflows.
    '''
    user_id = str(current_user.id)
    workflow_collection = request.app.state.workflow_collection
    rca_collection = request.app.state.rca_collection

    query = {}
    if current_user.role != "admin":
        query = {"owner_ids": user_id}

    workflows = await workflow_collection.find(query).to_list(length=None)
    queries = [{"pipeline_id": str(pipeline["_id"])} for pipeline in workflows]

    rca_events = []
    if queries:
        rca_events = await rca_collection.find(
            {"$or": queries}
        ).sort("triggered_at", -1).skip(skip).limit(limit).to_list(length=limit)

    return serialize_mongo({
        "status": "success",
        "count": len(rca_events),
        "data": rca_events
    })


@router.get("/rca_event/{rca_id}")
async def get_rca_event(
    rca_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    '''
    Get a specific RCA event by ID.
    '''
    from bson.objectid import ObjectId
    
    rca_collection = request.app.state.rca_collection
    
    try:
        rca_obj_id = ObjectId(rca_id)
    except Exception:
        return {"status": "error", "message": "Invalid RCA ID format"}
    
    rca_event = await rca_collection.find_one({"_id": rca_obj_id})
    
    if not rca_event:
        return {"status": "error", "message": "RCA event not found"}
    
    return serialize_mongo({
        "status": "success",
        "data": rca_event
    })