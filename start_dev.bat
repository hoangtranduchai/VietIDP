@echo off
chcp 65001 >nul 2>&1
REM =============================================================
REM  VietIDP - Dev Startup (Anaconda Prompt)
REM  Su dung Miniconda env "vietidp" voi GPU (RTX 5070)
REM =============================================================
REM
REM CACH DUNG: Mo Anaconda Prompt, chay:
REM   cd /d E:\OCR-LLM_Research\OCR-LLM_Research
REM   start_dev.bat
REM =============================================================

title VietIDP

echo.
echo  ============================================================
echo     VietIDP v3.0
echo     GPU: RTX 5070 8GB  -  LLM: Qwen2.5-7B
echo  ============================================================
echo.

REM -- Step 1: Activate conda env --
echo [1/6] Activating conda environment: vietidp
call conda activate vietidp
if errorlevel 1 (
    echo   ERROR: conda env "vietidp" not found!
    echo   Create it: conda create -n vietidp python=3.10 -y
    pause
    exit /b 1
)
echo   OK: vietidp activated

REM -- Step 2: Check GPU --
echo [2/6] Checking GPU...
python -c "import torch; print('  CUDA:', torch.cuda.is_available()); print('  GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'); print('  VRAM:', round(torch.cuda.get_device_properties(0).total_memory/1024**3,1), 'GB' if torch.cuda.is_available() else 'N/A')"
if errorlevel 1 (
    echo   WARNING: PyTorch not found or CUDA error
    echo   Install: pip install torch --index-url https://download.pytorch.org/whl/cu128
)

REM -- Step 3: Check dependencies --
echo [3/6] Checking dependencies...
python -c "import fastapi, uvicorn, sqlalchemy; print('  OK: Backend deps ready')" 2>nul
if errorlevel 1 (
    echo   Installing missing dependencies...
    pip install fastapi uvicorn[standard] python-multipart sqlalchemy psycopg2-binary
)

REM -- Step 4: Check Ollama --
echo [4/6] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo   Starting Ollama server...
    start /min "Ollama" ollama serve
    timeout /t 5 /nobreak >nul
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo   WARNING: Ollama failed to start. Run manually: ollama serve
    ) else (
        echo   OK: Ollama started
    )
) else (
    echo   OK: Ollama is running
)

REM -- Step 5: Check model --
echo [5/6] Checking Qwen2.5-7B model...
ollama list 2>nul | findstr /C:"qwen2.5" >nul
if errorlevel 1 (
    echo   Pulling qwen2.5:7b - first time download about 4.7GB...
    ollama pull qwen2.5:7b
) else (
    echo   OK: qwen2.5:7b available
)

REM -- Step 6: Start servers --
echo [6/6] Starting services...
echo.

REM Start Frontend in new window
echo   Starting Frontend on port 5173...
start "VietIDP Frontend" cmd /k "cd /d %~dp0apps\frontend && npm run dev"

REM Start Backend (this window)
echo.
echo  ============================================================
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
echo   Press Ctrl+C to stop backend
echo  ============================================================
echo.

uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
