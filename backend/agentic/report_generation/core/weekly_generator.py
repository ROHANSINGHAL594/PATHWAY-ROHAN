"""
Core weekly report generation logic.
Handles the workflow for generating weekly summary reports.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from collections import Counter

# Add parent directories to path for imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Import from agentic module
import llm_factory
from report_generation.agents.weekly_summarizer_agent import WeeklySummarizerAgent

logger = logging.getLogger(__name__)


def parse_incident_report(report_content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a markdown incident report and extract structured data.
    
    Note: Reports are generated from RCAAnalysisOutput which includes:
    - severity, affected_services, narrative, error_citations, root_cause
    
    Args:
        report_content: Full markdown content of the incident report
        metadata: Basic metadata (incident_id, severity, timestamp, affected_node)
        
    Returns:
        Dictionary with structured incident data including root cause, 
        affected components (services), resolution steps, and impact
    """
    incident_data = {
        "incident_id": metadata.get("incident_id", "UNKNOWN"),
        "timestamp": metadata.get("timestamp").isoformat() if metadata.get("timestamp") else "unknown",
        "severity": metadata.get("severity", "unknown"),
        "affected_node": metadata.get("affected_node", "unknown"),  # Primary service
        "root_cause": "Not specified",
        "affected_components": [],  # Will be extracted from "Affected Services" section
        "resolution_steps": [],
        "impact_summary": "Not specified"
    }
    
    lines = report_content.split('\n')
    current_section = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        # Extract Root Cause
        if '## root cause analysis' in line_lower or '## incident summary' in line_lower:
            current_section = 'root_cause'
            # Look ahead for the actual root cause content
            for j in range(i+1, min(i+10, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('#') and not next_line.startswith('**'):
                    if len(next_line) > 20:  # Meaningful content
                        incident_data['root_cause'] = next_line
                        break
        
        # Extract Impact Summary
        elif '## impact assessment' in line_lower or '## incident impact' in line_lower:
            current_section = 'impact'
            for j in range(i+1, min(i+10, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('#') and not next_line.startswith('**'):
                    if len(next_line) > 20:
                        incident_data['impact_summary'] = next_line
                        break
        
        # Extract Resolution Steps
        elif '## resolution steps' in line_lower or '## remediation' in line_lower:
            current_section = 'resolution'
            resolution_steps = []
            for j in range(i+1, min(i+20, len(lines))):
                next_line = lines[j].strip()
                if next_line.startswith('#'):  # New section
                    break
                if next_line.startswith('-') or next_line.startswith('*') or next_line[0:1].isdigit():
                    # Clean up list markers
                    step = next_line.lstrip('-*0123456789. ').strip()
                    if len(step) > 10:
                        resolution_steps.append(step)
            incident_data['resolution_steps'] = resolution_steps[:5]  # Top 5
        
        # Extract Affected Components from tables or lists
        elif 'affected component' in line_lower or 'impacted system' in line_lower:
            current_section = 'components'
            components = []
            for j in range(i+1, min(i+15, len(lines))):
                next_line = lines[j].strip()
                if next_line.startswith('#'):  # New section
                    break
                # Look for component names (usually after | or -)
                if '|' in next_line and not next_line.startswith('|---'):
                    parts = [p.strip() for p in next_line.split('|')]
                    if len(parts) >= 2:
                        comp_name = parts[1] if parts[1] else parts[0]
                        if comp_name and len(comp_name) > 2 and comp_name not in ['Component', 'Name', '']:
                            components.append({"component_name": comp_name, "impact_level": metadata.get("severity", "unknown")})
            incident_data['affected_components'] = components[:3]  # Top 3
    
    return incident_data


def load_incident_reports_from_files(
    reports_dir: Path,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Load incident reports from markdown files in the reports directory.
    Tries to load JSON metadata first, falls back to parsing filenames.
    
    Args:
        reports_dir: Path to reports directory
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        List of report metadata dictionaries
    """
    reports = []
    
    if not reports_dir.exists():
        return reports
    
    # First try to load from JSON metadata files (preferred)
    json_files = list(reports_dir.glob("incident_*.json"))
    
    if json_files:
        # Load from JSON metadata
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(metadata.get("timestamp", ""))
                
                # Filter by date range if specified
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue
                
                # Add timestamp as datetime object
                metadata["timestamp"] = timestamp
                metadata["affected_node"] = metadata.get("primary_service", "unknown")
                
                reports.append(metadata)
                
            except Exception as e:
                logger.warning(f"Failed to load metadata from {json_file}: {str(e)}")
                continue
    else:
        # Fallback: Load from markdown files and parse filenames
        logger.info("No JSON metadata found, parsing markdown files directly")
        for md_file in reports_dir.glob("incident_*.md"):
            try:
                # Parse filename: incident_20251207_044620_critical.md
                filename = md_file.name
                parts = filename.replace('.md', '').split('_')
                
                if len(parts) >= 4:
                    # Extract date/time and severity
                    date_str = parts[1]  # YYYYMMDD
                    time_str = parts[2]  # HHMMSS
                    severity = parts[3]  # critical/high/medium/low
                    
                    # Parse timestamp
                    timestamp = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
                    
                    # Filter by date range if specified
                    if start_date and timestamp < start_date:
                        continue
                    if end_date and timestamp > end_date:
                        continue
                    
                    # Create basic metadata
                    metadata = {
                        "incident_id": f"INC-{date_str}_{time_str}",
                        "timestamp": timestamp,
                        "severity": severity,
                        "primary_service": "unknown",
                        "affected_services": [],
                        "filename": filename,
                        "affected_node": "unknown"
                    }
                    
                    reports.append(metadata)
                    
            except Exception as e:
                logger.warning(f"Failed to parse markdown file {md_file}: {str(e)}")
                continue
    
    # Sort by timestamp descending
    reports.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
    
    logger.info(f"Loaded {len(reports)} incident reports from {reports_dir}")
    return reports


def calculate_statistics(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from incident reports.
    
    Args:
        reports: List of report metadata
        
    Returns:
        Dictionary with statistics
    """
    if not reports:
        return {
            "total_incidents": 0,
            "by_severity": {},
            "most_affected_services": []
        }
    
    # Count by severity
    severities = [r.get("severity", "unknown") for r in reports]
    severity_counts = dict(Counter(severities))
    
    # Count affected services
    all_services = []
    for r in reports:
        services = r.get("affected_services", [])
        all_services.extend(services)
    
    service_counts = Counter(all_services)
    most_affected = [{"service": svc, "count": cnt} for svc, cnt in service_counts.most_common(5)]
    
    return {
        "total_incidents": len(reports),
        "by_severity": severity_counts,
        "most_affected_services": most_affected
    }


def generate_weekly_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cleanup_after_report: bool = False
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a weekly summary report from stored incident reports in file system.
    
    Args:
        start_date: Start of report period (optional, defaults to all reports if both dates are None)
        end_date: End of report period (optional, defaults to all reports if both dates are None)
        cleanup_after_report: If True, deletes all report files after generation
        
    Returns:
        Tuple of (report_content, metadata) where metadata includes:
            - start_date: Report period start
            - end_date: Report period end
            - incident_count: Number of incidents included
            - filepath: Location where report was saved
            - cleanup_performed: True if cleanup was performed
            - deleted_files: Number of files deleted (if cleanup_performed)
            
    Raises:
        ValueError: If required environment variables are missing
        Exception: If report generation fails
    """
    # Create reasoning model using the unified factory
    try:
        reasoning_model = llm_factory.create_reasoning_model()
    except Exception as e:
        raise ValueError(
            f"Failed to create reasoning model from factory: {str(e)}. "
            "Ensure API keys are set in backend/agentic/.env"
        )
    
    # Set default date range
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=7)
    
    # Load incident reports from files
    reports_dir = Path("reports")
    reports = load_incident_reports_from_files(reports_dir, start_date, end_date)
    logger.info(f"Generating weekly report for {len(reports)} incidents from {start_date.date()} to {end_date.date()}")
    
    # Load full report content and extract rich incident data
    enriched_incidents = []
    for report_metadata in reports:
        try:
            # Load the actual markdown report
            md_filename = report_metadata.get("filename", "")
            md_filepath = reports_dir / md_filename
            
            with open(md_filepath, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # Parse it to extract structured data
            incident_data = parse_incident_report(report_content, report_metadata)
            enriched_incidents.append(incident_data)
            
        except Exception as e:
            logger.warning(f"Failed to load/parse report {report_metadata.get('filename', 'unknown')}: {str(e)}")
            # Fall back to basic metadata
            enriched_incidents.append({
                "incident_id": report_metadata.get("incident_id", "UNKNOWN"),
                "timestamp": report_metadata.get("timestamp"),
                "severity": report_metadata.get("severity", "unknown"),
                "affected_node": report_metadata.get("affected_node", "unknown"),
                "root_cause": "Failed to load report content",
                "affected_components": [],
                "resolution_steps": [],
                "impact_summary": "Unable to parse report"
            })
    
    # Calculate statistics from the reports
    statistics = calculate_statistics(reports)
    
    # Initialize the weekly summarizer agent with LLM from factory
    summarizer = WeeklySummarizerAgent(llm=reasoning_model)
    
    # Generate the appropriate report based on incident count
    if reports:
        # Generate incident analysis report with enriched data
        report_content = summarizer.generate_weekly_summary(
            incident_reports=enriched_incidents,  # Pass enriched data instead of raw metadata
            report_statistics=statistics,
            external_news=[],  # No external news in API version
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    else:
        # Generate all-clear report
        report_content = summarizer.generate_all_clear_report(
            external_news=[],  # No external news in API version
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    
    # Save the weekly report to file
    output_dir = Path("./weekly_reports")
    output_dir.mkdir(exist_ok=True)
    
    filename = f"weekly_report_{end_date.strftime('%Y%m%d')}.md"
    filepath = output_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    # Prepare metadata
    metadata = {
        "start_date": start_date,
        "end_date": end_date,
        "incident_count": len(reports),
        "filepath": str(filepath),
        "generated_at": datetime.now(),
        "cleanup_performed": False
    }
    
    # Perform cleanup if requested
    if cleanup_after_report and reports_dir.exists():
        logger.info("Cleanup requested - deleting JSON metadata files only (keeping markdown reports)")
        deleted_files = 0
        
        # Delete only JSON metadata files, keep markdown reports
        for file in reports_dir.glob("incident_*.json"):
            try:
                file.unlink()
                deleted_files += 1
            except Exception as e:
                logger.warning(f"Failed to delete {file}: {str(e)}")
        
        metadata["cleanup_performed"] = True
        metadata["deleted_files"] = deleted_files
        logger.info(f"Cleanup complete: Deleted {deleted_files} JSON files")
    
    return report_content, metadata
