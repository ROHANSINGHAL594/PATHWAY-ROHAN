"""
State definition for LangGraph workflow
"""

from typing import Dict, Any, List
from typing_extensions import TypedDict


class ReportState(TypedDict):
    """
    State object passed through the LangGraph workflow.
    Each node reads from and writes to this state.
    """
    
    # Inputs
    diagnostic_data: Dict[str, Any]
    
    # Planner outputs
    report_plan: Dict[str, Any]
    
    # Rule matching output
    matched_rules: List[Dict[str, Any]]
    
    # Chart generation
    chart_data: List[Dict[str, Any]]
    charts: List[Dict[str, str]]
    
    # Final output
    final_report: str
    
    # Metadata
    execution_time: float
    error: str
