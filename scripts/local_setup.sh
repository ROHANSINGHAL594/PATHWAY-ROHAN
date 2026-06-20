#!/bin/bash
# TODO: Change to production

# --- Configuration ---
# Set the name of the virtual environment directory
API_VENV_DIR="backend/api_venv"
# Set the path to your requirements file
API_REQS_FILE="backend/api/requirements.txt"

PID_DIR="deploy/pids"
LOG_DIR="deploy/logs"


PIPELINE_IMAGE_NAME="backend-pipeline:latest"
POSTGRES_IMAGE_NAME="backend-postgres:latest"
AGENTIC_IMAGE_NAME="backend-agentic:latest"


# Server ports
API_SERVER_PORT=8081

FRONTEND_PORT=8083
# ---------------------

# Stop the script if any command fails
set -e

# Create the PID directory if it doesn't exist
mkdir -p $PID_DIR
mkdir -p $LOG_DIR

## 1. Check for Python 3
echo "Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    # 2. Error and Exit if not found
    echo "Error: python3 is not installed. Please install it to continue." >&2
    exit 1
fi

echo "Python 3 found."

## 3. Create Virtual Environment for API
if [ ! -d "$API_VENV_DIR" ]; then
    echo "Creating virtual environment in './$API_VENV_DIR'..."
    python3 -m venv $API_VENV_DIR
else
    echo "Virtual environment './$API_VENV_DIR' already exists. Skipping creation."
fi

## 4. Activate Venv and Install Requirements for API
    echo "Activating virtual environment..."
    source "$API_VENV_DIR/bin/activate"
    pip install --upgrade pip
    if [ -f "$API_REQS_FILE" ]; then
        echo "Installing requirements from $API_REQS_FILE..."
        pip install -r $API_REQS_FILE > $LOG_DIR/pip.log 
        echo "Requirements installed."
    else
        echo "Warning: '$API_REQS_FILE' not found. Skipping dependency installation."
    fi

## 5. Checking if the docker images exist
    # Check if Docker daemon is running and the required image exist
    if ! docker version > /dev/null 2>&1; then
        echo "Error: Docker daemon is not running."
        exit 1
    fi
    echo "Docker daemon is up and running."

    if [ -z "$(docker images -q "$PIPELINE_IMAGE_NAME" 2> /dev/null)" ]; then
        echo "Image '$PIPELINE_IMAGE_NAME' does not exist locally."
        exit 1
    fi
    echo "Image '$PIPELINE_IMAGE_NAME' exists locally."

    if [ -z "$(docker images -q "$POSTGRES_IMAGE_NAME" 2> /dev/null)" ]; then
        echo "Image '$POSTGRES_IMAGE_NAME' does not exist locally."
        exit 1
    fi
    echo "Image '$POSTGRES_IMAGE_NAME' exists locally."

    if [ -z "$(docker images -q "$AGENTIC_IMAGE_NAME" 2> /dev/null)" ]; then
        echo "Image '$AGENTIC_IMAGE_NAME' does not exist locally."
        exit 1
    fi
    echo "Image '$AGENTIC_IMAGE_NAME' exists locally."

## 6. Starting up fast api
    echo "Starting FastAPI servers in background..."

    # Use nohup to keep the server running after the script exits.
    # Redirect stdout (>) and stderr (2>&1) to a log file.
    # Run in the background (&).
    export PIPELINE_IMAGE_NAME POSTGRES_IMAGE_NAME AGENTIC_IMAGE_NAME && nohup uvicorn backend.api.main:app --port $API_SERVER_PORT > $LOG_DIR/api.log 2>&1 &
    API_PID=$!
    echo $API_PID > "$PID_DIR/api.pid"

    # Print the Process ID (PID) of the background job
    echo "API Server started with PID: $API_PID"
    echo "You can monitor the logs with: tail -f $LOG_DIR/api.log"

    echo "---"
# 7. setting up the frontend
    cd frontend
    echo "Installing npm packages..."
    npm install > ../$LOG_DIR/frontend.log
    cd ..

    ## 7. Start Frontend
    echo "Starting frontend..."
    cd frontend

    echo "Starting frontend dev server..."
    # The --port option for Vite is passed directly
    export VITE_API_SERVER="http://localhost:$API_SERVER_PORT" && nohup npm run dev -- --port $FRONTEND_PORT > ../$LOG_DIR/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "../$PID_DIR/frontend.pid"
    cd ..

    # Print the Process ID (PID) of the background job
    echo "Frontend started with PID: $FRONTEND_PID"
    echo "You can monitor the logs with: tail -f $LOG_DIR/frontend.log"

    echo "---"

## 8. Start Contract Parser Agent Server
    echo "Starting Contract Parser Agent server..."
    cd backend/contractparseragent/server
    nohup python server.py > ../../../$LOG_DIR/contractparseragent.log 2>&1 &
    CONTRACTPARSERAGENT_PID=$!
    echo $CONTRACTPARSERAGENT_PID > "../../../$PID_DIR/contractparseragent.pid"
    cd ../../..

    echo "Contract Parser Agent server started with PID: $CONTRACTPARSERAGENT_PID"
    echo "You can monitor the logs with: tail -f $LOG_DIR/contractparseragent.log"

    echo "---"

echo "Setup script finished."
echo "To stop all services, run: ./scripts/stop.sh"













