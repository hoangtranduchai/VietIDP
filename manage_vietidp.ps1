# VietIDP - One-Click Start/Stop Script (PowerShell)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. KIEM TRA XEM HE THONG CO DANG CHAY KHONG
$nodeRunning = Get-Process -Name "node" -ErrorAction SilentlyContinue
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue

if ($nodeRunning -or $ollamaRunning) {
    Write-Host "==============================================" -ForegroundColor Magenta
    Write-Host "   DANG TAT HE THONG VIETIDP..." -ForegroundColor Magenta
    Write-Host "==============================================" -ForegroundColor Magenta
    
    Stop-Process -Name 'node' -Force -ErrorAction SilentlyContinue
    Stop-Process -Name 'ollama' -Force -ErrorAction SilentlyContinue
    
    Write-Host "`n[OK] Da TAT toan bo he thong an (Backend, Frontend, AI)!" -ForegroundColor Green
    Write-Host "Chuc ban xài trâu cày nghỉ ngơi vui vẻ. Cửa sổ sẽ tự đóng..." -ForegroundColor Gray
    Start-Sleep -Seconds 4
    exit
}

# 2. NEU CHUA CHAY THI TIEN HANH KHOI DONG
$OllamaCli = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "   HE THONG AI VIETIDP (MLOps v2.0) - BOOTING" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Kiem tra thu vien
if (!(Test-Path "$Root\apps\backend\node_modules")) {
    Write-Host "`n[*] Đang tự động cài thư viện Backend..." -ForegroundColor Magenta
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd apps\backend && npm install" -WorkingDirectory $Root -Wait
}
if (!(Test-Path "$Root\apps\frontend\node_modules")) {
    Write-Host "`n[*] Đang tự động cài thư viện Frontend..." -ForegroundColor Magenta
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd apps\frontend && npm install" -WorkingDirectory $Root -Wait
}

# 3. KIEM TRA VA IMPORT MODEL YOLO (Neu nguoi dung quen copy khi chuyen o dia)
$TargetModelPath = "$Root\models\stamp_model\weights\best.pt"
$SourceModelPath = "C:\Users\LAPTOP T&T\Desktop\AI_Science\ai\models\stamp_model\weights\best.pt"
if (!(Test-Path $TargetModelPath)) {
    if (Test-Path $SourceModelPath) {
        Write-Host "`n[*] Phat hien thieu model AI! Dang tu dong import model tu Thu muc Desktop cu..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Force -Path "$Root\models\stamp_model\weights" | Out-Null
        Copy-Item -Path $SourceModelPath -Destination $TargetModelPath -Force
        Write-Host "    [OK] Da Import model tieu chuan thanh cong!" -ForegroundColor Green
    } else {
        Write-Host "`n[!] KHONG TIM THAY MODEL NHAN DIEN (best.pt)! AI se chay o che do Mo Phong (Mock)." -ForegroundColor Yellow
    }
}

Write-Host "`n[1/4] Bat may chu AI (Ollama)..." -ForegroundColor Yellow
Start-Process -FilePath $OllamaCli -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 6

Write-Host "[2/4] Nap mo hinh Qwen2.5:1.5B vao GPU..." -ForegroundColor Yellow
Start-Process -FilePath $OllamaCli -ArgumentList "run", "qwen2.5:1.5b" -WindowStyle Hidden
Start-Sleep -Seconds 6

Write-Host "[3/4] Bat Backend API..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "index.js" -WorkingDirectory "$Root\apps\backend" -WindowStyle Hidden

Write-Host "[4/4] Bat Giao dien Web..." -ForegroundColor Yellow
Start-Process -FilePath "node" -ArgumentList "node_modules/vite/bin/vite.js", "--port", "5173" -WorkingDirectory "$Root\apps\frontend" -WindowStyle Hidden

Write-Host "`n[ ] Doi 8 giay roi mo trinh duyet..." -ForegroundColor Gray
Start-Sleep -Seconds 8
Start-Process "http://localhost:5173"

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "[OK] VietIDP dang chay hoan toan an!" -ForegroundColor Green
Write-Host "     => De TAT he thong, HAY NHAN DUP VAO FILE BAT NAY 1 LAN NUA!" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Green
Start-Sleep -Seconds 4
