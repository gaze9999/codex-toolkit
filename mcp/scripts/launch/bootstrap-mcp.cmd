@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
  python -B "%~dp0..\bootstrap_mcp.py" %*
) else (
  py -3 -B "%~dp0..\bootstrap_mcp.py" %*
)
set "MCP_SETUP_EXIT=%ERRORLEVEL%"
if not "%MCP_SETUP_EXIT%"=="0" echo Setup did not complete. Python 3.11+ is required.
exit /b %MCP_SETUP_EXIT%
