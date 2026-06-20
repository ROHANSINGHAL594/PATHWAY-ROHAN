"""
Core report generation logic.
Contains the business logic for generating incident and weekly reports.
"""

from .report_generator import generate_incident_report
from .weekly_generator import generate_weekly_report

__all__ = ["generate_incident_report", "generate_weekly_report"]
