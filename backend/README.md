The backend service for our Low code platform, built with FastAPI and Pathway. This service handles pipeline orchestration, user authentication, Docker container management, and AI-powered agentic workflows.

##  Architecture Overview

The backend consists of four main components:

### 1. API Service (`api/`)
The main FastAPI application that serves as the central API gateway.

**Responsibilities:**
- User authentication and authorization (JWT-based)
- Pipeline CRUD operations
- Docker container lifecycle management
- Schema validation and node type registry
- WebSocket connections for real-time alerts
- MongoDB integration for metadata storage

**Key Files:**
- `main.py` - FastAPI application with all endpoints
- `dockerScript.py` - Docker container management utilities

### 2. Pipeline Service (`pipeline/`)
The core pipeline execution engine that runs inside Docker containers.

**Responsibilities:**
- Reading and parsing pipeline JSON configurations
- Topological sorting of pipeline graphs
- Dynamic node execution using Pathway
- Real-time data processing
- HTTP server for pipeline control (start/stop)

**Key Files:**
- `__main__.py` - Pipeline orchestration and execution
- `mappings.py` - Node type to Pathway function mappings
- `server.py` - FastAPI server for pipeline control
- `RunBookDocumentStore.py` - Uses **pathway's document** store to live index errors, which is essential for runbook error matching, without worrying about reindexing or outdated/broken data.
### 3. Agentic Service (`agentic/`)
AI-powered agent management system for intelligent pipeline operations.

**Responsibilities:**
- LLM-based agent creation and management
- Agentic tool integration (SQL, RAG, custom)
- Alert generation with contextual awareness and targeting low latency
- Multi-agent coordination with supervisor pattern, and inter workflow communication
- Root Cause Analysis (RCA) workflow
- Automated incident report generation with weekly summaries
- PII detection and sanitization for security
- Multi-layer guardrails (input scanning, MCP security gateway)

**Key Files:**
- `app.py` - FastAPI application for agent services
- `pii.py` - PII pattern detection and sanitization
- `guardrails/` - Security guardrails (input scanning, gateway, batch processing)
- `rca/` - Root Cause Analysis system 
- `report_generation/` - LangGraph-based incident report generation
- `requirements.txt` - AI/ML dependencies

### 4. Core Libraries (`lib/`)
Shared libraries and node definitions used across services.

**Key Modules:**
- `io_nodes.py` - Input/output connector node definitions (40+ connectors)
- `tables.py` - Table operation node definitions
- `alert.py` - Alert system node definitions
- `validate.py` - Schema validation and node registry
- `node.py` - Base node class and interfaces

### 5. Contract Parser Agent (`contractparseragent/`)
LLM-powered pipeline builder that converts SLA metrics into Pathway flowcharts.

**Responsibilities:**
- Interactive chat-based pipeline creation
- Two-phase workflow: input filter negotiation → node-by-node construction
- OpenTelemetry span configuration
- Automated flowchart generation from natural language and PDFs

**Key Files:**
- `agent_builder.py` - Two-phase pipeline builder (CLI mode)
- `graph_builder.py` - Node generation and macro planning
- `ingestion.py` - PDF extraction and metric loading
- `node_catalog.json` - Node type definitions
- `server/server.py` - WebSocket server for interactive sessions

##  Node Types

### Input Connectors (25+)
Data source integrations for reading data into pipelines:

- **Message Queues**: Kafka, Redpanda, NATS, MQTT
- **Databases**: PostgreSQL, MySQL, MongoDB, SQLite
- **Cloud Storage**: S3, MinIO, Google Drive
- **Data Lakes**: Delta Lake, Iceberg
- **Files**: CSV, JSON Lines, Plain Text
- **Streaming**: Kinesis, Debezium, Airbyte
- **Web**: HTTP/REST endpoints
- **Custom**: Python connector for custom sources

### Output Connectors (20+)
Data destination integrations for writing pipeline results:

- **Message Queues**: Kafka, Redpanda, NATS, MQTT
- **Databases**: PostgreSQL, MySQL, MongoDB, DynamoDB
- **Search**: Elasticsearch
- **Cloud Services**: BigQuery, Pub/Sub, Kinesis
- **Files**: CSV, JSON Lines
- **Monitoring**: Logstash, QuestDB

### Table Operations (10+)
Data transformation and manipulation nodes:

- **Filter**: Apply conditions to filter rows
- **Sort**: Sort data by columns
- **Join**: Join two tables (inner, left, right, outer)
- **Concat**: Concatenate two tables
- **Update Rows**: Update existing rows with new data

### Temporal Operations
Time-based windowing for streaming data:

- **Sliding Window**: Overlapping time windows
- **Tumbling Window**: Non-overlapping fixed windows
- **Session Window**: Gap-based session windows

### AI Operations
- **Alert Node**: AI-generated contextual alerts
- **RAG Node**: Retrieval Augmented Generation

## Pipeline Execution Flow

```
1. User designs pipeline → Saves to MongoDB
                              ↓
2. User clicks "Activate" → API creates Docker container with:
                              - Pipeline service (Pathway runtime)
                              - Agentic service (AI agents)
                              - PostgreSQL (for agent data access)
                              ↓
3. Container starts with unique ports assigned
   - pipeline_host_port (e.g., 8001)
   - agentic_host_port (e.g., 5334)
   - db_host_port (e.g., 5433)
                              ↓
4. User clicks "Run" → API calls container's /trigger endpoint
                              ↓
5. Pipeline service:
   a. Reads flowchart.json from volume mount
   b. Validates all nodes using Pydantic models
   c. Performs topological sort for execution order
   d. Builds Pathway computational graph
   e. Executes: pw.run()
                              ↓
6. Pipeline processes data in real-time:
   - Input nodes: Read from sources (Kafka, S3, PostgreSQL, etc.)
   - Transformation nodes: Filter, join, aggregate, window operations
   - AI nodes: Agent-based processing and decision making
   - Alert nodes: Generate contextual notifications via LLM
   - Output nodes: Write to destinations (Kafka, databases, files)
                              ↓
7. Real-time monitoring:
   - Metrics exported via HTTP endpoint (port 11111)
   - Alerts published to Kafka topics
   - WebSocket broadcasts to frontend
   - MongoDB notifications for approval requests
                              ↓
8. User clicks "Stop" → Pipeline gracefully shuts down
   - Completes current processing batch
   - Closes connections to external systems
   - Container remains running for quick restart
                              ↓
9. User clicks "Spin Down" → Container and network removed
   - All resources cleaned up
   - Pipeline status updated in MongoDB
```

## Root Cause Analysis (RCA) System

The platform includes an intelligent RCA system that automatically analyzes telemetry data to identify root causes of incidents.

### Supported Incident Types

1. **Error Analysis**: Traces error logs to identify failure points
2. **Latency Analysis**: Analyzes performance degradation using span data
3. **Downtime Analysis**: Investigates service availability issues

### RCA Workflow

```
1. Incident Triggered → RCA Event Created
                              ↓
2. Input Sanitization:
   - PII detection and masking (emails, phones, IPs, tokens)
   - Security guardrails applied (MCP Security Gateway)
   - Malicious input filtering
                              ↓
3. Agent Selection Based on Metric Type:
   ERROR → Error Agent (trace log analysis)
   LATENCY → Latency Agent (span analysis + graph building)
   DOWNTIME → Downtime Agent (timestamp analysis)
                              ↓
4. Multi-Agent Workflow (LangGraph):
   a. Planner Agent: Creates analysis structure
   b. Specialized Agent: Performs deep analysis
   c. Summarizer Agent: Generates insights
                              ↓
5. Output Generation:
   - Root cause identification
   - Contributing factors
   - Timeline reconstruction
   - Recommended actions
                              ↓
6. Report Generation (Optional):
   - Incident report (Markdown)
   - Weekly summary with trend analysis
   - File-based storage for audit trail
```

### Security Features

1. **PII Sanitization** (`pii.py`):
   - Email addresses → `[EMAIL]`
   - Phone numbers → `[PHONE]`
   - IP addresses → `[IP]`
   - Aadhaar numbers → `[AADHAAR]`
   - API tokens → `[TOKEN]`
   - User/Session IDs → `[USER_ID]`/`[SESSION]`

2. **Input Guardrails** (`guardrails/`):
   - **Base Detector**: Framework for threat detection
   - **Before Agent**: Input scanning before LLM processing
   - **Gateway**: MCP Security Gateway for request validation
   - **Batch Processing**: Efficient multi-input validation

### Report Generation

Automated incident report generation using Google Gemini:

- **Incident Reports**: Comprehensive analysis with root cause, timeline, and recommendations
- **Weekly Summaries**: Trend analysis across multiple incidents
- **Storage**: JSON metadata + Markdown reports in `reports/` and `weekly_reports/`
- **API**: FastAPI endpoints for integration with external systems

## Runbook & Remediation Workflow

The system includes an automated runbook and remediation system:

```
1. Error Detected → Sent to Agentic Service
                              ↓
2. Pathway Semantic Search:
   - Vector embedding of error message
   - Similarity search in error knowledge base
   - Returns top-k matches with distance scores
                              ↓
3. Confidence Classification:
   HIGH :    Auto-execute actions
   MEDIUM:   Requires approval
   LOW :     Manual intervention needed
                              ↓
4. If MEDIUM confidence → Approval Request:
   a. Create ApprovalRequest with full state
   b. Store in ApprovalManager (in-memory + MongoDB)
   c. Send notification to MongoDB collection
   d. WebSocket broadcasts approval request to UI
                              ↓
5. User Reviews Request:
   - Views matched error and suggested actions
   - Sees confidence score and risk levels
   - Checks per-action approval requirements
                              ↓
6. Approval Decision:
   
   IF APPROVED:
   a. User approves overall remediation
   b. Execution begins sequentially
   c. For each action:
      - If requires_approval=True → Pause execution
      - Request per-action approval from user
      - User approves → Resume execution
      - User rejects → Skip action, continue with next
   d. Update notification status at each step
   e. WebSocket broadcasts progress updates
   
   IF REJECTED:
   a. Mark ApprovalRequest as rejected
   b. Store rejection reason
   c. Update notification status
   d. Log rejection for audit trail
                              ↓
7. Action Execution:
   - Fetch action details from RunbookRegistry (PostgreSQL)
   - Resolve secrets from SecretsManager
   - Validate safety constraints
   - Execute via appropriate executor:
     * SSH scripts
     * API calls (REST/RPC)
     * Database queries
   - Record execution results
                              ↓
8. Completion:
   - Update ApprovalRequest status to completed
   - Log all execution details
   - Send final notification update
   - Provide execution summary to user
```

## Getting Started

### Prerequisites

```bash
# Python 3.9+ (3.13+ recommended for report generation)
python --version

# Docker
docker --version

# PostgreSQL
psql --version

# Optional: Kafka (for alerts)
kafka-server-start --version
```

**note** Please ensure 

### Installation
>Follow this only when testing backend standalone - otherwise use scripts/local_setup.sh

1. **Configure environment variables:**

```bash
# backend/api/.env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=pathway_tasks
SECRET_KEY=your-secret-key-here

# LLM API Keys
GROQ_API_KEY=your-groq-api-key
ANTHROPIC_API_KEY=your-anthropic-key  # For Contract Parser Agent
GOOGLE_API_KEY=your-google-api-key    # For Report Generation

PATHWAY_LICENSE_KEY=your-pathway-license
KAFKA_BOOTSTRAP_SERVER=localhost:9092

# PostgreSQL for user authentication
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin123

# Docker images (set these environment variables before starting API)
PIPELINE_IMAGE_NAME=backend-pipeline:latest
POSTGRES_IMAGE_NAME=backend-postgres:latest
AGENTIC_IMAGE_NAME=backend-agentic:latest

# Optional: RCA Configuration
RCA_ENABLE_GUARDRAILS=true
RCA_PII_DETECTION=true
```

2. **Setup PostgreSQL for user authentication:**
```bash
# Install PostgreSQL (if not installed)
sudo apt install postgresql postgresql-contrib  # Ubuntu/Debian
# or: brew install postgresql@15  # macOS

# Create database and user
sudo -u postgres psql
CREATE DATABASE db;
CREATE USER admin WITH PASSWORD 'admin123';
GRANT ALL PRIVILEGES ON DATABASE db TO admin;
\c db
GRANT ALL ON SCHEMA public TO admin;
\q
```

**Note:** User tables are automatically created when you start the API server.

3. **Build Docker images:**

```bash
cd backend
docker compose build
```

4. **Install API dependencies:**

```bash
cd backend/api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Note:** User tables are automatically created when you start the API server. For manual setup, see `backend/auth/README.md`.

4. **Build Docker images:**

```bash
cd backend
docker compose build
```

### Running the API Service

```bash
cd backend/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

API will be available at: `http://localhost:8081`

Interactive API docs: `http://localhost:8081/docs`

##  API Endpoints

### Authentication (`/auth/`)

```
POST   /auth/signup          - Register new user
POST   /auth/login           - Login and get JWT token
POST   /auth/refresh         - Refresh access token
POST   /auth/logout          - Logout (invalidate token)
GET    /auth/me              - Get current user info
```

### Schema (`/schema/`)

```
GET    /schema/all           - List all available node types
GET    /schema/{node_name}   - Get JSON schema for specific node
```

### Workflow & Version Management (`/api/v1/`)

```
POST   /create_pipeline              - Create new workflow
POST   /save                         - Save workflow version
POST   /save_draft                   - Save draft without versioning
POST   /retrieve                     - Get workflow by ID
GET    /versions/{workflow_id}       - List all versions of workflow
POST   /restore_version              - Restore specific version
POST   /add_viewer                   - Add viewer permissions
POST   /remove_viewer                - Remove viewer permissions
DELETE /delete/{workflow_id}         - Delete workflow
```

### Pipeline Management

```
POST   /spinup               - Create Docker container for pipeline
POST   /spindown             - Stop and remove pipeline container
POST   /run                  - Start pipeline execution
POST   /stop                 - Stop pipeline execution
GET    /pipeline/{id}/status - Get pipeline execution status
```

### Overview & Monitoring (`/overview/`)

```
GET    /kpi                                      - Dashboard KPIs (workflows, alerts, runtime)
GET    /logs                                     - Fetch pipeline logs
GET    /workflows/                               - List user workflows
GET    /total_runtime                            - Total runtime across pipelines
GET    /notifications                            - Get user notifications
PATCH  /notifications/{notification_id}/action  - Update notification action
GET    /charts                                   - Chart data for dashboards
```

### Root Cause Analysis (`/rca/`)

```
POST   /add_rca_event              - Create RCA event (agent-only)
GET    /get_rca_events             - List RCA events for pipeline
GET    /get_rca_event/{event_id}   - Get specific RCA event
PATCH  /update_rca_event/{event_id} - Update RCA event status
DELETE /delete_rca_event/{event_id} - Delete RCA event
```

### Runbook & Remediation (`/runbook/`)

```
POST   /runbook/remediate                  - Trigger remediation for an error
POST   /runbook/remediate/approve          - Approve/reject remediation request
GET    /runbook/approvals/pending          - List pending approval requests
GET    /runbook/approvals/{request_id}     - Get approval request details
POST   /runbook/approvals/{request_id}/actions/{action_id}/approve
                                            - Approve individual action
```

### Discovery & Secrets (`/v1/`)

```
POST   /v1/discover/ssh      - Discover actions from SSH server
POST   /v1/discover/swagger  - Discover actions from OpenAPI spec
POST   /v1/secrets/provision - Provision secrets for discovered actions
GET    /v1/secrets/list      - List provisioned secrets
```

### Real-time Communication

```
WS     /ws/alerts/{pipeline_id}  - WebSocket for live alerts
WS     /ws/                       - General WebSocket connection
```

### Test & Development (`/test/`)

```
POST   /test_rca_event        - Generate test RCA event
POST   /test_notification     - Generate test notification
POST   /test_alert            - Generate test alert
POST   /test_log              - Generate test log entry
POST   /test_critical_log     - Generate critical log
POST   /add_notification      - Manually add notification
POST   /add_log               - Manually add log entry
POST   /test_all              - Run all tests
```

##  Adding Custom Nodes

### Step 1: Define Node Schema

Create a new Pydantic model in `lib/io_nodes.py` (for I/O) or `lib/tables.py` (for transformations):

```python
# backend/lib/tables.py

from typing import Literal
from .node import Node

class MyCustomNode(Node):
    node_id: Literal["my_custom"]
    category: Literal["table"]
    n_inputs: Literal[1] = 1
    
    # Node-specific parameters
    threshold: float
    column_name: str
```

### Step 2: Add Pathway Function Mapping

Add the node's execution logic in `pipeline/mappings.py`:

```python
# backend/pipeline/mappings.py

table_mappings: dict[str, MappingValues] = {
    # ... existing mappings
    
    "my_custom": {
        "node_fn": lambda inputs, node: inputs[0].select(
            *pw.this,
            custom_result=pw.this[node.column_name] * node.threshold
        ),
    },
}
```

### Step 3: Update Frontend

Add the new node to the frontend sidebar and configure its UI (see `frontend/README.md`).

### Step 4: Test

Create a pipeline using your new node and verify it executes correctly.

##  Validation System

The validation system uses Pydantic models to ensure pipeline configurations are correct before execution.

### How Validation Works

1. **Node Registry**: `validate.py` scans `io_nodes.py` and `tables.py` to build a map of `node_id → Pydantic Class`

2. **Validation Function**: `validate_nodes()` takes a list of node dictionaries from the frontend

3. **Schema Checking**: For each node:
   - Looks up the appropriate Pydantic model
   - Extracts properties from the JSON structure
   - Instantiates the model (triggers validation)
   - Returns validated node objects or raises errors

### Example Usage

```python
from backend.lib.utils import validate_nodes

nodes_data = [
    {
        "node_id": "csv",
        "category": "io",
        "data": {
            "properties": [
                {"label": "path", "value": "/data/input.csv"},
                {"label": "table_schema", "value": '{"id": "int", "name": "str"}'}
            ]
        }
    }
]

validated = validate_nodes(nodes_data)
# Returns list of validated node objects
```

##  Agentic System

The agentic system enables AI-powered operations within pipelines.

### Agent Architecture

```
Supervisor Agent
    ├── Data Agent 1 (SQL access)
    ├── Data Agent 2 (RAG access)
    ├── RCA Agents (Error/Latency/Downtime)
    ├── Report Generation Agent (LangGraph workflow)
    └── Custom Agent N
```

### Creating Agents

Agents are configured per pipeline with:
- **Name**: Unique identifier
- **Description**: What the agent does
- **Master Prompt**: System instructions
- **Tools**: Database tables, custom functions, or RAG stores
- **Guardrails**: Input sanitization and security checks

### Agent Tools

1. **SQL Tools**: Query PostgreSQL tables with natural language
2. **RAG Tools**: Query document stores (Pathway-based indexing)
3. **Custom Tools**: User-defined functions
4. **RCA Tools**: Specialized tools for log analysis, span traversal, metric queries

### Alert Generation

Alerts use a specialized agent that:
1. Receives trigger data from pipeline
2. Evaluates against alert prompt
3. Generates structured alert (type + message)
4. Publishes to Kafka topic
5. WebSocket pushes to frontend
6. Stores in MongoDB for audit trail

### LLM Configuration

Supported providers (`llm_factory.py`):
- **Groq**: Fast inference for real-time alerts
- **Anthropic Claude**: Advanced reasoning for RCA
- **Google Gemini**: Report generation and summarization
- **OpenAI**: General-purpose agent tasks

Configuration via `llm_config.py` with provider-specific settings.

##  Docker Container Structure

Each pipeline runs in an **isolated Docker container** with:

```
Container:
├── Pipeline Service (port: dynamic)
│   └── Pathway runtime executing the workflow
├── Agentic Service (port: dynamic)
│   └── AI agents for intelligent operations
└── PostgreSQL (port: dynamic)
    └── Database for agent SQL queries
```

The API server manages containers using Docker SDK:
- Creates containers with unique names
- Maps random host ports to avoid conflicts
- Stores container metadata in MongoDB
- Provides lifecycle management (start/stop/remove)

##  Database Schema

### MongoDB Collections

**workflows** (workflow metadata with version control):
```json
{
  "_id": "ObjectId",
  "name": "Workflow Name",
  "owner_ids": ["user_id"],
  "viewer_ids": ["viewer_id1", "viewer_id2"],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z",
  "container_id": "docker_container_id",
  "pipeline_host_port": 8001,
  "agentic_host_port": 8002,
  "db_host_port": 5433,
  "host_ip": "192.168.1.100",
  "status": "Stopped",
  "runtime": 3600
}
```

**versions** (version history):
```json
{
  "_id": "ObjectId",
  "workflow_id": "ObjectId",
  "version_number": 1,
  "pipeline": { /* Flowchart JSON */ },
  "created_at": "2024-01-01T00:00:00Z",
  "created_by": "user_id",
  "commit_message": "Initial version"
}
```

**notifications** (alerts and approval requests):
```json
{
  "_id": "ObjectId",
  "pipeline_id": "ObjectId",
  "type": "alert|approval",
  "message": "Alert message",
  "alert": {
    "action_taken": false,
    "action_value": "acknowledged"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**rca_events** (Root Cause Analysis incidents):
```json
{
  "_id": "ObjectId",
  "pipeline_id": "ObjectId",
  "title": "High Latency Detected",
  "description": "95th percentile exceeded threshold",
  "triggered_at": "2024-01-01T00:00:00Z",
  "trace_ids": ["trace_1", "trace_2"],
  "metadata": {
    "metric_type": "latency|error|downtime",
    "root_cause": "Database connection pool exhaustion",
    "analysis_result": { /* RCA output */ }
  },
  "status": "in_progress|completed|failed"
}
```

### PostgreSQL

**User Authentication** (`users` table):
- `id` (Integer, Primary Key)
- `email` (String, Unique)
- `hashed_password` (String, bcrypt)
- `full_name` (String, Optional)
- `is_active` (Boolean)
- `role` (String: "user"|"admin")
- `created_at` (DateTime)

**Agent Data Tables**:
- Dynamically created based on pipeline output schemas
- Agents can query these tables using natural language
- Supports complex joins and aggregations

**Runbook Registry** (`actions` table):
- Action definitions with SSH/API/K8s executors
- Secret references for credentials
- Safety constraints and approval requirements

##  Security

### Authentication Flow

1. User registers: `POST /auth/signup`
   - Password hashed with bcrypt
   - User stored in PostgreSQL

2. User logs in: `POST /auth/login`
   - Credentials verified
   - JWT access token (60 min) + refresh token (30 days) issued

3. Protected requests:
   - Include: `Authorization: Bearer <access_token>`
   - API validates JWT signature and expiration

4. Token refresh: `POST /auth/refresh`
   - Exchange refresh token for new access token

### Secrets Management

The system includes a comprehensive secrets management system:

1. **Discovery Phase:**
   - SSH/API discovery identifies required secrets (credentials, API keys)
   - Returns `secrets_required` array with keys and descriptions

2. **Provisioning:**
   - Users provide secret values via `/v1/secrets/provision`
   - Secrets stored encrypted in SQLite database
   - Secret keys follow format: `{service}_{resource}_{parameter}`

3. **Resolution:**
   - Actions reference secrets via `secret_references` array
   - Execution engine resolves secrets before action execution
   - Secrets injected into SSH connections, API headers, etc.

4. **Security Schemes:**
   - API Key (header, query, cookie)
   - HTTP Basic Authentication
   - Bearer Token
   - OAuth2
   - OpenID Connect
   - Dynamic application based on action metadata

### Best Practices

- Store tokens in HTTP-only cookies (production)
- Use HTTPS in production
- Rotate secret keys regularly
- Implement rate limiting on all endpoints
- Validate all user inputs with Pydantic models
- Sanitize database queries (use parameterized queries)
- Keep secrets in secure vault (production)
- Use per-action approval for high-risk operations
- Audit all remediation actions with timestamps

##  Contract Parser Agent

Interactive pipeline builder for converting SLA metrics into executable workflows.

### Usage Modes

1. **Interactive WebSocket Server**:
```bash
cd backend/contractparseragent/server
export ANTHROPIC_API_KEY="your-key"
python server.py

# In another terminal
python test_the_client.py
```

2. **CLI Mode with JSON**:
```bash
cd backend/contractparseragent
python agent_builder.py --metrics_file metrics.json
```

3. **PDF Extraction**:
```bash
python agent_builder.py --pdf_path contract.pdf
```

4. **Interactive CLI**:
```bash
python agent_builder.py --interactive
```

### Two-Phase Workflow

**Phase 1: Input Filter Negotiation**
- Discusses required OpenTelemetry span fields
- Configures data source connectors
- Sets up filtering criteria
- User approves input configuration

**Phase 2: Node-by-Node Construction**
- Generates calculation nodes step-by-step
- Requests user approval for each node
- Builds complete pipeline graph
- Validates node connections and data flow

**Output**: `flowchart.json` compatible with main pipeline system

### Testing Without LLM

```bash
cd backend/contractparseragent/server
python mock_server.py      # Terminal 1
python test_mock_client.py # Terminal 2
```

Mock mode uses predefined responses for testing the workflow without API costs.

##  Performance Considerations

### Pipeline Optimization

1. **Node Ordering**: Topological sort ensures optimal execution
2. **Lazy Evaluation**: Pathway uses lazy evaluation for efficiency
3. **Streaming**: Built for continuous data processing
4. **Parallelization**: Pathway handles parallel execution automatically

### Scaling

- **Horizontal**: Run multiple API servers behind load balancer
- **Vertical**: Increase Docker container resources
- **Database**: Use MongoDB replica sets for HA
- **Kafka**: Scale Kafka cluster for high throughput


