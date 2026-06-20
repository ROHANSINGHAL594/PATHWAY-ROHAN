#!/bin/bash

# Stop API server (port 8081)
kill -9 $(lsof -t -i :8081) 

# Stop Frontend (port 8083)
kill -9 $(lsof -t -i :8083) 

# Stop Contract Parser Agent server (port 8000)
kill -9 $(lsof -t -i :8000) 

echo "All services stopped."
