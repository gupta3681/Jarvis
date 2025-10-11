#!/bin/bash

# Run Streamlit frontend with correct Python path

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT"
uv run streamlit run frontend/app.py
