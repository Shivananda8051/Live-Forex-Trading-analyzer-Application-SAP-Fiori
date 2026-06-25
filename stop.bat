@echo off
echo Stopping Forex Platform services...
taskkill /FI "WINDOWTITLE eq Django Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Celery Worker*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Celery Beat*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq UI5 Frontend*" /T /F >nul 2>&1
echo All services stopped.
pause
