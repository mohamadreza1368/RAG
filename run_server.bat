@echo off
chcp 65001 > nul
echo ========================================================
echo   Starting Unified RAG Ecosystem Web Server...
echo ========================================================
echo.
python run_server.py --host 0.0.0.0 --port 8000
pause
