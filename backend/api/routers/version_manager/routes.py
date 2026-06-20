from fastapi import APIRouter, Depends, HTTPException, Request, status
from bson.objectid import ObjectId
from ..auth.routes import get_current_user
from ..auth.models import User
from datetime import datetime
from typing import List
import logging
from .schema import save_workflow_payload, retrieve_payload, save_draft_payload, add_viewer_payload, remove_viewer_payload, create_pipeline_with_details_payload
from .crud import create_workflow as _create_workflow
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..auth.database import get_db


logger = logging.getLogger(__name__)
router = APIRouter()

def serialize_mongo(doc):
    if isinstance(doc, ObjectId):
        return str(doc)
    
    if isinstance(doc, datetime):
        return doc.isoformat()

    if isinstance(doc, list):
        return [serialize_mongo(x) for x in doc]

    if isinstance(doc, dict):
        return {k: serialize_mongo(v) for k, v in doc.items()}

    return doc


#----------------------------------Create workflow------------------------------------#


@router.post("/create_pipeline")
async def create_workflow(
    name:str,
    request:Request,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new workflow
    """

    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    mongo_client = request.app.state.mongo_client
    try:            
        user_identifier = str(current_user.id)
        new_workflow = await _create_workflow(name,user_identifier,version_collection,workflow_collection,mongo_client)
        return {
            "message": "Workflow created successfully",
            "id": str(new_workflow["_id"]),
            "user_id": user_identifier,
            "current_version_id": new_workflow["current_version_id"]
        }
    except Exception as e:
        logger.error(f"Create Workflow error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/create_pipeline_with_details",
    tags=["version"],
    summary="Create pipeline with details",
    description="Create a new pipeline with name, description, viewer IDs, and nodes setup. This combines pipeline creation and saving in a single operation."
)
async def create_pipeline_with_details(
    request: Request,
    payload: create_pipeline_with_details_payload,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new pipeline with all details including name, description, viewers, and nodes setup.
    This endpoint combines the functionality of create_pipeline and save in a single operation.
    """
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    mongo_client = request.app.state.mongo_client
    
    try:
        user_identifier = str(current_user.id)
        
        # Prepare pipeline document from payload
        pipeline_doc = {
            "edges": payload.pipeline.get("edges", []),
            "nodes": payload.pipeline.get("nodes", []),
            "viewport": payload.pipeline.get("viewport", {
                "x": 0,
                "y": 0,
                "zoom": 1
            })
        }
        
        # Create version document
        version_doc = {
            "version_description": payload.description or "",
            "user_id": user_identifier,
            "version_created_at": datetime.now(),
            "version_updated_at": datetime.now(),
            "pipeline": pipeline_doc
        }
        
        # Create workflow document (matching structure from create_workflow in crud.py)
        workflow_doc = {
            "owner_ids": [user_identifier],
            "viewer_ids": payload.viewer_ids or [],
            "name": payload.name or None,  # Store workflow name
            "start_Date": None,
            "status": "Stopped",
            "container_id": "",
            "agent_container_id": "",
            "agent_port": "",
            "agent_ip": "",
            "notification": [],
            "pipeline_host_port": "",
            "agentic_host_port": "",
            "db_host_port": "",
            "host_ip": "",
            "versions": [],
            "last_started": None,
            "runtime": 0
        }
        
        # Use transaction to ensure atomicity
        async with await mongo_client.start_session() as session:
            async with session.start_transaction():
                # Insert version first
                version = await version_collection.insert_one(version_doc, session=session)
                version_doc["_id"] = version.inserted_id
                
                # Update workflow with version info
                workflow_doc["versions"] = [str(version.inserted_id)]
                workflow_doc["current_version_id"] = str(version.inserted_id)
                workflow_doc["last_updated"] = datetime.now()
                
                # Insert workflow
                result = await workflow_collection.insert_one(workflow_doc, session=session)
                workflow_doc["_id"] = result.inserted_id
                
                # Commit transaction
                await session.commit_transaction()
        
        return {
            "status": "success",
            "message": "Pipeline created successfully",
            "pipeline_id": str(workflow_doc["_id"]),
            "version_id": str(version.inserted_id),
            "user_id": user_identifier,
            "viewer_ids": payload.viewer_ids
        }
        
    except Exception as e:
        logger.error(f"Create pipeline with details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pipeline: {str(e)}"
        )



#-----------------------------------   Save workflow and Drafts     ----------------------------------------#


@router.post("/save")
async def save_workflow(
    request:Request,
    payload: save_workflow_payload,
    current_user: User = Depends(get_current_user)
):
    """
    Saves a version to the database
    """

    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    mongo_client = request.app.state.mongo_client

    try:
        user_identifier = str(current_user.id)
        workflow_query = {"_id": ObjectId(payload.workflow_id)}
        version_query = {"_id": ObjectId(payload.current_version_id)}

        try:
            (ObjectId(payload.workflow_id) is None)
            (ObjectId(payload.current_version_id) is None)
        except:
            raise HTTPException(status_code=404, detail="Workflow or Version not found")

        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in": [user_identifier]}

        existing_version = await version_collection.find_one({"_id": ObjectId(payload.current_version_id)})
        existing_workflow = await workflow_collection.find_one({"_id": ObjectId(payload.workflow_id)})

        if not existing_version or not existing_workflow:
            raise HTTPException(status_code=404, detail="Version or workflow not found")

        async with await mongo_client.start_session() as session:
            async with session.start_transaction():
                update_result = await version_collection.update_one(
                    version_query,
                    {
                        '$set': {
                            "version_description": payload.version_description,
                            "version_updated_at": payload.version_updated_at,
                            "pipeline": payload.pipeline,
                        }
                    },
                    session=session
                )

                if update_result.modified_count == 0 and update_result.matched_count == 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not authorzed to save the workflow."
                    )

                new_version = await version_collection.insert_one(
                    {
                        "user_id": user_identifier,
                        "version_description": payload.version_description,
                        "version_created_at": datetime.now(),
                        "version_updated_at": datetime.now(),
                        "pipeline": payload.pipeline,
                    },
                    session=session
                )

                if not new_version.inserted_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Error updating Workflow"
                    )

                # Build workflow update operations
                workflow_set_ops = {"current_version_id": str(new_version.inserted_id)}
                
                # Optionally update viewer_ids if provided
                if payload.viewer_ids is not None:
                    workflow_set_ops["viewer_ids"] = payload.viewer_ids

                workflow_update_result = await workflow_collection.update_one(
                    workflow_query,
                    {   
                        '$set': workflow_set_ops,
                        "$push": {"versions": str(new_version.inserted_id)}
                    },
                    session=session
                )

                if workflow_update_result.modified_count == 0 and workflow_update_result.matched_count == 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not authorzed to save the workflow."
                    )

        return {
            "message": "Updated successfully",
            "version_id": str(new_version.inserted_id),
            "workflow_id": str(payload.workflow_id),
            "user_id": user_identifier
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating workflow: {str(e)}"
        )

@router.post("/save_draft")
async def save_draft(
    request:Request,
    payload: save_draft_payload,
    current_user: User = Depends(get_current_user)
):
    """
    save the draft to the database
    """

    version_collection = request.app.state.version_collection
    workflow_collection = request.app.state.workflow_collection
    try: 
        current_version_id = payload.version_id
        pipeline=payload.pipeline
        workflow_id=payload.pipeline_id
        version_description= payload.version_description
        user_identifier = str(current_user.id)
        try:
            (ObjectId(current_version_id) is None)
            (ObjectId(workflow_id) is None)
        except:
            raise HTTPException(status_code=404, detail="Workflow or Version not found")

        workflow_query = {"_id": ObjectId(workflow_id)}
        version_query = {"_id": ObjectId(current_version_id)}
        existing_version = await version_collection.find_one({"_id": ObjectId(current_version_id)})
        existing_workflow = await workflow_collection.find_one({"_id":ObjectId(workflow_id)})

        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in":user_identifier}
            version_query["user_id"] = user_identifier

        if not existing_version or not existing_workflow:
            raise HTTPException(status_code=404, detail="Version or pipeline not found")
        
        # Check authorization: user must be version creator, workflow owner, or admin
        is_version_creator = existing_version.get("user_id") == user_identifier
        is_workflow_owner = user_identifier in existing_workflow.get("owner_ids", [])
        is_admin = current_user.role == "admin"
        
        if not (is_version_creator or is_workflow_owner or is_admin):
            raise HTTPException(status_code=403, detail="You are not authorised to Edit the workflow")

        result = await version_collection.update_one(
            version_query,
            {
                '$set': {
                    "version_description": version_description,
                    "version_updated_at": datetime.now(),
                    "pipeline": pipeline,
                }

            })

        return {
                "message": "Draft saved successfully",
                "id": current_version_id,
                "user_id": user_identifier,
                "version": str(result)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating version: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

#---------------------------------    Retrieve workflow and Drafts--------------------------------------#

@router.post("/retrieve_pipeline")
async def retrieve_workflow(
    request:Request,
    payload: retrieve_payload,
    current_user: User = Depends(get_current_user)
):

    """

    Retrieve a workflow from the database
    """
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    workflow_id = payload.workflow_id
    version_id = payload.version_id
    role = current_user.role

    try:
        try:
            (ObjectId(workflow_id) is None)
            (ObjectId(version_id) is None)
        except:
            raise HTTPException(status_code=404, detail="Workflow or Version not found")
        user_identifier = str(current_user.id)
        existing_version = await version_collection.find_one({"_id": ObjectId(version_id)})
        existing_workflow = await workflow_collection.find_one({"_id": ObjectId(workflow_id)})

        if not existing_version or not existing_workflow:
            raise HTTPException(status_code=404, detail="Version or workflow not found")

        if( role=="admin" or user_identifier in existing_workflow["owner_ids"] or user_identifier in existing_workflow["viewer_ids"]):
            return {
                "message": "Pipeline data retrieved successfully",
                "workflow": serialize_mongo(existing_workflow),
                "version": serialize_mongo(existing_version)
            }
        else:
            raise HTTPException(status_code=403, detail="You are not authorised to access the pipeline")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrieve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#retrieve version was redundant as retrieve workflow uses version id and i can get the draft version from current version id and the workflow to be used form the workflow collection

@router.get("/retrieve_all")
async def retrieve_all(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = None
):

    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection

    query = {}
    if current_user.role != "admin":
        query = {"owner_ids": str(current_user.id)}

    cursor = workflow_collection.find(query).sort("last_updated", -1).skip(skip)

    if limit is not None:
        cursor = cursor.limit(limit)
        workflows = await cursor.to_list(length=limit)
    else:
        workflows = await cursor.to_list(length=None)

    current_user_id = str(current_user.id)

    for wf in workflows:
        version_ids = wf.get("versions", [])
        owner_ids = wf.get("owner_ids", [])

        # ===== FETCH USER-SPECIFIC VERSION ===== #
        if version_ids:
            object_ids = [ObjectId(v_id) for v_id in version_ids]
            user_version = await version_collection.find_one({
                "_id": {"$in": object_ids},
                "user_id": current_user_id
            })

            if not user_version and wf.get("current_version_id"):
                user_version = await version_collection.find_one({
                    "_id": ObjectId(wf["current_version_id"])
                })

            wf["user_pipeline_version"] = user_version

        # # ===== FETCH OWNERS FROM POSTGRES (NO PRIVACY RISK) ===== #
            if owner_ids:
                # Convert string IDs to integers
                owner_ids_int = [int(uid) for uid in owner_ids]

                stmt = select(User).where(User.id.in_(owner_ids_int))
                users = (await db.execute(stmt)).scalars().all()

                wf["owners"] = [
                    {
                        "id": str(u.id),
                        "display_name": u.full_name,
                        "initials": "".join([x[0].upper() for x in u.full_name.split()[:2]])
                    }
                    for u in users
                ]


    return serialize_mongo({
        "status": "success",
        "count": len(workflows),
        "data": workflows
    })


@router.get("/pipeline/{pipeline_id}/details")
async def get_pipeline_details(
    request: Request,
    pipeline_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get pipeline details including creation time and alerts
    """
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    notification_collection = request.app.state.notification_collection
    
    try:
        workflow = await workflow_collection.find_one({"_id": ObjectId(pipeline_id)})
        if not workflow:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Check authorization
        user_identifier = str(current_user.id)
        if current_user.role != "admin":
            if user_identifier not in workflow.get("owner_ids", []) and user_identifier not in workflow.get("viewer_ids", []):
                raise HTTPException(status_code=403, detail="Not authorized to access this pipeline")
        
        # Get first version_created_at (pipeline creation time)
        version_ids = workflow.get("versions", [])
        first_version_created_at = None
        
        if version_ids:
            # Get the first version (oldest)
            first_version_id = version_ids[0]
            first_version = await version_collection.find_one({"_id": ObjectId(first_version_id)})
            if first_version:
                first_version_created_at = first_version.get("version_created_at")
        
        # If no first version, use current version
        if not first_version_created_at and workflow.get("current_version_id"):
            current_version = await version_collection.find_one({"_id": ObjectId(workflow["current_version_id"])})
            if current_version:
                first_version_created_at = current_version.get("version_created_at")
        
        # Get all alerts/notifications for this pipeline
        alerts = await notification_collection.find({
            "pipeline_id": pipeline_id,
            "type": "alert"
        }).to_list(length=None)
        
        return serialize_mongo({
            "status": "success",
            "pipeline_id": pipeline_id,
            "created_at": first_version_created_at,
            "alerts": alerts,
            "alerts_count": len(alerts)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pipeline details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#---------------------------- Delete workflow and Drafts--------------------------#
@router.post("/delete_pipeline")
async def delete_workflow(
    request:Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    
    """
    Delete a workflow from the database
    """
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    mongo_client = request.app.state.mongo_client

    try:
        user_identifier = str(current_user.id)
        try:
            (ObjectId(workflow_id) is None)
        except:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow_query = {"_id": ObjectId(workflow_id)}

        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in": [user_identifier]}
        existing_workflow = await workflow_collection.find_one({"_id": ObjectId(workflow_id)})

        if not existing_workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        
        if  not ((user_identifier in existing_workflow.get("owner_ids")) or (current_user.role=="admin")):
            raise HTTPException(status_code=403, detail="You are not authorised to delete the pipeline")
        
        if existing_workflow.get("container_id"):
            raise HTTPException(status_code=409, detail="workflow running, Stop and Spin down the workflow to delete the Workflow")
        
        async with await mongo_client.start_session() as session:
            async with session.start_transaction(): 

                for version_id in existing_workflow.get('versions', []):
                    await version_collection.delete_one(
                        {'_id': ObjectId(version_id)},
                        session=session)

                workflow = await workflow_collection.delete_one(
                    workflow_query, 
                    session=session)
                
                if workflow.deleted_count == 0:
                    raise HTTPException(status_code=404, detail="workflow not found or not authorized")

        return {
            "message": "workflow deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/delete_draft")
async def delete_draft(
    request:Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    mongo_client = request.app.state.mongo_client
    try:
        
        user_identifier = str(current_user.id)
        try:
            (ObjectId(workflow_id) is None)
        except:
            raise HTTPException(status_code=404, detail="Workflow not found")
        workflow_query = {"_id": ObjectId(workflow_id)}
        existing_workflow = await workflow_collection.find_one(workflow_query)

        if not existing_workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if not (user_identifier in existing_workflow["owner_ids"] or current_user.role == "admin"):
            raise HTTPException(status_code=403, detail="You are not authorised to Delete the Edits")

        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in": [user_identifier]}
        
        async with await mongo_client.start_session() as session:
            async with session.start_transaction():
                pipeline={
                    "edges": [],
                    "nodes": [],
                    "viewport": {
                        "x": 0,
                        "y": 0,
                        "zoom": 1
                    }
                }
                version_description = ""
                pipeline_doc = {
                    "edges": [],
                    "nodes": [],
                    "viewport": {
                        "x": 0,
                        "y": 0,
                        "zoom": 1
                    }
                }
                previous_version= {
                        "version_description": "",
                        "user_id": user_identifier,
                        "version_created_at": datetime.now(),
                        "version_updated_at": datetime.now(),
                        "pipeline": pipeline_doc
                    }
                current_version_id = existing_workflow.get("current_version_id")
                if(len(existing_workflow.get("versions"))!=1):
                    previous_version_id = existing_workflow.get("versions")[-2]
                    previous_version = await version_collection.find_one(
                        {"_id": ObjectId(previous_version_id)},
                        session=session
                    )
                    pipeline=previous_version.get("pipeline")
                    version_description=previous_version.get("version_description")
                updated_result = await version_collection.update_one(
                    {"_id": ObjectId(str(current_version_id))},
                    {
                        '$set': {
                            "version_description": version_description,
                            "version_updated_at": datetime.now(),
                            "pipeline": pipeline,
                        }
                    },
                    session=session
                )

                if updated_result.matched_count == 0:
                    raise HTTPException(404, "Version not found")

        return serialize_mongo({
            "version_id": current_version_id,
            "version": previous_version
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting draft: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/retrieve_versions")
async def retrieve_versions(
    request: Request,
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    workflow_collection = request.app.state.workflow_collection
    version_collection = request.app.state.version_collection
    try:
        user_identifier = str(current_user.id)
        workflow_query = {"_id": ObjectId(workflow_id)}
        existing_workflow = await workflow_collection.find_one(workflow_query)

        if not existing_workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if not (user_identifier in existing_workflow["owner_ids"] or current_user.role == "admin"):
            raise HTTPException(status_code=403, detail="You are not authorised to view the versions")

        version_ids = existing_workflow.get("versions", [])

        version_data = []
        for version_id in version_ids:
            version = await version_collection.find_one({"_id": ObjectId(version_id)})
            if not version:
                raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
            version_data.append({'date': version.get("version_created_at"), 'user': version.get("user_id"), 'version_id': str(version.get("_id")), 'description': version.get("version_description")})

        return [version_data[-5::][::-1], len(version_data)]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving versions: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

#---------------------------- Add Viewer to Pipeline --------------------------#
@router.post(
    "/add_viewer",
    tags=["version"],
    summary="Add viewer to pipeline",
    description="Add a user as a viewer to a pipeline. Only pipeline owners or admins can add viewers. The user must not already be an owner or viewer of the pipeline."
)
async def add_viewer_to_pipeline(
    request: Request,
    payload: add_viewer_payload,
    current_user: User = Depends(get_current_user)
):
    """
    Add a viewer to a pipeline.
    Only pipeline owners or admins can add viewers.
    """
    workflow_collection = request.app.state.workflow_collection
    
    try:
        user_identifier = str(current_user.id)
        pipeline_id = payload.pipeline_id
        viewer_user_id = payload.user_id
        
        # Validate pipeline_id format
        try:
            pipeline_object_id = ObjectId(pipeline_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid pipeline_id format")
        
        # Find the workflow
        workflow_query = {"_id": pipeline_object_id}
        
        # If not admin, check if user is owner
        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in": [user_identifier]}
        
        existing_workflow = await workflow_collection.find_one(workflow_query)
        
        if not existing_workflow:
            raise HTTPException(
                status_code=404,
                detail="Pipeline not found or you don't have permission to modify it"
            )
        
        # Check if viewer is already in the list
        viewer_ids = existing_workflow.get("viewer_ids", [])
        if viewer_user_id in viewer_ids:
            raise HTTPException(
                status_code=400,
                detail="User is already a viewer of this pipeline"
            )
        
        # Check if viewer is already an owner
        owner_ids = existing_workflow.get("owner_ids", [])
        if viewer_user_id in owner_ids:
            raise HTTPException(
                status_code=400,
                detail="User is already an owner of this pipeline"
            )
        
        # Add viewer to the pipeline
        update_result = await workflow_collection.update_one(
            {"_id": pipeline_object_id},
            {
                "$addToSet": {"viewer_ids": viewer_user_id}
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to add viewer to pipeline"
            )
        
        return {
            "status": "success",
            "message": "Viewer added successfully",
            "pipeline_id": pipeline_id,
            "viewer_id": viewer_user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding viewer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add viewer: {str(e)}")


#---------------------------- Remove Viewer from Pipeline --------------------------#
@router.post(
    "/remove_viewer",
    tags=["version"],
    summary="Remove viewer from pipeline",
    description="Remove a user as a viewer from a pipeline. Only pipeline owners or admins can remove viewers."
)
async def remove_viewer_from_pipeline(
    request: Request,
    payload: remove_viewer_payload,
    current_user: User = Depends(get_current_user)
):
    """
    Remove a viewer from a pipeline.
    Only pipeline owners or admins can remove viewers.
    """
    workflow_collection = request.app.state.workflow_collection
    
    try:
        user_identifier = str(current_user.id)
        pipeline_id = payload.pipeline_id
        viewer_user_id = payload.user_id
        
        # Validate pipeline_id format
        try:
            pipeline_object_id = ObjectId(pipeline_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid pipeline_id format")
        
        # Find the workflow
        workflow_query = {"_id": pipeline_object_id}
        
        # If not admin, check if user is owner
        if current_user.role != "admin":
            workflow_query["owner_ids"] = {"$in": [user_identifier]}
        
        existing_workflow = await workflow_collection.find_one(workflow_query)
        
        if not existing_workflow:
            raise HTTPException(
                status_code=404,
                detail="Pipeline not found or you don't have permission to modify it"
            )
        
        # Check if viewer is in the list
        viewer_ids = existing_workflow.get("viewer_ids", [])
        if viewer_user_id not in viewer_ids:
            raise HTTPException(
                status_code=400,
                detail="User is not a viewer of this pipeline"
            )
        
        # Remove viewer from the pipeline
        update_result = await workflow_collection.update_one(
            {"_id": pipeline_object_id},
            {
                "$pull": {"viewer_ids": viewer_user_id}
            }
        )
        
        if update_result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to remove viewer from pipeline"
            )
        
        return {
            "status": "success",
            "message": "Viewer removed successfully",
            "pipeline_id": pipeline_id,
            "viewer_id": viewer_user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing viewer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove viewer: {str(e)}")
