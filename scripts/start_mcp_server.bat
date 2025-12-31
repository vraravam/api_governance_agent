@echo off
REM MCP Server Launcher Script for Windows (Batch)
REM This ensures the correct Python interpreter and PYTHONPATH are used

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Set PYTHONPATH to include the src directory
set PYTHONPATH=%SCRIPT_DIR%\..\src;%PYTHONPATH%

REM Use the virtual environment Python
"%SCRIPT_DIR%\..\.venv\Scripts\python.exe" "%SCRIPT_DIR%\..\src\mcp_server\server.py" %*
