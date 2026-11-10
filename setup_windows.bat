@echo off
setlocal
cd /d %~dp0

where py >nul 2>nul
if errorlevel 1 goto use_python
set PYTHON_CMD=py
goto python_ready
:use_python
set PYTHON_CMD=python
:python_ready

echo [1/5] Preparing Python backend...
cd backend
if not exist .venv %PYTHON_CMD% -m venv .venv
if errorlevel 1 goto :fail
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto :fail
if not exist .env copy .env.example .env >nul
echo Running database migrations...
alembic upgrade head
if errorlevel 1 goto :fail
cd ..

echo [2/5] Installing exact React dependencies...
cd frontend
call npm install
if errorlevel 1 goto :fail
if not exist .env copy .env.example .env >nul

echo [3/5] Building frontend...
call npm run build
if errorlevel 1 goto :fail
cd ..

echo [4/5] Running backend tests...
cd backend
set PYTHONPATH=.
pytest -q
if errorlevel 1 goto :fail
cd ..

echo [5/5] Setup complete and validated.
echo Run run_windows.bat to start TuberIntel.
exit /b 0

:fail
echo.
echo Setup or validation failed. Review the error above before the demo.
exit /b 1
