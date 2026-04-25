import os
import sys
import subprocess
import platform

def print_step(msg):
    print(f"\n{'-'*60}\n>>> {msg}\n{'-'*60}")

def run_command(cmd, shell=True):
    try:
        subprocess.run(cmd, check=True, shell=shell)
    except subprocess.CalledProcessError as e:
        print(f"\n[LỖI] Lệnh thất bại: {cmd}")
        print(f"Chi tiết: {e}")
        sys.exit(1)

def main():
    print("="*80)
    print(" OCR-LLM - TỰ ĐỘNG CÀI ĐẶT MÔI TRƯỜNG (PHASE 0)".center(80))
    print("="*80)

    # 1. Kiểm tra Conda
    if "CONDA_DEFAULT_ENV" not in os.environ:
        print("[CẢNH BÁO] Bạn không chạy trong môi trường Conda (Miniconda/Anaconda).")
        print("Đề xuất:")
        print("1. Mở Anaconda Prompt.")
        print("2. Chạy: conda create -n ocr_llm python=3.10 -y")
        print("3. Chạy: conda activate ocr_llm")
        print("4. Chạy lại script này: python setup_env.py")
        
        reply = input("\nBạn có chắc chắn muốn tiếp tục cài đặt trực tiếp không? (y/N): ")
        if reply.lower() != 'y':
            sys.exit(0)
    else:
        print(f"[*] Môi trường Conda hiện tại: {os.environ['CONDA_DEFAULT_ENV']}")

    # 2. Cài đặt PyTorch với CUDA 12.1 (Tối ưu cho RTX 30xx/40xx/50xx)
    print_step("Bước 1: Cài đặt PyTorch (CUDA 12.1)")
    pytorch_cmd = f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    run_command(pytorch_cmd)

    # 3. Cài đặt các thư viện lõi từ requirements.txt
    print_step("Bước 2: Cài đặt các thư viện phụ thuộc (requirements.txt)")
    if os.path.exists("requirements.txt"):
        pip_cmd = f"{sys.executable} -m pip install -r requirements.txt"
        run_command(pip_cmd)
    else:
        print("[LỖI] Không tìm thấy file requirements.txt")
        sys.exit(1)

    # 4. Xác nhận môi trường
    print_step("Bước 3: Kiểm tra thiết lập")
    try:
        import torch
        print(f"[*] PyTorch Version: {torch.__version__}")
        print(f"[*] CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[*] Thiết bị GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("[CẢNH BÁO] Không thể import torch. Vui lòng kiểm tra lại quá trình cài đặt.")

    print("\n" + "="*80)
    print(" CÀI ĐẶT THÀNH CÔNG! HỆ THỐNG ĐÃ SẴN SÀNG CHO PHASE 1.".center(80))
    print("="*80)

if __name__ == "__main__":
    main()
