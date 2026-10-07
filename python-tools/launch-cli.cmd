@echo off
setlocal
if exist "%~dp0.venv\Scripts\python.exe" goto localpython
if exist "%~dp0.venv-gui\Scripts\python.exe" goto legacypython
python "%~dp0launch-cli.py" %*
exit /b %errorlevel%
:localpython
"%~dp0.venv\Scripts\python.exe" "%~dp0launch-cli.py" %*
exit /b %errorlevel%
:legacypython
"%~dp0.venv-gui\Scripts\python.exe" "%~dp0launch-cli.py" %*
exit /b %errorlevel%
