from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime
from backend.api.routers.auth.models import User
from backend.api.routers.auth.routes import get_current_user
from bson.objectid import ObjectId
import httpx


router = APIRouter()


async def get_workflow_container_url(request_obj: Request, pipelineId: str, current_user: User) -> tuple[str, str]:
    """
    Get the pipeline container URL for a workflow.
    Returns (ip, port) tuple.
    Raises HTTPException if workflow not found or user not authorized.
    """
    workflow_collection = request_obj.app.state.workflow_collection
    current_user_id = current_user.id
    workflow = await workflow_collection.find_one({'_id': ObjectId(pipelineId)})

    if not workflow or not workflow.get('pipeline_host_port') or not workflow.get("host_ip"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found or not spinned up")
    if str(current_user_id) not in workflow.get('owner_ids', []) and str(current_user_id) not in workflow.get('viewer_ids', []) and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to access this workflow")

    return workflow['host_ip'], workflow['pipeline_host_port']


async def get_agentic_container_url(request_obj: Request, pipelineId: str, current_user: User) -> tuple[str, str]:
    """
    Get the agentic container URL for a workflow.
    Returns (ip, port) tuple.
    Raises HTTPException if workflow not found or user not authorized.
    """
    workflow_collection = request_obj.app.state.workflow_collection
    current_user_id = current_user.id
    workflow = await workflow_collection.find_one({'_id': ObjectId(pipelineId)})

    if not workflow or not workflow.get('agentic_host_port') or not workflow.get("host_ip"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found or agentic container not running")
    if str(current_user_id) not in workflow.get('owner_ids', []) and str(current_user_id) not in workflow.get('viewer_ids', []) and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to access this workflow")

    return workflow['host_ip'], workflow['agentic_host_port']


@router.get("/{pipelineId}/{path:path}")
async def proxy_get_to_container(
    request_obj: Request, 
    path: str, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user)
):
    """
    Proxy GET requests to the pipeline container.
    Used for: /runbook/actions, /runbook/query-errors, /runbook/approvals, etc.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/{path}"
    
    # Forward query parameters
    query_params = dict(request_obj.query_params)
    
    print(f"Proxying GET to: {url} with params: {query_params}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=query_params)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


@router.post("/{pipelineId}/{path:path}")
async def proxy_post_to_container(
    request_obj: Request, 
    path: str, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user), 
    data: Dict[str, Any] = Body(default={})
):
    """
    Proxy POST requests to the pipeline container.
    Accepts any JSON body and forwards it to the container.
    Used for: /runbook/remediate, /runbook/actions/add, /runbook/discover/*, /data, etc.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/{path}"
    print(f"Proxying POST to: {url}")
    print(f"Request data: {data}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=data)
            print("Response:", response)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


@router.put("/{pipelineId}/{path:path}")
async def proxy_put_to_container(
    request_obj: Request, 
    path: str, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user), 
    data: Dict[str, Any] = Body(default={})
):
    """
    Proxy PUT requests to the pipeline container.
    Used for: /runbook/actions/{action_id} updates
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/{path}"
    print(f"Proxying PUT to: {url}")
    print(f"Request data: {data}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


@router.delete("/{pipelineId}/{path:path}")
async def proxy_delete_to_container(
    request_obj: Request, 
    path: str, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user)
):
    """
    Proxy DELETE requests to the pipeline container.
    Used for: /runbook/actions/{action_id} deletion
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/{path}"
    print(f"Proxying DELETE to: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


# ============ Agentic Container Routes (Reports) ============

agentic_router = APIRouter()


@agentic_router.get("/{pipelineId}/reports/list")
async def list_reports(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user)
):
    """
    List all available reports for a workflow.
    Proxies to the agentic container.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/api/v1/reports/list"
    
    print(f"Proxying GET to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.get("/{pipelineId}/reports/{report_id}")
async def get_report(
    request_obj: Request, 
    pipelineId: str, 
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get report content by ID.
    Proxies to the agentic container.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/api/v1/reports/{report_id}"
    
    print(f"Proxying GET to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.get("/{pipelineId}/reports/{report_id}/download")
async def download_report(
    request_obj: Request, 
    pipelineId: str, 
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download report as a markdown file.
    Proxies to the agentic container and streams the file.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/api/v1/reports/{report_id}/download"
    
    print(f"Proxying GET (download) to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            # Get filename from content-disposition header or default
            content_disposition = response.headers.get("content-disposition", "")
            filename = f"{report_id}.md"
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[-1].strip('"')
            
            return StreamingResponse(
                iter([response.content]),
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/reports/generate")
async def generate_report(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Generate a new incident report.
    Proxies to the agentic container's /api/v1/reports/incident endpoint.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/api/v1/reports/incident"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"Request data: {data}")

    async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for report generation
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


# ============ Agentic Container Routes (Actions - Runbook) ============

@agentic_router.get("/{pipelineId}/runbook/actions")
async def list_runbook_actions(
    request_obj: Request, 
    pipelineId: str, 
    service: Optional[str] = None,
    method: Optional[str] = None,
    validated_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    List all runbook actions from the agentic container.
    Used for populating action dropdowns in RunBook.jsx error catalog.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/actions"
    
    # Build query params
    params = {}
    if service:
        params['service'] = service
    if method:
        params['method'] = method
    if validated_only:
        params['validated_only'] = 'true'
    
    print(f"Proxying GET to agentic: {url} with params: {params}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.get("/{pipelineId}/runbook/actions/{action_id}")
async def get_runbook_action(
    request_obj: Request, 
    pipelineId: str, 
    action_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific runbook action by ID from the agentic container.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/actions/{action_id}"
    
    print(f"Proxying GET to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.delete("/{pipelineId}/runbook/actions/{action_id}")
async def delete_runbook_action(
    request_obj: Request, 
    pipelineId: str, 
    action_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a runbook action by ID from the agentic container.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/actions/{action_id}"
    
    print(f"Proxying DELETE to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/runbook/actions/add")
async def add_runbook_action(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Add a new runbook action to the agentic container.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/actions/add"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"Action data: {data}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/runbook/discover/swagger")
async def discover_from_swagger(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Discover actions from Swagger/OpenAPI specification.
    Proxies to the agentic container's swagger discovery endpoint.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/discover/swagger"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"Swagger discovery data: {data}")

    async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for discovery
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/runbook/discover/ssh")
async def discover_from_ssh(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Discover actions from SSH server scripts.
    Proxies to the agentic container's SSH discovery endpoint.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/discover/ssh"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"SSH discovery data: {data}")

    async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for discovery
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/runbook/discover/documentation")
async def discover_from_documentation(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Discover actions from documentation text.
    Proxies to the agentic container's documentation discovery endpoint.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/discover/documentation"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"Documentation discovery data: {data}")

    async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for discovery
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.post("/{pipelineId}/runbook/remediate/approve")
async def approve_remediation(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user),
    data: Dict[str, Any] = Body(default={})
):
    """
    Approve or reject a remediation action request.
    Handles both request-level and action-level approvals.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/remediate/approve"
    
    print(f"Proxying POST to agentic: {url}")
    print(f"Approval data: {data}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.get("/{pipelineId}/runbook/approvals/pending")
async def list_pending_approvals(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user)
):
    """
    List all pending approval requests for this pipeline.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/approvals/pending"
    
    print(f"Proxying GET to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


@agentic_router.get("/{pipelineId}/runbook/approvals/{request_id}")
async def get_approval_status(
    request_obj: Request, 
    pipelineId: str, 
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a specific approval request.
    """
    ip, port = await get_agentic_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/runbook/approvals/{request_id}"
    
    print(f"Proxying GET to agentic: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach agentic container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Agentic container error: {exc.response.text}")


# ============ Pipeline Container Routes (Error Registry) ============

@router.get("/{pipelineId}/error-registry/mappings")
async def list_error_mappings(
    request_obj: Request, 
    pipelineId: str, 
    current_user: User = Depends(get_current_user)
):
    """
    List all error-action mappings from the pipeline container's error registry.
    Used for populating the error catalog list in RunBook.jsx.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/error-registry/mappings"
    
    print(f"Proxying GET to pipeline: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


@router.get("/{pipelineId}/error-registry/mappings/{error}")
async def get_error_mapping(
    request_obj: Request, 
    pipelineId: str, 
    error: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific error mapping by error identifier from the pipeline container.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/error-registry/mappings/{error}"
    
    print(f"Proxying GET to pipeline: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


class ErrorMappingRequest(BaseModel):
    """Request model for adding/updating error mappings."""
    error: str = Field(..., description="Error identifier")
    actions: List[str] = Field(..., description="List of action IDs to execute for this error")
    description: Optional[str] = Field(None, description="Description of the error and remediation")


@router.post("/{pipelineId}/error-registry/mappings")
async def add_error_mapping(
    request_obj: Request, 
    pipelineId: str, 
    mapping: ErrorMappingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add or update an error-action mapping in the pipeline container's error registry.
    Used for creating new error catalog entries in RunBook.jsx.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/error-registry/mappings"
    
    print(f"Proxying POST to pipeline: {url}")
    print(f"Mapping data: {mapping.model_dump()}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=mapping.model_dump())
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")


@router.delete("/{pipelineId}/error-registry/mappings/{error}")
async def delete_error_mapping(
    request_obj: Request, 
    pipelineId: str, 
    error: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete an error mapping from the pipeline container's error registry.
    """
    ip, port = await get_workflow_container_url(request_obj, pipelineId, current_user)
    url = f"http://{ip}:{port}/error-registry/mappings/{error}"
    
    print(f"Proxying DELETE to pipeline: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to reach pipeline container: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Pipeline container error: {exc.response.text}")