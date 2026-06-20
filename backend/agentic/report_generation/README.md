# Report Generation Agent

AI-powered incident report generation system using LangGraph multi-agent workflow with file-based storage.

**Location**: `backend/agentic/report_generation/`

## Overview

This system generates comprehensive incident reports from telemetry-based RCA (Root Cause Analysis) output and creates weekly summaries with trend analysis. It uses:

- **LangGraph**: Multi-agent workflow (Planner → Drafter)
- **Google Gemini**: LLM for report generation
- **File-based Storage**: Simple JSON metadata + Markdown reports
- **FastAPI**: REST API endpoints for integration

## Architecture

```
backend/agentic/report_generation/
├── api/                      # FastAPI application
│   ├── main.py              # API entry point
│   ├── routes/              # API endpoints
│   └── schemas/             # Request/response models
├── core/                     # Business logic
│   ├── report_generator.py  # Incident report generation
│   └── weekly_generator.py  # Weekly summary generation
├── agents/                   # LLM agents
│   ├── planner_agent.py     # Report structure planning
│   ├── drafter_agent.py     # Final report drafting
│   └── weekly_summarizer_agent.py  # Weekly summaries
├── langgraph_workflow/       # Multi-agent workflow orchestration
├── reports/                  # Generated incident reports (auto-created)
└── weekly_reports/           # Generated weekly summaries (auto-created)
```

## Prerequisites

- Python 3.13+
- Google Gemini API key

## Installation

1. **Dependencies are managed at the agentic level**:
   - No separate requirements.txt - dependencies are in `backend/agentic/requirements.txt`
   - Install from the agentic directory: `cd backend/agentic && pip install -r requirements.txt`

2. **Configure environment variables**:
Create/update `.env` file in `backend/agentic/`:
```env
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-pro
```

## Usage

### Starting the API Server

```bash
cd backend/agentic/report_generation
uvicorn agentic.report_generation.api.main:app --host 0.0.0.0 --port 8085
```

API will be available at: `http://localhost:8085`  
Interactive docs at: `http://localhost:8085/docs`

### API Endpoints

#### 1. Generate Incident Report

**POST** `/api/v1/reports/incident`

Generates a detailed incident report from pipeline topology and RCA data.

**Request Body** (matches `RCAAnalysisOutput` from `backend/agentic/rca/output.py`):
```json
{
  "rca_output": {
    "severity": "CRITICAL",
    "affected_services": [
      "transform-001",
      "ml-tide-001",
      "egress-api-001"
    ],
    "narrative": "Critical SLA breach detected on Transformation Node following deployment v1.3. P99 latency spiked from 85ms to 342ms causing timeout errors and downstream backpressure, affecting 12,487 transactions.",
    "error_citations": [
      {
        "timestamp": "2025-12-03T08:08:00Z",
        "service": "transform-001",
        "message": "Deployment v1.3 initiated with memory-intensive operations"
      },
      {
        "timestamp": "2025-12-03T08:18:00Z",
        "service": "transform-001",
        "message": "GC overhead detected: Old Gen collection took 2.3s, heap 89%"
      }
    ],
    "root_cause": "Bad deployment v1.3 introduced memory-intensive data enrichment operations without sufficient container memory allocation, triggering frequent garbage collection pauses."
  }
}
```

**Response**:
```json
{
  "success": true,
  "report_content": "# Incident Report\n...",
  "report_id": "INC-20251203_084700-transform-001",
  "severity": "critical",
  "generated_at": "2025-12-03T08:47:00Z",
  "processing_time_seconds": 25.3
}
```

#### 2. Generate Weekly Report

**POST** `/api/v1/reports/weekly`

Generates a weekly summary report from all stored incidents.

**Request Body**:
```json
{
  "start_date": "2025-11-27T00:00:00Z",  // Optional - null for all reports
  "end_date": "2025-12-03T23:59:59Z",    // Optional - null for all reports
  "cleanup_after_report": false           // Set to true to delete reports after generation
}
```

**Response**:
```json
{
  "success": true,
  "report_content": "# Weekly Operational Report\n...",
  "start_date": "2025-11-27T00:00:00Z",
  "end_date": "2025-12-03T23:59:59Z",
  "incident_count": 7,
  "generated_at": "2025-12-04T00:00:00Z",
  "processing_time_seconds": 12.5
}
```

**Cleanup Mode**: Set `cleanup_after_report: true` to automatically delete all incident reports after generating the weekly summary. This is useful for periodic cleanup after archiving.

## Examples

Sample request files are provided in `examples/`:
- `incident_request_example.json` - Memory leak scenario
- `incident_request_database_issue.json` - Database connection pool exhaustion
- `incident_request_network_throttling.json` - S3 throttling
- `incident_request_ml_model_failure.json` - Corrupted ML model
- `incident_request_cache_issue.json` - Stale cache configuration

**Test with curl**:
```bash
curl -X POST http://localhost:8085/api/v1/reports/incident \
  -H "Content-Type: application/json" \
  -d @examples/incident_request_example.json
```

## RCA Output Schema

The report generation system expects RCA output from **telemetry data analysis** to match the `RCAAnalysisOutput` structure from `backend/agentic/rca/output.py`:

```python
class ErrorCitation(BaseModel):
    timestamp: str  # Timestamp of the log entry
    service: str    # Service or scope name where the error occurred
    message: str    # Relevant error message or excerpt from the log body

class RCAAnalysisOutput(BaseModel):
    severity: str                    # CRITICAL, HIGH, MEDIUM, or LOW
    affected_services: List[str]     # Services affected (primary service first)
    narrative: str                   # Clear explanation of what happened (max 5 sentences)
    error_citations: List[ErrorCitation]  # 2-5 specific log entries that support the analysis
    root_cause: str                  # Technical root cause (specific and actionable)
```

**Key Features**:
- **Telemetry-Based**: RCA is performed on telemetry data (logs, metrics, traces), not pipeline topology
- **Auto-generated ID**: System generates `incident_id` as `INC-{timestamp}-{primary_service}`
- **Service-Centric**: Focuses on `affected_services` identified from telemetry
- **Evidence-Based**: `error_citations` provide concrete evidence from logs
- **No Topology Required**: Reports are generated purely from RCA output without needing pipeline diagrams

## File-Based Storage

The system uses simple file-based storage:
- **Reports Directory**: `reports/` - stores incident reports
- **File Format**: 
  - `incident_{timestamp}_{severity}.md` - Markdown report content
  - `incident_{timestamp}_{severity}.json` - JSON metadata with incident details
- **Weekly Reports**: Stored in `weekly_reports/` directory
- **No Database Required**: All data stored as files for simplicity and portability

## Report Features

### Incident Reports Include:
- Executive summary with key findings
- Root cause analysis from telemetry data
- Affected services analysis
- Error log citations table (timestamp, service, message)
- Impact assessment based on telemetry metrics
- Timeline reconstruction from error citations
- Remediation recommendations
- All data presented in tables and formatted text (no charts/diagrams)

### Weekly Reports Include:
- Executive summary
- Incident statistics and trends
- Critical incident details with root causes
- Most affected components
- Pattern analysis
- Recommendations for next week
- Pipeline health overview

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | - | Google Gemini API key |
| `GOOGLE_MODEL` | No | `gemini-pro` | Gemini model to use |

### API Server Settings

Edit `api/main.py` to configure:
- CORS origins (default: all allowed)
- Port (default: 8085)
- Logging level (default: INFO)

## Integration Guide

### Adding to Your Project

1. Copy the `report generation agent` folder to your project
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in your deployment
4. Start the API server or import the core modules

### Programmatic Usage

```python
from agentic.report_generation.core.report_generator import generate_incident_report
from agentic.report_generation.core.weekly_generator import generate_weekly_report

# Generate incident report from telemetry-based RCA
report_content, metadata = generate_incident_report(
    rca_output=rca_dict
)

# Generate weekly report
weekly_content, metadata = generate_weekly_report(
    start_date=datetime(2025, 11, 27),
    end_date=datetime(2025, 12, 3),
    cleanup_after_report=False
)
```

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY backend/agentic /app/agentic

RUN pip install -r /app/agentic/requirements.txt

EXPOSE 8085

CMD ["uvicorn", "agentic.report_generation.api.main:app", "--host", "0.0.0.0", "--port", "8085"]
```

## Development

### Project Structure

- **`api/`**: FastAPI routes and schemas (REST API layer)
- **`core/`**: Business logic (report generation workflows)
- **`agents/`**: LLM agents (Planner, Drafter, Summarizer)
- **`langgraph_workflow/`**: Multi-agent orchestration
- **`reports/`**: Generated incident reports (auto-created)
- **`weekly_reports/`**: Generated weekly summaries (auto-created)

### Adding New Features

1. **New Agent**: Create in `agents/`, implement prompt and LLM call
2. **New Endpoint**: Add route in `api/routes/`, define schema in `api/schemas/`
3. **New Report Type**: Extend workflow in `langgraph_workflow/`

## Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not found"**
- Ensure `.env` file exists with valid API key
- Check environment variables are loaded

**Weekly report shows "Unknown" for everything**
- Ensure incident reports exist in `reports/` directory
- Check that both `.md` and `.json` files are present for each incident

**Reports not being found**
- Verify the `reports/` directory exists and contains incident files
- Check file naming format: `incident_{timestamp}_{severity}.md|.json`

## Performance

- **Incident Report Generation**: 15-25 seconds (includes LLM calls for analysis and drafting)
- **Weekly Report Generation**: 10-15 seconds (depends on number of incidents)
- **File I/O**: < 1 second (reading/writing reports from file system)

## License

Internal use only - check with your team for licensing details.

## Support

For issues or questions, contact the DevOps team or check the project documentation.
