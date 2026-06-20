<<<<<<< HEAD
# PATHWAY-ROHAN
=======
# Laminar 

Real-time data pipeline platform with SLA-driven orchestration, visual workflow design, AI-powered agents, and automated monitoring built on Pathway's streaming engine.

## Key Features

**Visual Pipeline Designer**  
Drag-and-drop interface for building complex data pipelines by connecting pre-configured nodes that uses real-time validation to ensure node schema compatibility while Pathway compiles visual workflows into pipelines. Support for multiple connectors across message queues, databases, cloud storage, and APIs.
 
**Context-Aware Pipeline Generation**  
Upload business documents to the UI and Laminar automatically extracts requirements, thresholds, and obligations to generate fully-configured metric monitoring and processing pipelines. This eliminates manual translation layers, ensuring direct alignment between business commitments and technical implementations.

**Predictive Analytics with Streaming ML**  
Continuous forecasting using online learning models (TiDE, ARF, Mamba) that adapt in real-time to data patterns. The platform predicts threshold breaches in advance, allowing for proactive intervention before issues impact operations and customers. Models update automatically with each data point without manual retraining.

**Autonomous Root Cause Analysis**  
Leveraging the extensive power of agentic AI and Pathway’s compatibility with streaming data sources, our platform gets rid of the need to manually correlate outputs from various tools when an incident occurs, through our Root Cause Analysis agent, which analyses relevant data sources and historical issues to diagnose the root cause. It then suggests
confidence-scored fixes, and executes the ones it is confident about (without the need of human intervention).

**Autonomous Execution of High-Confidence Fixes**
Graduated automation framework that executes high-confidence fixes automatically while escalating ambiguous situations with recommended actions and supporting evidence. Organizations progressively expand automation as confidence builds, balancing efficiency with risk tolerance.

**Production-Ready Guardrails**  
Comprehensive 4-layer security gateway covering network (SSRF, TLS), access (rate limiting, RBAC, BOLA prevention), data (prompt injection detection, PII scanning, secrets detection), and process controls (human-in-the-loop approval, XSS prevention). Sub-200ms overhead maintains real-time responsiveness.

**Distributed Architecture**  
Five-layer architecture with React frontend, FastAPI control layer, Pathway streaming engine in isolated Docker containers, LangGraph-orchestrated agentic services, and multi-database persistence (PostgreSQL, MongoDB, vector search). Sub-second end-to-end latency with exactly-once processing semantics.

---

##  Prerequisites

- **Python**: 3.9 or higher
- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **Docker**: Latest version with Docker Compose
- **PostgreSQL**: 15 or higher (for user authentication)
- **MongoDB Atlas**: Cloud MongoDB instance (Required - local MongoDB won't support the notification system with change streams). Get free tier at https://cloud.mongodb.com/
- **Kafka**: Optional, for streaming capabilities
- **lsof**: Required for stopping services (install via `sudo apt install lsof` on Ubuntu/Debian or `brew install lsof` on macOS)

##  Quick Start

> **Important Setup Notes:**
> - Only ONE `.env` file needed (in `backend/api/`)
> - MongoDB Atlas required (local MongoDB won't work)
> - Run `unset DOCKER_HOST` before Docker commands
> - Install `lsof` for stop script

### 1. Environment Configuration

Copy and edit the `.env` file:

```bash
cp backend/api/.env.template backend/api/.env
```

Required settings in `backend/api/.env`:
- `MONGO_URI`: MongoDB Atlas connection string (get from https://cloud.mongodb.com/)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: PostgreSQL credentials
- `GROQ_API_KEY`, `LANGSMITH_API_KEY`: Optional, for AI features

### 2. Start Kafka (Optional for testing)

If you're using Kafka-based nodes:

```bash
docker compose -f backend/kafka-docker-compose.yaml up -d
```

### 3. Build Docker Images

```bash
cd backend
docker compose build
cd ..
```

### 5. Setup PostgreSQL for User Authentication

The system requires PostgreSQL for user authentication and runbook management.

**Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql@15
brew services start postgresql@15
```

**Create Database and User:**
```bash
# Access PostgreSQL
sudo -u postgres psql

# Create database and grant privileges
CREATE DATABASE db;
CREATE USER admin WITH PASSWORD 'admin123';
GRANT ALL PRIVILEGES ON DATABASE db TO admin;
\c db
GRANT ALL ON SCHEMA public TO admin;
\q
```
**Note:** You must update your role in the user table to view all workflows as admin and other higher level options.
**Note:** User authentication tables are automatically created when the API server starts.

### 6. Run Setup Script

Make the scripts executable:

```bash
chmod +x scripts/local_setup.sh
chmod +x scripts/stop.sh
chmod +x scripts/clean_up.sh
```

Start all services (Development mode):

```bash
./scripts/local_setup.sh
```

This script will:
- Create Python virtual environments
- Install all backend dependencies
- Build required Docker images (pipeline, agentic, postgres)
- Start the API server on port **8081**
- Install frontend dependencies via npm
- Start the frontend dev server on port **8083**
- Start the Contract Parser Agent server
- Save process IDs for easy management

### 8. Access the Application

Open your browser and navigate to:
```
http://localhost:8083
```

The application provides:
- Visual workflow designer with drag-and-drop interface
- User authentication (sign up/login) with cookie-based sessions
- Real-time workflow monitoring
- WebSocket-based alerts and notifications
- Overview dashboard with analytics
- Admin panel for user management
## Management Commands

### Stop All Services

```bash
./scripts/stop.sh
```

### Clean Up a Pipeline

Remove Docker containers and networks for a specific pipeline:

```bash
./scripts/clean_up.sh <PIPELINE_ID>
```

### View Logs

Development logs are stored in `deploy/logs/` directory:
- `api.log` - API server logs
- `frontend.log` - Frontend server logs
- `contractparseragent.log` - Contract parser agent logs

Production logs:
- `deploy/logs/api_access.log` - API access logs
- `deploy/logs/api_error.log` - API error logs
- `deploy/logs/frontend.log` - Frontend logs

### Docker Images

The system uses three main Docker images for pipeline execution:

1. **backend-pipeline:latest** - Pathway runtime for pipeline execution
2. **backend-agentic:latest** - AI agents for intelligent operations
3. **backend-postgres:latest** - PostgreSQL for agent data storage

Build all images:
```bash
cd backend
unset DOCKER_HOST
docker compose build
cd ..
```

##  Important Notes

### MongoDB Atlas Requirement

**Critical:** Requires MongoDB Atlas (not local) for Change Streams support. Get free tier at: https://cloud.mongodb.com/

### Single .env Configuration

One `.env` file in `backend/api/` contains all configuration: MongoDB, PostgreSQL, Docker images, and API keys.

##  Complete Workflow

### 1. User Authentication & Workspace Setup
1. User signs up or logs in via the frontend
2. HttpOnly cookie is set for authenticated API access
3. Session stored in PostgreSQL
4. User workspaces are created in MongoDB

### 2. Workflow Creation & Design
1. User creates a new workflow in the visual designer (Playground component)
2. Drag and drop nodes from the node drawer
3. Connect nodes to define data flow
4. Configure each node's properties using dynamic JSON Schema forms
5. Undo/redo support for all changes
6. Save the workflow configuration to MongoDB

### 3. Workflow Activation (Docker Container Creation)
1. Click "Activate" button in the UI
2. API server receives the workflow ID
3. Docker Compose creates containers with three services:
   - **Pipeline service** (Pathway runtime on port 8000)
   - **Agentic service** (AI agents on port 5333)
   - **PostgreSQL** (for agent queries on port 5432)
4. Container metadata stored in MongoDB:
   - Container ID
   - Service ports and networking
   - Host IP address
   - Workflow status

### 4. Agent Configuration (Optional)
1. If using AI-powered nodes, configure agents via API
2. POST to `/build` with agent definitions:
   - Agent name and description
   - SQL tools (PostgreSQL table access)
   - Master prompts for LLM guidance
3. Agents are initialized in the agentic service container

### 5. Workflow Execution
1. Click "Run" button in the UI
2. API calls the container's `/trigger` endpoint
3. Pipeline service reads `flowchart.json`:
   - Validates all nodes using Pydantic models
   - Performs topological sort for execution order
   - Builds Pathway computational graph
4. Data flows through the workflow:
   - Input nodes read from sources (Kafka, files, databases, APIs)
   - Transformation nodes process data (filter, join, window, aggregate)
   - AI nodes use agents for intelligent processing
   - Alert nodes generate contextual notifications
   - Output nodes write to destinations (Kafka, databases, files)

### 6. Real-time Monitoring
1. WebSocket connection established on `/ws` endpoint
2. Connection health monitored via ping/pong messages
3. Workflow metrics displayed in the UI
4. Alerts, logs, and notifications pushed via WebSocket
5. Automatic reconnection with exponential backoff
6. MongoDB notifications collection tracks all events

### 7. Runbook & Remediation System
1. Errors detected trigger `/runbook/remediate` API endpoint
2. RemediationOrchestrator searches error registry using semantic matching
3. **Confidence-based approval workflow:**
   - **HIGH confidence** : Auto-execute (If none of the actions require individual approval)
   - **MEDIUM confidence** : Requires approval
   - **LOW confidence** : Manual intervention
4. **Per-action approval** for high-risk operations:
   - Actions marked with `requires_approval=True` pause execution
   - User approves via `/runbook/approve/{approval_id}` endpoint
   - Execution resumes from checkpoint after approval
5. Approval requests stored with full state preservation
6. Notifications sent via WebSocket and stored in MongoDB
7. ActionExecutor runs approved actions (SSH, API calls, scripts)
8. SafetyValidator ensures safe execution
9. Results logged and status updates broadcasted

### 8. Contract Parser Agent (SLA-to-Pipeline Conversion)
1. User provides SLA metrics via chat interface
2. Input options:
   - Upload JSON file with metrics
   - Extract metrics from PDF contract
   - Interactive CLI mode
3. Two-phase workflow:
   - **Phase 1:** Negotiate OpenTelemetry span filters
   - **Phase 2:** Build calculation nodes step-by-step with approval
4. Generates `flowchart.json` compatible with main pipeline system
5. User imports generated pipeline into visual designer

### 9. Workflow Stop & Cleanup
1. Click "Stop" button to gracefully shut down workflow
2. Pathway runtime stops processing
3. Containers remain running for quick restart
4. Click "Spin Down" to remove containers completely
5. Use `./scripts/clean_up.sh <PIPELINE_ID>` script to remove containers and networks

### 10. Data Persistence & State
- **MongoDB:** Stores workflows, container metadata, notifications, logs, RCA events, versions
- **PostgreSQL:** User authentication, sessions, runbook actions, agent data
- **Kafka:** Message streaming and alert distribution (optional)
- **Docker volumes:** Persistent storage for workflow data



##  Monitoring & Analytics

- **Real-time Alerts**: WebSocket-based alert notifications with automatic reconnection
- **Workflow Status**: Live monitoring of workflow execution
- **Overview Dashboard**: View workflow metrics, statistics, and performance
- **Admin Analytics**: User management and system-wide metrics


##  Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│  - Visual Flow Editor (React Flow)                          │
│  - User Dashboard & Analytics                               │
│  - Real-time Pipeline Monitoring                            │
│  - Approval Request UI                                      │
└───────────────────┬─────────────────────────────────────────┘
                    │ REST API / WebSocket
┌───────────────────┴─────────────────────────────────────────┐
│                   API Server (FastAPI)                      │
│  - Pipeline Management & CRUD                               │
│  - User Authentication (JWT)                                │
│  - Docker Container Orchestration                           │
│  - Schema Validation (Pydantic)                             │
│  - Runbook API & Remediation Orchestrator                   │
└───────────┬─────────────────┬───────────────────────────────┘
            │                 │
    ┌───────┴────────┐   ┌────┴──────────────────┐
    │   MongoDB      │   │  PostgreSQL           │
    │   (Metadata)   │   │  (User Auth & Actions)│
    └────────────────┘   └───────────────────────┘
            │
        ┌───┴──────────────────────────────────────┐
        │                                          │
┌───────▼──────────┐                    ┌──────────▼────────┐
│  Docker Engine   │                    │  Contract Parser  │
│  (Pipeline Exec) │                    │  Agent (WebSocket)│
└───────┬──────────┘                    └───────────────────┘
        │                                   - SLA → Pipeline
    ┌───┴──────────────────────┐           - Chat Interface
    │   Pipeline Container     │           - 2-Phase Workflow
    │   ┌──────────────────┐   │
    │   │ Pipeline Service │   │
    │   │ - Pathway Runtime│   │   <──────┐
    │   └──────────────────┘   │          │
    │   ┌──────────────────┐   │          │
    │   │ Agentic Service  │   │          │
    │   │ - AI Agents      │   │          │
    │   │ - Alert Gen      │───┼──────────┘
    │   │ - RCA System     │   │  Kafka Topics
    │   └──────────────────┘   │
    │   ┌──────────────────┐   │
    │   │ PostgreSQL       │   │
    │   │ - Agent Data     │   │
    │   └──────────────────┘   │
    └──────────────────────────┘
```

### Contract Parser Agent

The Contract Parser Agent is a specialized LLM-powered service that converts SLA metrics from contracts into executable Pathway pipelines:

**Architecture:**
```
┌──────────────────────────────────────────────────┐
│          WebSocket Client (User)                 │
│  - Upload SLA metrics (JSON/PDF)                 │
│  - Interactive negotiation                       │
└─────────────────┬────────────────────────────────┘
                  │ WebSocket
┌─────────────────▼────────────────────────────────┐
│       Contract Parser Agent Server               │
│  - server.py: WebSocket handler                  │
│  - agent_builder.py: 2-phase builder             │
│  - graph_builder.py: Node generation             │
│  - ingestion.py: PDF/JSON extraction             │
└─────────────────┬────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼────────┐    ┌──────▼─────────┐
│ Node Catalog   │    │ Anthropic API  │
│ - 40+ nodes    │    │ - Claude LLM   │
│ - Schemas      │    │ - Planning     │
└────────────────┘    └────────────────┘
        │
        │ Generates
        ▼
┌────────────────────────────────────┐
│       flowchart.json               │
│  - Compatible with main system     │
│  - Import into visual designer     │
└────────────────────────────────────┘
```

**Two-Phase Workflow:**

1. **Phase 1: Input Filter Negotiation**
   - User provides SLA metrics
   - Agent analyzes OpenTelemetry span requirements
   - Interactive chat to define filters
   - Agrees on input data structure

2. **Phase 2: Step-by-Step Pipeline Building**
   - Agent plans calculation nodes
   - Presents each step for approval
   - User can modify or reject steps
   - Generates final flowchart.json

**Usage:**
```bash
# Start server
cd backend/contractparseragent/server
python server.py

# Test client
python test_the_client.py

# Or use CLI mode
cd backend/contractparseragent
python agent_builder.py --metrics_file metrics.json
python agent_builder.py --pdf_path contract.pdf
python agent_builder.py --interactive
```


##  Project Structure

```
pathway-tasks/
├── frontend/                 # React-based UI
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── workflow/   # Workflow canvas (Playground, WorkflowCanvas)
│   │   │   ├── createWorkflow/ # Workflow creation wizard
│   │   │   ├── overview/   # Dashboard overview components
│   │   │   ├── workflowslist/ # Workflow list views
│   │   │   ├── admin/      # Admin panel components
│   │   │   └── common/     # Shared components (sidebar, etc.)
│   │   ├── pages/          # Page components
│   │   │   ├── Login.jsx   # Login page
│   │   │   ├── Signup.jsx  # Signup page
│   │   │   ├── Overview.jsx # Dashboard overview
│   │   │   ├── Workflows.jsx # Workflow editor
│   │   │   ├── WorkflowsList.jsx # Workflow list page
│   │   │   └── Admin.jsx   # Admin panel
│   │   ├── context/        # React context providers
│   │   │   ├── AuthContext.jsx # Authentication state
│   │   │   ├── GlobalContext.jsx # Global app state
│   │   │   └── WebSocketContext.jsx # Real-time connection
│   │   ├── utils/          # Helper functions and API clients
│   │   ├── hooks/          # Custom React hooks (useUndoRedo)
│   │   ├── theme/          # MUI theme configuration
│   │   └── i18n.js         # Internationalization
│   └── package.json
│
├── backend/
│   ├── api/                 # FastAPI server
│   │   ├── main.py         # Main app and lifespan management
│   │   ├── dockerScript.py # Docker management
│   │   └── routers/        # API route modules
│   │       ├── auth/       # Authentication (login, signup, users)
│   │       ├── pipelines.py # Workflow CRUD operations
│   │       ├── run_book.py  # Runbook remediation API
│   │       ├── websocket.py # WebSocket connections
│   │       ├── overview.py  # Dashboard statistics
│   │       ├── rca.py       # Root cause analysis
│   │       └── action.py    # Action execution
│   │
│   ├── pipeline/            # Pipeline execution engine
│   │   ├── __main__.py     # Pipeline orchestration
│   │   ├── server.py       # Pipeline HTTP server
│   │   └── mappings/       # Node type mappings
│   │
│   ├── agentic/             # AI agent service
│   │   └── app.py          # Agent management and execution
│   │
│   ├── lib/                 # Core libraries
│   │   ├── io_nodes.py     # Input/output node definitions
│   │   ├── tables.py       # Table operation nodes
│   │   ├── node.py         # Base node class
│   │   └── agents/         # Agent-related nodes
│   │
│   └── contractparseragent/ # SLA-to-Pipeline converter
│       ├── agent_builder.py # Two-phase workflow
│       ├── graph_builder.py # Pipeline generation
│       └── server/          # WebSocket server
│
└── scripts/                 # Deployment scripts
    ├── local_setup.sh
    ├── stop.sh
    └── clean_up.sh
```

##  Security

- Cookie-based authentication with HttpOnly cookies
- Session management with PostgreSQL storage
- Password hashing with bcrypt
- Environment-based secrets management
- Isolated Docker execution environments
- Role-based access control (User/Admin)

##  Verification & Testing

After running `./scripts/local_setup.sh`, verify everything is working:

### 1. Check Service Logs

```bash
# API Server (should show MongoDB Atlas connection)
tail -f deploy/logs/api.log
# Look for:
# - "Connected to MongoDB, DB: easyworkflow"
# - "Notification change stream listener started"
# - "Log change stream listener started"
# - "Workflow change stream listener started"
# - "RCA change stream listener started"

# Frontend
tail -f deploy/logs/frontend.log
# Look for: "VITE v7.2.6 ready"
```

### 2. Test HTTP Endpoints

```bash
# Frontend (should return 200)
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8083

# API Documentation (should return 200)
curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8081/docs
```

### 3. Verify Change Streams

Check API logs for "change stream listener started" messages (4 total). SSL errors mean you're using local MongoDB instead of Atlas.

### 4. Access the Application

Open http://localhost:8083 - login/signup pages should load without errors.

##  Troubleshooting

### Port Already in Use

If ports 8081 (API) or 8083 (frontend) are already in use:

1. **Stop services properly:**
   ```bash
   ./scripts/stop.sh
   ```

2. **If stop.sh fails, manually kill processes:**
   ```bash
   pkill -9 -f "uvicorn backend.api.main"
   pkill -9 -f "vite"
   ```

3. **Modify port numbers** (if needed):
   - Edit `scripts/local_setup.sh` for API_SERVER_PORT and FRONTEND_PORT


### MongoDB Connection Errors

SSL errors mean you're using local MongoDB. Use Atlas instead: https://cloud.mongodb.com/
Update `MONGO_URI` in `.env` with format: `mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/`

### Services Won't Start After Stopping

Run `./scripts/stop.sh`, then `rm -f deploy/pids/*.pid`, wait 3 seconds, restart.
>>>>>>> 066818f (pathway-files)
