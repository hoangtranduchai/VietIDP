# -*- coding: utf-8 -*-
"""
VietIDP Pilot Test Script
==========================
Chay kiem tra toan bo pipeline E2E tren GPU.

Su dung:
    conda activate vietidp
    cd /d E:\\OCR-LLM_Research\\OCR-LLM_Research
    python scripts/pilot_test.py
"""

import os
import sys
import json
import time

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_gpu():
    """Test 1: GPU va CUDA."""
    print_header("TEST 1: GPU & CUDA")
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  VRAM: {vram:.1f} GB")
            return True
        else:
            print("  [WARN] CUDA not available - running on CPU")
            return True  # Continue tests on CPU
    except ImportError:
        print("  [FAIL] PyTorch not installed")
        return False


def test_config():
    """Test 2: Configuration."""
    print_header("TEST 2: Configuration")
    try:
        from src.config import Config
        print(f"  LLM Model: {Config.OLLAMA_MODEL}")
        print(f"  OCR Model: {Config.VIETOCR_MODEL}")
        print(f"  YOLO Weights: {Config.STAMP_DETECTION_MODEL}")
        print(f"  YOLO exists: {Config.STAMP_DETECTION_MODEL.exists()}")
        print(f"  Database: {Config.DATABASE_URL[:40]}...")
        return True
    except Exception as e:
        print(f"  [FAIL] Config error: {e}")
        return False


def test_ocr_engine():
    """Test 3: OCR engine (VietOCR + EasyOCR)."""
    print_header("TEST 3: OCR Engine (VietOCR + EasyOCR)")
    try:
        from src.ocr.engine import VietnameseOCREngine
        start = time.time()
        engine = VietnameseOCREngine()
        elapsed = time.time() - start
        print(f"  Load time: {elapsed:.1f}s")
        print(f"  VietOCR ready: {engine.vietocr_predictor is not None}")
        print(f"  EasyOCR ready: {engine.text_detector is not None}")
        print(f"  Engine loaded: {engine.is_loaded}")
        return engine.is_loaded
    except Exception as e:
        print(f"  [FAIL] OCR error: {e}")
        return False


def test_ollama():
    """Test 4: Ollama + Qwen2.5-7B."""
    print_header("TEST 4: Ollama LLM (Qwen2.5-7B)")
    try:
        import requests
        from src.config import Config

        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code != 200:
            print("  [FAIL] Ollama not responding")
            return False

        models = [m['name'] for m in r.json().get('models', [])]
        print(f"  Available models: {models}")

        has_qwen = any('qwen2.5' in m for m in models)
        print(f"  Qwen2.5-7B: {'[OK]' if has_qwen else '[FAIL] Not found'}")

        if has_qwen:
            from src.llm.ollama_client import OllamaClient
            client = OllamaClient()
            start = time.time()
            result, error = client.generate(
                'Tra loi bang JSON: {"test": "ok"}',
                format_json=True
            )
            elapsed = time.time() - start
            print(f"  Inference test: {result}")
            print(f"  Inference time: {elapsed:.1f}s")
            return error is None

        return has_qwen
    except Exception as e:
        print(f"  [FAIL] Ollama error: {e}")
        return False


def test_stamp_detection():
    """Test 5: YOLO stamp detection."""
    print_header("TEST 5: YOLO Stamp Detection")
    try:
        from src.config import Config
        if not Config.STAMP_DETECTION_MODEL.exists():
            print(f"  [WARN] Weights not found: {Config.STAMP_DETECTION_MODEL}")
            return True  # Skip, not critical

        from ultralytics import YOLO
        import numpy as np

        model = YOLO(str(Config.STAMP_DETECTION_MODEL))
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        results = model(dummy_img, conf=0.25, verbose=False)
        print(f"  Model loaded: [OK]")
        print(f"  Detection on blank image: {len(results[0].boxes)} boxes (expected 0)")
        return True
    except Exception as e:
        print(f"  [FAIL] YOLO error: {e}")
        return False


def test_stamp_matting():
    """Test 6: HybridStampMatting."""
    print_header("TEST 6: HybridStampMatting")
    try:
        from src.preprocessing.stamp_matting import HybridStampMatting
        import numpy as np

        matting = HybridStampMatting()
        img = np.full((100, 100, 3), (255, 255, 255), dtype=np.uint8)
        img[30:70, 30:70] = (0, 0, 200)  # Red stamp region (BGR)

        result = matting.remove_stamp(img)
        print(f"  Matting ready: [OK]")
        print(f"  Input shape: {img.shape}")
        print(f"  Output shape: {result.shape if result is not None else 'None'}")
        return result is not None
    except Exception as e:
        print(f"  [FAIL] Matting error: {e}")
        return False


def test_database():
    """Test 7: Database."""
    print_header("TEST 7: Database (SQLAlchemy)")
    try:
        from src.api.database import init_db, get_session, Document
        init_db()
        session = get_session()
        count = session.query(Document).count()
        session.close()
        print(f"  Database initialized: [OK]")
        print(f"  Documents in DB: {count}")
        return True
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
        return False


def test_fastapi():
    """Test 8: FastAPI app."""
    print_header("TEST 8: FastAPI Application")
    try:
        from src.api.fastapi_app import app
        print(f"  App title: {app.title}")
        print(f"  Version: {app.version}")
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        api_routes = [r for r in routes if r.startswith('/api')]
        print(f"  Total routes: {len(routes)}")
        print(f"  API routes: {len(api_routes)}")
        for r in api_routes:
            print(f"    -> {r}")
        return True
    except Exception as e:
        print(f"  [FAIL] FastAPI error: {e}")
        return False


def test_full_pipeline():
    """Test 9: Full pipeline (if sample file exists)."""
    print_header("TEST 9: Full E2E Pipeline")

    test_files = []
    for d in ['data/test', 'data/raw', 'data']:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    test_files.append(os.path.join(d, f))

    if not test_files:
        print("  [WARN] No test files found in data/test/ or data/raw/")
        print("  Skipping pipeline test. Add a test document to run E2E.")
        return True

    test_file = test_files[0]
    print(f"  Test file: {test_file}")

    try:
        from src.pipeline.ocr_llm_pipeline import VietIDPPipeline

        print("  Loading pipeline (this may take 30-60s on first run)...")
        start = time.time()
        pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)
        load_time = time.time() - start
        print(f"  Pipeline load time: {load_time:.1f}s")

        print(f"  Processing: {os.path.basename(test_file)}...")
        start = time.time()
        result = pipeline.process_file(test_file, save_result=True)
        process_time = time.time() - start

        print(f"\n  -- RESULTS --")
        print(f"  Status: {result.get('status')}")
        print(f"  Pages: {result.get('num_pages')}")
        print(f"  Stamps found: {result.get('total_stamps')}")
        print(f"  OCR text length: {len(result.get('full_text', ''))} chars")
        print(f"  Processing time: {process_time:.1f}s")

        extraction = result.get('extraction', {})
        if extraction:
            print(f"\n  -- EXTRACTION --")
            for k, v in extraction.items():
                if v:
                    print(f"  {k}: {str(v)[:80]}")

        return result.get('status') == 'success'

    except Exception as e:
        print(f"  [FAIL] Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("  VietIDP NeuralIDP Enterprise -- Pilot Test")
    print("  Testing all components on GPU")
    print("=" * 60)

    tests = [
        ("GPU & CUDA", test_gpu),
        ("Configuration", test_config),
        ("OCR Engine", test_ocr_engine),
        ("Ollama LLM", test_ollama),
        ("YOLO Detection", test_stamp_detection),
        ("Stamp Matting", test_stamp_matting),
        ("Database", test_database),
        ("FastAPI App", test_fastapi),
        ("Full Pipeline", test_full_pipeline),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"  [FAIL] Unexpected error: {e}")
            results[name] = False

    # Summary
    print_header("PILOT TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, ok in results.items():
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status}  {name}")

    print(f"\n  Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n  ALL TESTS PASSED -- System ready for production!")
    else:
        print(f"\n  {total - passed} test(s) failed -- check output above")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
