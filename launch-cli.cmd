@echo off
setlocal DisableDelayedExpansion
for /f "tokens=2 delims=:" %%C in ('chcp') do set "CODEX_SETUP_CODEPAGE=%%C"
chcp 65001 >nul
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0launch-cli.ps1" %*
set "CODEX_SETUP_EXIT=%ERRORLEVEL%"
if defined CODEX_SETUP_CODEPAGE chcp %CODEX_SETUP_CODEPAGE% >nul
exit /b %CODEX_SETUP_EXIT%
