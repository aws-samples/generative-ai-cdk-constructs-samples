#!/bin/bash
# Wrapper for travel-agent that uses the virtual environment
PROJECT_DIR="/Users/dinsajwa/work/projects/agentcore-demo"
source "$PROJECT_DIR/agent/.venv/bin/activate"
python3 "$PROJECT_DIR/travel-agent" "$@"
