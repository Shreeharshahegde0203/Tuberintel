@echo off
cd /d %~dp0
if not exist backend\.venv\Scripts\python.exe (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist frontend\node_modules (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
start "TuberIntel Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "TuberIntel Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo TuberIntel is starting. Open http://localhost:5173
