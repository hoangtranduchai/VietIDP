# VietIDP - One-Click Start/Stop Script (PowerShell)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaCli = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$PythonExe = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# 1. KIEM TRA XEM HE THONG CANONICAL STACK CO DANG CHAY KHONG
$nodeRunning = Get-Process -Name "node" -ErrorAction SilentlyContinue
$pythonRunning = Get-Process -Name "python" -ErrorAction SilentlyContinue
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue

if ($nodeRunning -or $pythonRunning -or $ollamaRunning) {
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host "   DANG TAT HE THONG VIETIDP..." -ForegroundColor Magenta
    Write-Host "==============================================" -ForegroundColor Magenta

    Stop-Process -Name 'node' -Force -ErrorAction SilentlyContinue
    Stop-Process -Name 'python' -Force -ErrorAction SilentlyContinue
    Stop-Process -Name 'ollama' -Force -ErrorAction SilentlyContinue

    Write-Host "`n[OK] Da TAT toan bo he thong an (FastAPI, Frontend, AI)!" -ForegroundColor Green
    Write-Host "Chuc ban xài trâu cày nghỉ ngơi vui vẻ. Cửa sổ sẽ tự đóng..." -ForegroundColor Gray
    Start-Sleep -Seconds 4
    exit
}

# 2. NEU CHUA CHAY THI TIEN HANH KHOI DONG CANONICAL STACK
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
Write-Host "==============================================" -ForegroundColor Green
Start-Sleep -Seconds 4
