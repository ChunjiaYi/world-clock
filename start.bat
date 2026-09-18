@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
) else (
  set "PYTHON_CMD=python"
)
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import importlib.metadata as m; assert m.version('PySide6-Essentials') == '6.8.3'; assert m.version('tzdata') == '2026.4'" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
start "World Clock" ".venv\Scripts\pythonw.exe" "world_clock.py"
exit /b 0
:failed
echo Setup failed. Install Python 3.10+ from python.org and enable PATH.
echo Check the internet connection, then run this file again.
pause
exit /b 1
