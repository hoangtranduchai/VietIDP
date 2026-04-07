# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="vietidp",
    version="2.0.0",
    description="Vietnamese Intelligent Document Processing - OCR + LLM Pipeline",
    author="VietIDP Research Team",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "opencv-python-headless>=4.8.0",
        "Pillow>=10.0.0",
        "numpy>=1.24.0",
        "PyMuPDF>=1.23.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "ocr": [
            "paddlepaddle>=2.6.0",
            "paddleocr>=2.7.0",
        ],
        "gpu": [
            "torch>=2.0.0",
            "torchvision>=0.15.0",
            "paddlepaddle-gpu>=2.6.0",
            "paddleocr>=2.7.0",
        ],
        "finetune": [
            "torch>=2.0.0",
            "transformers>=4.40.0",
            "datasets>=2.18.0",
            "accelerate>=0.28.0",
            "peft>=0.10.0",
            "bitsandbytes>=0.43.0",
            "trl>=0.8.0",
        ],
        "api": [
            "fastapi>=0.110.0",
            "uvicorn>=0.29.0",
            "python-multipart>=0.0.9",
        ],
        "dev": [
            "scikit-image>=0.21.0",
            "matplotlib>=3.8.0",
            "tensorboard>=2.15.0",
        ],
    },
)
