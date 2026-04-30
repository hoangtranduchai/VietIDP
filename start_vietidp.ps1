# VietIDP - Script khoi dong he thong Canonical Stack (PowerShell)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaCli = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   HE THONG AI VIETIDP (FastAPI + React/Vite)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

if (!(Test-Path "$Root\apps\frontend\node_modules")) {
    Write-Host "`n[*] Phat hien chua cai dat thu vien Frontend. Dang cai dat tu dong..." -ForegroundColor Magenta
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd apps\frontend && npm install" -WorkingDirectory $Root -Wait
    Write-Host "    Hoan tat cai dat Frontend!" -ForegroundColor Green
}

Write-Host "`n[1/3] Bat may chu AI Ollama..." -ForegroundColor Yellow
Start-Process -FilePath $OllamaCli -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 5

Write-Host "[2/3] Khoi dong FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "src.api.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $Root -WindowStyle Hidden

Write-Host "[3/3] Khoi dong Giao dien Web (Port 5173)..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "node_modules/vite/bin/vite.js", "--port", "5173" -WorkingDirectory "$Root\apps\frontend" -WindowStyle Hidden

Write-Host "`n[ ] Doi 8 giay roi mo trinh duyet..." -ForegroundColor Gray
Start-Sleep -Seconds 8
Start-Process "http://localhost:5173"

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "[OK] VietIDP dang chay voi FastAPI + React/Vite" -ForegroundColor Green
Write-Host "     Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "     Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "     API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "     Dev path legacy: start_dev.bat" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Green
Read-Host "`nNhan Enter de dong cua so nay"
