#!/bin/bash
# MCP Server Launcher Script
# This ensures the correct Python interpreter and PYTHONPATH are used

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Set PYTHONPATH to include the src directory
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Ensure venv is on PATH
export PATH="$PROJECT_ROOT/.venv/bin:$PATH"

# Use the virtual environment Python
# If direnv is active, this will use the direnv-managed Python
# Otherwise, falls back to explicit .venv path
if command -v python3 &> /dev/null && [[ "$VIRTUAL_ENV" != "" ]]; then
    # direnv or venv is active
    exec python3 "$PROJECT_ROOT/src/mcp_server/server.py" "$@"
else
    # Fallback to explicit venv path
    exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/src/mcp_server/server.py" "$@"
fi
