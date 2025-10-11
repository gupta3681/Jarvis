#!/bin/bash

# Run FastAPI backend server

cd "$(dirname "$0")"
uv run python server.py
