"""
Core incident report generation logic.
Handles the workflow execution for generating incident reports.
"""

import time
import json
import sys
from datetime import datetime
from typing import Dict, Any, Tuple
from pathlib import Path

# Add parent directories to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Import from agentic module
import llm_config
import llm_factory
from report_generation.langgraph_workflow import create_workflow, ReportState

def generate_incident_report(
    rca_output: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate an incident report using the LangGraph multi-agent workflow.
    
    Args:
        rca_output: Root cause analysis results from telemetry data analysis
        
    Returns:
        Tuple of (report_content, metadata) where metadata includes:
            - report_id: Unique identifier for the report
            - filepath: Location where report was saved
            - severity: Severity level of the incident
            - execution_time: Time taken to generate report
            - incident_id: Auto-generated ID
            
    Raises:
        ValueError: If required LLM configuration is missing
        Exception: If workflow execution fails
    """
    # Create LLM models using the unified factory
    # Planner and ChartGen use agent models, Drafter uses reasoning
    try:
        agent_model = llm_factory.create_agent_model()
        reasoning_model = llm_factory.create_reasoning_model()
    except Exception as e:
        raise ValueError(
            f"Failed to create LLM models from factory: {str(e)}. "
            "Ensure API keys are set in backend/agentic/.env"
        )
    
    # Prepare diagnostic data structure expected by workflow (only RCA output)
    diagnostic_data = {
        "rca_output": rca_output
    }
    
    # Initialize workflow with LLM models from factory
    workflow = create_workflow(agent_model, reasoning_model)
    
    # Initialize state for the multi-agent workflow
    initial_state: ReportState = {
        "diagnostic_data": diagnostic_data,
        "report_plan": {},
        "matched_rules": [],
        "chart_data": [],
        "charts": [],
        "final_report": "",
        "execution_time": 0.0,
        "error": ""
    }
    
    # Execute the workflow (Planner -> Rules/Charts -> ChartGen -> Drafter)
    start_time = time.time()
    final_state = workflow.invoke(initial_state)
    execution_time = time.time() - start_time
    
    # Check for workflow errors
    if final_state.get("error"):
        raise Exception(f"Workflow execution failed: {final_state['error']}")
    
    report_content = final_state["final_report"]
    
    # Extract metadata from RCA output (new RCAAnalysisOutput structure)
    severity = rca_output.get("severity", "UNKNOWN").lower()
    affected_services = rca_output.get("affected_services", [])
    primary_service = affected_services[0] if affected_services else "unknown"
    
    # Generate incident_id from timestamp and primary service
    current_time = datetime.now()
    incident_timestamp = current_time.strftime("%Y%m%d_%H%M%S")
    incident_id = f"INC-{incident_timestamp}-{primary_service}"
    
    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Create filename with severity and incident ID
    filename = f"incident_{incident_timestamp}_{severity}.md"
    filepath = reports_dir / filename
    
    # Save report to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    # Save metadata to JSON file
    metadata_file = reports_dir / f"incident_{incident_timestamp}_{severity}.json"
    report_metadata = {
        "incident_id": incident_id,
        "severity": severity,
        "primary_service": primary_service,
        "affected_services": affected_services,
        "timestamp": current_time.isoformat(),
        "execution_time": execution_time,
        "filename": filename,
        "filepath": str(filepath)
    }

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(report_metadata, f, indent=2)

    # Return metadata for API response
    metadata = {
        "report_id": filename.replace(".md", ""),
        "incident_id": incident_id,
        "severity": severity,
        "filepath": str(filepath),
        "execution_time": execution_time,
        "generated_at": current_time
    }
    return report_content, metadata
