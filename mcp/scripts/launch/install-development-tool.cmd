@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" (
  echo Usage: install-development-tool.cmd TOOL [-Interface mcp] [-Apply]
  exit /b 2
)
for /f "tokens=2 delims=:" %%C in ('chcp') do set "MCP_SETUP_CODEPAGE=%%C"
chcp 65001 >nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0install-development-tool.ps1" %*
set "MCP_SETUP_EXIT=%ERRORLEVEL%"
if defined MCP_SETUP_CODEPAGE chcp %MCP_SETUP_CODEPAGE% >nul
exit /b %MCP_SETUP_EXIT%
