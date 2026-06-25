@echo off
title Forex Analysis Platform
echo ============================================
echo   Forex Analysis Platform - Launcher
echo ============================================
echo.

set PROJECT_DIR=%~dp0
set VENV=%PROJECT_DIR%venv\Scripts
set BACKEND=%PROJECT_DIR%backend
set FRONTEND=%PROJECT_DIR%frontend

:: Check Redis
echo [1/4] Checking Redis...
"C:\Program Files\Redis\redis-cli.exe" ping >nul 2>&1
if errorlevel 1 (
    echo       Starting Redis server...
    start "Redis" /min "C:\Program Files\Redis\redis-server.exe"
    timeout /t 2 /nobreak >nul
) else (
    echo       Redis is running.
)

:: Start Django (Daphne ASGI server)
echo [2/4] Starting Django backend (Daphne on port 8000)...
start "Django Backend" cmd /k "cd /d %BACKEND% && %VENV%\python.exe -m daphne -b 127.0.0.1 -p 8000 backend.asgi:application"
timeout /t 2 /nobreak >nul

:: Start Celery worker + beat
echo [3/4] Starting Celery worker + beat...
start "Celery Worker" cmd /k "cd /d %BACKEND% && %VENV%\celery.exe -A backend worker --loglevel=info --pool=solo"
timeout /t 1 /nobreak >nul
start "Celery Beat" cmd /k "cd /d %BACKEND% && %VENV%\celery.exe -A backend beat --loglevel=info"
timeout /t 1 /nobreak >nul

:: Start UI5 frontend
echo [4/4] Starting UI5 frontend (port 8080)...
start "UI5 Frontend" cmd /k "cd /d %FRONTEND% && npx ui5 serve --open index.html --port 8080"

echo.
echo ============================================
echo   All services started!
echo.
echo   Frontend:  http://localhost:8080
echo   Backend:   http://localhost:8000
echo   WebSocket: ws://localhost:8000/ws/
echo.
echo   Close this window or press Ctrl+C to stop.
echo   Run stop.bat to kill all services.
echo ============================================
echo.
pause
