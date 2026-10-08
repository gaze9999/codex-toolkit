@echo off
setlocal
set "MCP_SETUP_PYTHON_VERSION="
where py >nul 2>nul
if errorlevel 1 goto try_python
for %%V in (3 3.13 3.12 3.11) do if not defined MCP_SETUP_PYTHON_VERSION call :probe_py %%V
if not defined MCP_SETUP_PYTHON_VERSION goto try_python
goto launch_py
:try_python
where python >nul 2>nul
if errorlevel 1 goto missing
call python -I -B -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto missing
set "MCP_SETUP_PYTHON_KIND=python"
:launch
call python -X utf8 -B "%~dp0..\bootstrap_mcp.py" %*
exit /b %ERRORLEVEL%
:launch_py
call py -%MCP_SETUP_PYTHON_VERSION% -X utf8 -B "%~dp0..\bootstrap_mcp.py" %*
exit /b %ERRORLEVEL%
:missing
echo Select an existing Python 3.11+ using py or PATH python 1>&2
exit /b 2
:probe_py
call py -%~1 -I -B -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 set "MCP_SETUP_PYTHON_VERSION=%~1"
exit /b 0
