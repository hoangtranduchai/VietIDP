@echo off
chcp 65001 >nul
setlocal

echo ==============================================
echo        HE THONG TRI TUE NHAN TAO VIETIDP
echo          VietIDP OCR-LLM Pipeline v3.0
echo     Canonical stack: FastAPI + React/Vite
echo ==============================================
echo.

set "ROOT=%~dp0"
set "PYTHON_EXE=%ROOT%.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

if not exist "%ROOT%apps\frontend\node_modules" (
    echo [*] Dang cai dat thu vien cho Frontend...
    pushd "%ROOT%apps\frontend"
    call npm install
    popd
)

echo [1/3] Dang danh thuc May chu AI (Ollama)...
start "Ollama Server" /MIN cmd /c "ollama serve"

echo [2/3] Dang khoi dong FastAPI Backend (port 8000)...
start "VietIDP FastAPI" /MIN cmd /c "cd /d %ROOT% && %PYTHON_EXE% -m uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000"

echo [3/3] Dang mo Giao dien Web (port 5173)...
start "VietIDP Frontend" /MIN cmd /c "cd /d %ROOT%apps\frontend && npx vite --port 5173"

echo.
echo He thong dang duoc ket noi... Vui long doi 5 giay!
timeout /t 5 >nul
start http://localhost:5173

echo.
echo ==============================================
echo [!] XONG! Trang web da duoc mo tren trinh duyet.
echo.
echo     Frontend: http://localhost:5173
echo     Backend:  http://localhost:8000
echo     API Docs: http://localhost:8000/docs
echo     Ollama:   http://localhost:11434
echo.
echo [i] Dev legacy path van co the dung qua start_dev.bat khi can.
echo ==============================================
pause
