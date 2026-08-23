#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting ZeroGravity Backend..."
cd "$SCRIPT_DIR"
PYTHONPATH=src python -m uvicorn orbveil.api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting ZeroGravity Frontend..."
cd "$SCRIPT_DIR/dashboard" && npm run dev &
FRONTEND_PID=$!

wait $BACKEND_PID
wait $FRONTEND_PID
