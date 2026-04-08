@echo off
chcp 65001 >nul
echo =========================================================
echo   CAI DAT MOI TRUONG CONDA - VIETIDP (RTX GPU / 64GB RAM)
echo =========================================================
echo.

:: Kiem tra xem Conda (Miniconda) da duoc cai dat chua
where conda >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Khong tim thay Miniconda tren may nay.
    echo [*] Vui long truy cap https://docs.anaconda.com/free/miniconda/ de tai!
    echo [*] Cai dat Miniconda3 Windows 64-bit roi mo "Anaconda Prompt" de thu lai.
    pause
    exit /b
)

echo [*] Dang tien hanh doc file environment.yml...
echo [*] Qua trinh nay se tu dong tai PyTorch CUDA 12.1 va cac thu vien.
echo [*] Xin vui long cho doi (co the mat 5-10 phut tuy mang)...
echo.

call conda env create -f environment.yml

if %ERRORLEVEL% equ 0 (
    echo.
    echo =========================================================
    echo [OK] DA CAI DAT XONG MOI TRUONG!
    echo =========================================================
    echo.
    echo De bat dau project, xin hay dung lenh:
    echo    conda activate vietidp
    echo.
) else (
    echo.
    echo [Loi] Co loi xay ra trong qua trinh tao moi truong phia tren.
    echo Vui long kiem tra lai mang hoac xem chi tiet loi ben tren.
)

pause
