@echo off
chcp 65001 >nul
echo ==============================================
echo        HE THONG TRI TUE NHAN TAO VIETIDP
echo          VietIDP OCR-LLM Pipeline v2.0
echo   (Tich hop YOLOv8 + PaddleOCR + Qwen2.5)
echo ==============================================
echo.

if not exist "%~dp0\apps\backend\node_modules" (
    echo [*] Dang cai dat thu vien cho Backend...
    cd "%~dp0\apps\backend"
    call npm install
)

if not exist "%~dp0\apps\frontend\node_modules" (
    echo [*] Dang cai dat thu vien cho Frontend...
    cd "%~dp0\apps\frontend"
    call npm install
)

echo [1/3] Dang danh thuc May chu AI (Ollama)...
start "Ollama Server" /MIN cmd /c "ollama serve"

echo [2/3] Dang khoi dong Backend API (port 5000)...
cd "%~dp0\apps\backend"
start "VietIDP Backend" /MIN cmd /c "node index.js"

echo [3/3] Dang mo Giao dien Web (port 5173)...
cd "%~dp0\apps\frontend"
start "VietIDP Frontend" /MIN cmd /c "npx vite --port 5173"

echo.
echo He thong dang duoc ket noi... Vui long doi 5 giay!
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ==============================================
echo [!] XONG! Trang web da duoc mo tren trinh duyet.
echo.
echo     Frontend: http://localhost:5173
echo     Backend:  http://localhost:5000
echo     Ollama:   http://localhost:11434
echo.
echo [!] De tat he thong, dong 3 cua so mau den dang thu nho.
echo ==============================================
pause
