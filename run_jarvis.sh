#!/bin/bash

# Script to run Jarvis with both backend and frontend

echo "🤖 Starting Jarvis Personal Assistant..."
echo ""

# Check if backend is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend already running on port 8000"
else
    echo "🚀 Starting backend server..."
    uv run python server.py &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
    sleep 3
fi

echo ""
echo "🎨 Starting Streamlit frontend..."
echo "Frontend will open in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start Streamlit from project root (so imports work)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT"
uv run streamlit run frontend/app.py

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT
