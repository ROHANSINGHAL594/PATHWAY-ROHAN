# Laminar Frontend

Modern React-based visual workflow builder for creating and managing real-time data pipelines. Built with React Flow, Material-UI, Tailwind CSS, and Vite.

## Features

### Visual Workflow Editor
- **Drag-and-Drop Interface**: Intuitive node-based workflow builder with React Flow
- **Real-time Validation**: Instant feedback on connections and configurations
- **Auto-Layout**: Smart node positioning and edge routing
- **Zoom & Pan**: Navigate large workflows easily
- **Node Catalog**: Extensive pre-built nodes organized by category
- **Undo/Redo**: Full history management for workflow changes
- **Property Editor**: Configure node properties with dynamic forms

### User Authentication
- **Secure Login/Signup**: Cookie-based authentication with HttpOnly cookies
- **Session Management**: Automatic session handling
- **Protected Routes**: Role-based access control (User/Admin)
- **Admin Panel**: Administrative interface for user management

### Real-time Features
- **WebSocket Integration**: Live notifications and updates
- **Alert System**: Real-time alerts for workflow events
- **Notification Panel**: Track all system notifications
- **Workflow Status**: Real-time execution monitoring

### Dashboard & Analytics
- **Workflow Management**: Create, edit, delete, and organize workflows
- **Overview Dashboard**: Quick stats and workflow status
- **Workflow List**: Grid view of all workflows with search/filter
- **Execution Logs**: View workflow execution history
- **Contract Parser Integration**: Generate workflows automatically from documents and descriptions

### User Experience
- **Responsive Design**: Works on desktop and tablet
- **Modern UI**: Material-UI with Tailwind CSS
- **Data Visualization**: Charts with Recharts and MUI X-Charts
- **Date Pickers**: Advanced date/time selection
- **Markdown Support**: Rich text rendering


##  Quick Start

### Prerequisites

- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **Backend API**: Running on port 8081

### Setup & Run

**Recommended:** Use the automated setup script from project root:

```bash
# From project root
./scripts/local_setup.sh
```

This script handles:
- Installing npm dependencies
- Starting dev server on port **8083**
- Process management and logging

**Manual Setup:**

```bash
cd frontend
npm install
npm run dev -- --port 8083
```

The application will be available at `http://localhost:8083`

Features in development mode:
- Hot module replacement (HMR)
- Fast refresh for React components
- Source maps for debugging
- Detailed error messages

### Configuration

No `.env` file needed for frontend. Backend API URL is configured in `config.json`:

```json
{
  "API_URL": "http://localhost:8081"
}
```

### Development Features

- Hot module replacement (HMR)
- Fast refresh for React components
- Source maps for debugging
- Detailed error messages

### Production Build

```bash
npm run build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── workflow/        # Workflow canvas and editor
│   │   ├── createWorkflow/  # Workflow creation wizard
│   │   ├── overview/        # Dashboard overview
│   │   ├── workflowslist/   # Workflow list views
│   │   ├── admin/           # Admin panel components
│   │   ├── common/          # Shared components (sidebar, etc.)
│   │   ├── base/            # Base UI components
│   │   └── icons/           # Icon components
│   ├── pages/               # Page components
│   │   ├── Login.jsx
│   │   ├── Signup.jsx
│   │   ├── Overview.jsx
│   │   ├── Workflows.jsx
│   │   ├── WorkflowsList.jsx
│   │   ├── Admin.jsx
│   │   ├── ProtectedRoute.jsx
│   │   └── AdminProtectedRoute.jsx
│   ├── context/             # React context providers
│   │   ├── AuthContext.jsx
│   │   ├── GlobalContext.jsx
│   │   └── WebSocketContext.jsx
│   ├── utils/               # Utility functions
│   │   ├── dashboard.utils.js
│   │   ├── developerDashboard.api.js
│   │   └── validation helpers
│   ├── hooks/               # Custom React hooks
│   │   └── useUndoRedo.js
│   ├── lib/                 # Library code and constants
│   ├── theme/               # MUI theme configuration
│   ├── styles/              # Global styles
│   ├── providers/           # Additional providers
│   ├── reducers/            # State reducers
│   ├── helpers/             # Helper functions
│   ├── assets/              # Static assets
│   ├── config.js            # App configuration
│   ├── i18n.js              # Internationalization setup
│   ├── App.jsx              # Main App component
│   └── main.jsx             # Entry point
├── public/                  # Public assets
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
├── eslint.config.js         # ESLint configuration
├── package.json             # Dependencies
├── config.json              # TypeScript config
└── .env.template            # Environment template
```

## Key Components

### Workflow Editor
- **Playground**: Main workflow canvas container with undo/redo
- **WorkflowCanvas**: React Flow canvas implementation
- **NodeDrawer**: Draggable node catalog
- **PropertyBar**: Node configuration sidebar
- **BottomToolbar**: Workflow action controls
- **ZoomControl**: Canvas zoom controls

### Page Components
- **Overview**: Dashboard with workflow stats and quick actions
- **WorkflowsList**: Grid/list view of all workflows
- **Workflows**: Individual workflow editor page
- **Admin**: Administrative panel for user management
- **Login/Signup**: Authentication pages

### Context Providers
- **AuthContext**: User authentication state and methods
- **GlobalContext**: Global app state (workflows, notifications, loading)
- **WebSocketContext**: Real-time WebSocket connection management

## API Integration

The frontend communicates with the backend via:

1. **REST API** (fetch with cookies):
   - Authentication (cookie-based sessions)
   - Workflow CRUD operations
   - Node schema fetching
   - Admin operations

2. **WebSocket** (native WebSocket API):
   - Real-time alerts and notifications
   - Workflow status updates
   - Log streaming
   - Connection health monitoring (ping/pong)

Example API usage:

```javascript
// Fetch workflows
import { fetchAllWorkflows } from './utils/developerDashboard.api';

const loadWorkflows = async () => {
  const response = await fetchAllWorkflows();
  if (response.status === "success") {
    setWorkflows(response.data);
  }
};

// WebSocket connection (from WebSocketContext)
const connectWebSocket = () => {
  const wsUrl = `${import.meta.env.VITE_WS_SERVER}/ws`;
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
  };
};
```

## State Management

Uses React Context API for global state:

- **AuthContext**: User authentication state, login/logout methods
- **GlobalContext**: Workflows, notifications, loading states, container IDs
- **WebSocketContext**: Real-time connection, alerts, logs, workflow updates

## Styling

- **Material-UI (MUI)**: Primary component library (v7+)
- **Tailwind CSS**: Utility-first styling (v4+)
- **Emotion**: CSS-in-JS styling
- **Responsive Design**: Mobile-first approach
- **Theme System**: MUI theme with custom configuration

## Technology Stack

### Core
- **React**: v19.1.1
- **React Router**: v7.9.5 (with hash link support)
- **Vite**: v6+ (build tool)

### UI Libraries
- **Material-UI (MUI)**: v7.3.5
  - Core components
  - Icons
  - Data Grid
  - Charts
  - Date Pickers
  - Lab components
- **Tailwind CSS**: v4.1.16
- **Emotion**: CSS-in-JS

### Workflow & Visualization
- **@xyflow/react**: v12.9.2 (React Flow)
- **Recharts**: v3.5.0
- **MUI X-Charts**: v8.20.0

### Forms & Validation
- **React JSON Schema Form**: v6.1.2
  - Core, MUI bindings
  - AJV8 validator

### Utilities
- **i18next**: v25.6.3 (internationalization)
- **react-i18next**: v16.3.5
- **dayjs**: v1.11.19 (date handling)
- **react-markdown**: v10.1.0
- **react-toastify**: v11.0.5 (notifications)
- **js-cookie**: v3.0.5
- **Swiper**: v12.0.3 (carousels)
- **Lucide React**: v0.555.0 (icons)

## Environment Variables

```env
# Backend API Configuration
VITE_API_SERVER=http://localhost:8081

# WebSocket Configuration  
VITE_WS_SERVER=ws://localhost:8081

# Postgres Server
VITE_POSTGRES_SERVER=http://localhost:8001

# Contract Parser WebSocket
VITE_CONTRACT_PARSER=http://localhost:8000/ws

# Asset Base URL (optional)
VITE_ASSET_BASE_URL=""
```
## Deployment

### Production Build Only

The frontend is designed to be served as a static build:

```bash
npm run build
# Outputs to dist/ directory
```

Deploy the `dist` folder to any static hosting service:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages
- Any web server (nginx, Apache)

### Serving Built Files

```bash
# Using serve
npm install -g serve
serve -s dist -p 5173

# Using Python
python -m http.server 5173 -d dist

# Using Node.js http-server
npx http-server dist -p 5173
```

## Key Features Implementation

### Undo/Redo System
The workflow editor includes a full undo/redo system implemented via `useUndoRedo` hook:
- Node additions/removals
- Edge connections/deletions
- Node movements
- Property updates
- Keyboard shortcuts (Ctrl+Z, Ctrl+Shift+Z)

### WebSocket Reconnection
Automatic reconnection logic with:
- Exponential backoff
- Maximum retry attempts
- Ping/pong health checks
- Connection status tracking
- Manual disconnect handling

### Form Validation
Dynamic forms using React JSON Schema Form:
- Schema-based validation
- MUI-themed components
- AJV8 validator integration
- Custom field widgets

## Performance Optimization

- Lazy load routes with `React.lazy()` (if needed)
- Memoize expensive computations with `useMemo()`
- Optimize re-renders with `React.memo()` and `useCallback()`
- Code splitting via dynamic imports
- Vite's automatic chunk optimization
- WebSocket message batching for high-frequency updates