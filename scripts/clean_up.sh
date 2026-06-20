#!/usr/bin/env bash

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <pipeline_id>"
  exit 1
fi

PIPELINE_ID="$1"

AGENTIC="agentic_${PIPELINE_ID}"
DB="db_${PIPELINE_ID}"
PIPELINE="${PIPELINE_ID}"
NETWORK="net_${PIPELINE_ID}"

echo "Removing containers:"
docker rm -f "$AGENTIC" "$DB" "$PIPELINE" 2>/dev/null || true

echo "Removing network:"
docker network rm "$NETWORK" 2>/dev/null || true

echo "Cleanup complete for pipeline_id: $PIPELINE_ID"
