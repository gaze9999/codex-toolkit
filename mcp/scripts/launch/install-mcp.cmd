@echo off
setlocal DisableDelayedExpansion
for /f "tokens=2 delims=:" %%C in ('chcp') do set "MCP_SETUP_CODEPAGE=%%C"
chcp 65001 >nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0install-mcp.ps1" %*
set "MCP_SETUP_EXIT=%ERRORLEVEL%"
if defined MCP_SETUP_CODEPAGE chcp %MCP_SETUP_CODEPAGE% >nul
exit /b %MCP_SETUP_EXIT%
