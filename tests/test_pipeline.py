# -*- coding: utf-8 -*-
"""
Unit Tests — VietIDP Pipeline
===============================
Chạy: pytest tests/ -v --tb=short
"""

import os
import sys
import json
import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════
# Test Config
# ═══════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_config_import(self):
        from src.config import Config
        assert Config.OLLAMA_MODEL == "qwen2.5:7b"

    def test_config_paths(self):
        from src.config import Config
        assert Config.BASE_DIR.exists()
        assert Config.DATA_DIR.exists()

    def test_vietocr_model(self):
        from src.config import Config
        assert Config.VIETOCR_MODEL == "vgg_transformer"


# ═══════════════════════════════════════════════════════════════════════
# Test Metrics
# ═══════════════════════════════════════════════════════════════════════

class TestMetrics:
    def test_cer_identical(self):
        from src.evaluation.benchmark import character_error_rate
        assert character_error_rate("hello", "hello") == 0.0

    def test_cer_different(self):
        from src.evaluation.benchmark import character_error_rate
        cer = character_error_rate("helo", "hello")
        assert 0.0 < cer < 1.0

    def test_cer_empty(self):
        from src.evaluation.benchmark import character_error_rate
        assert character_error_rate("", "") == 0.0
        assert character_error_rate("abc", "") == 1.0

    def test_wer_identical(self):
        from src.evaluation.benchmark import word_error_rate
        assert word_error_rate("xin chào", "xin chào") == 0.0

    def test_wer_different(self):
        from src.evaluation.benchmark import word_error_rate
        wer = word_error_rate("xin chao", "xin chào thế giới")
        assert wer > 0.0

    def test_f1_perfect(self):
        from src.evaluation.benchmark import extraction_f1
        pred = {'loai_van_ban': 'Quyết định', 'so_hieu': '123/QĐ'}
        gt = {'loai_van_ban': 'Quyết định', 'so_hieu': '123/QĐ'}
        result = extraction_f1(pred, gt)
        assert result['f1'] == 1.0

    def test_f1_zero(self):
        from src.evaluation.benchmark import extraction_f1
        pred = {'loai_van_ban': 'Công văn', 'so_hieu': '999'}
        gt = {'loai_van_ban': 'Quyết định', 'so_hieu': '123/QĐ'}
        result = extraction_f1(pred, gt)
        assert result['f1'] == 0.0

    def test_f1_partial(self):
        from src.evaluation.benchmark import extraction_f1
        pred = {'loai_van_ban': 'Quyết định', 'so_hieu': 'wrong'}
        gt = {'loai_van_ban': 'Quyết định', 'so_hieu': '123/QĐ'}
        result = extraction_f1(pred, gt)
        assert 0.0 < result['f1'] < 1.0


# ═══════════════════════════════════════════════════════════════════════
# Test Database
# ═══════════════════════════════════════════════════════════════════════

class TestDatabase:
    def test_init_db(self):
        from src.api.database import init_db
        init_db()  # Should not raise

    def test_create_document(self):
        from src.api.database import init_db, get_session, Document
        init_db()
        session = get_session()
        doc = Document(
            filename="test_doc.pdf",
            file_path="/tmp/test_doc.pdf",
            file_type="pdf",
            file_size=1024,
            status="pending"
        )
        session.add(doc)
        session.commit()
        assert doc.id is not None
        # Cleanup
        session.delete(doc)
        session.commit()
        session.close()

    def test_to_dict(self):
        from src.api.database import init_db, get_session, Document
        init_db()
        session = get_session()
        doc = Document(
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=512,
            status="completed"
        )
        session.add(doc)
        session.commit()
        d = doc.to_dict()
        assert d['filename'] == 'test.pdf'
        assert d['status'] == 'completed'
        # Cleanup
        session.delete(doc)
        session.commit()
        session.close()


# ═══════════════════════════════════════════════════════════════════════
# Test FastAPI
# ═══════════════════════════════════════════════════════════════════════

class TestFastAPI:
    def test_app_creation(self):
        from src.api.fastapi_app import app
        assert app.title == "VietIDP — Vietnamese Intelligent Document Processing"

    def test_routes_exist(self):
        from src.api.fastapi_app import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        assert '/api/health' in routes
        assert '/api/process_document' in routes
        assert '/api/documents' in routes

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api.fastapi_app import app
        client = TestClient(app)
        res = client.get('/api/health')
        assert res.status_code == 200
        data = res.json()
        assert data['status'] == 'healthy'
        assert 'services' in data


# ═══════════════════════════════════════════════════════════════════════
# Test Prompts
# ═══════════════════════════════════════════════════════════════════════

class TestPrompts:
    def test_prompts_exist(self):
        from src.llm.prompts import PROMPTS
        assert 'extraction' in PROMPTS
        assert 'summarize' in PROMPTS
        assert 'classify' in PROMPTS

    def test_prompt_format(self):
        from src.llm.prompts import PROMPTS
        prompt = PROMPTS['extraction']
        assert '{text}' in prompt


# ═══════════════════════════════════════════════════════════════════════
# Test Stamp Matting (Unit - no GPU needed)
# ═══════════════════════════════════════════════════════════════════════

class TestStampMatting:
    def test_color_mask(self):
        """Test red color detection in HSV."""
        import cv2
        # Create a red image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = (0, 0, 255)  # BGR red
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Red hue ranges
        lower1 = np.array([0, 50, 50])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, 50, 50])
        upper2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        assert mask.sum() > 0  # Should detect red


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
