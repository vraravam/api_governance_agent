# MCP Server Launcher Script for Windows (PowerShell)
# This ensures the correct Python interpreter and PYTHONPATH are used

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set PYTHONPATH to include the src directory
$env:PYTHONPATH = "$ScriptDir\..\src;$env:PYTHONPATH"

# Use the virtual environment Python
& "$ScriptDir\..\.venv\Scripts\python.exe" "$ScriptDir\..\src\mcp_server\server.py" $args
