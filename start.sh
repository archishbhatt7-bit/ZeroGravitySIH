#!/bin/bash

echo "Starting OrbVeil Backend..."
python -m uvicorn src.orbveil.api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting OrbVeil Frontend..."
cd dashboard && npm run dev &
FRONTEND_PID=$!

wait $BACKEND_PID
wait $FRONTEND_PID
