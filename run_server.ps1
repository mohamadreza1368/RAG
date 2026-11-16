# Unified RAG Ecosystem Server Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting Unified RAG Ecosystem Web Server..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Web Interface: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Default Admin: admin / admin123" -ForegroundColor Yellow
Write-Host ""

python run_server.py --host 0.0.0.0 --port 8000
