from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Admin API", description="Simulates admin actions like restart, troubleshoot, etc.")

class ServiceActionRequest(BaseModel):
    service_name: str
    details: Optional[str] = None

@app.get("/")
def root():
    return {"message": "Mock Admin API is running."}

@app.post("/restart_service")
def restart_service(req: ServiceActionRequest):
    return {"status": "success", "action": "restart", "service": req.service_name, "details": req.details or "Service restarted successfully."}

@app.post("/troubleshoot_service")
def troubleshoot_service(req: ServiceActionRequest):
    return {"status": "success", "action": "troubleshoot", "service": req.service_name, "details": req.details or "Troubleshooting completed. No issues found."}

@app.post("/update_service")
def update_service(req: ServiceActionRequest):
    return {"status": "success", "action": "update", "service": req.service_name, "details": req.details or "Service updated to latest version."}

@app.post("/status_service")
def status_service(req: ServiceActionRequest):
    return {"status": "success", "action": "status", "service": req.service_name, "details": req.details or "Service is running smoothly."}

@app.post("/simulate_error")
def simulate_error(req: ServiceActionRequest):
    return {"status": "error", "action": "simulate_error", "service": req.service_name, "details": req.details or "Simulated error occurred."}

# To run: uvicorn mock_admin_api:app --host 0.0.0.0 --port 9000