#!/bin/bash

# Script to start the FastAPI backend server

echo "Starting BB Arena Optimizer Backend Server..."

# Change to the project root directory
cd "$(dirname "$0")/.."

# Install dependencies if needed
echo "Installing Python dependencies..."
pip install -e .

# Start the FastAPI server
echo "Starting FastAPI server on http://localhost:8000"
python -m bb_arena_optimizer.api.server
