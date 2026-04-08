# VietIDP - Script khoi dong he thong MLOps Version (PowerShell)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaCli = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   HE THONG AI VIETIDP (MLOps v2.0) - BOOTING" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Kiem tra va cai dat thu vien Backend neu chua co
if (!(Test-Path "$Root\apps\backend\node_modules")) {
    Write-Host "`n[*] Phat hien chua cai dat thu vien Backend. Dang cai dat tu dong..." -ForegroundColor Magenta
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd apps\backend && npm install" -WorkingDirectory $Root -Wait
    Write-Host "    Hoan tat cai dat Backend!" -ForegroundColor Green
}

# Kiem tra va cai dat thu vien Frontend neu chua co
if (!(Test-Path "$Root\apps\frontend\node_modules")) {
    Write-Host "`n[*] Phat hien chua cai dat thu vien Frontend. Dang cai dat tu dong..." -ForegroundColor Magenta
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd apps\frontend && npm install" -WorkingDirectory $Root -Wait
    Write-Host "    Hoan tat cai dat Frontend!" -ForegroundColor Green
}

# Buoc 1: Bat Ollama Server (an hoan toan)
Write-Host "`n[1/4] Bat may chu AI Ollama..." -ForegroundColor Yellow
Start-Process -FilePath $OllamaCli -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 6

# Buoc 2: Nap model Qwen2.5:7b (an hoan toan)
Write-Host "[2/4] Nap mo hinh Qwen2.5:7B vao GPU..." -ForegroundColor Yellow
Start-Process -FilePath $OllamaCli -ArgumentList "run", "qwen2.5:7b" -WindowStyle Hidden
Start-Sleep -Seconds 6

# Buoc 3: Bat Backend
Write-Host "[3/4] Khoi dong Backend API..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "index.js" -WorkingDirectory "$Root\apps\backend" -WindowStyle Hidden

# Buoc 4: Bat Frontend
Write-Host "[4/4] Khoi dong Giao dien Web (Port 5173)..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "node_modules/vite/bin/vite.js", "--port", "5173" -WorkingDirectory "$Root\apps\frontend" -WindowStyle Hidden

# Mo trinh duyet
Write-Host "`n[ ] Doi 8 giay roi mo trinh duyet..." -ForegroundColor Gray
Start-Sleep -Seconds 8
Start-Process "http://localhost:5173"

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "[OK] VietIDP v2.0 dang chay ngam hoan hao!" -ForegroundColor Green
Write-Host "     De TAT he thong: Chay file 'stop_vietidp.bat'" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Green
Read-Host "`nNhan Enter de dong cua so nay"
