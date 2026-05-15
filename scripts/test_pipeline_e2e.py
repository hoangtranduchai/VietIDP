# -*- coding: utf-8 -*-
"""
Test Pipeline End-to-End (QLoRA Backend)
=========================================
Chạy toàn bộ pipeline VietIDP trên 1 file PDF:
  YOLO → Stamp Removal → OCR → Layout → QLoRA → Validation

Sử dụng:
  python scripts/test_pipeline_e2e.py                         # Test 1 PDF đầu tiên
  python scripts/test_pipeline_e2e.py --pdf data/raw/pdf_test/pdf_test_0001.pdf
  python scripts/test_pipeline_e2e.py --num 3                 # Test 3 PDF
"""

import os
import sys
import json
import time
import argparse
import pathlib

# [HOTFIX] Windows UTF-8
_original_read_text = pathlib.Path.read_text
def _utf8_read_text(self, encoding=None, errors=None):
    return _original_read_text(self, encoding=encoding or "utf-8", errors=errors)
pathlib.Path.read_text = _utf8_read_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(args):
    from src.pipeline.ocr_llm_pipeline import VietIDPPipeline

    # 1. Khởi tạo pipeline (load tất cả models 1 lần)
    print("\n🚀 Khởi tạo VietIDP Pipeline (QLoRA backend)...\n")
    pipeline = VietIDPPipeline(load_yolo=True, load_ocr=True, load_llm=True)

    # 2. Xác định file PDF cần test
    if args.pdf:
        pdf_files = [args.pdf]
    else:
        pdf_dir = os.path.join("data", "raw", "pdf_test")
        all_pdfs = sorted([
            os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.pdf')
        ])
        pdf_files = all_pdfs[:args.num]

    print(f"\n📂 Test {len(pdf_files)} file PDF\n")

    # 3. Chạy pipeline
    results = []
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n{'='*60}")
        print(f"📄 [{i+1}/{len(pdf_files)}] {os.path.basename(pdf_path)}")
        print(f"{'='*60}")

        try:
            result = pipeline.process_file(pdf_path, save_result=True)

            extraction = result.get('extraction', {})
            print(f"\n  📊 KẾT QUẢ TRÍCH XUẤT:")
            print(f"     Loại VB:      {extraction.get('loai_van_ban', '—')}")
            print(f"     Số hiệu:     {extraction.get('so_hieu', '—')}")
            print(f"     Ngày BH:     {extraction.get('ngay_ban_hanh', '—')}")
            print(f"     Cơ quan:     {extraction.get('co_quan_ban_hanh', '—')}")
            print(f"     Trích yếu:   {extraction.get('trich_yeu', '—')[:80]}")
            print(f"     Người ký:    {extraction.get('nguoi_ky', '—')}")
            print(f"     Trang:       {result.get('num_pages', 0)}")
            print(f"     Stamps:      {result.get('total_stamps', 0)}")
            print(f"     Thời gian:   {result.get('processing_time_seconds', 0):.1f}s")

            results.append({
                'file': os.path.basename(pdf_path),
                'status': 'success',
                'extraction': extraction,
                'pages': result.get('num_pages', 0),
                'stamps': result.get('total_stamps', 0),
                'time': result.get('processing_time_seconds', 0),
            })
        except Exception as e:
            print(f"  ❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'file': os.path.basename(pdf_path),
                'status': 'error',
                'error': str(e),
            })

    # 4. Tổng kết
    print(f"\n\n{'='*60}")
    print(f"📊 TỔNG KẾT ({len(results)} files)")
    print(f"{'='*60}")

    success = sum(1 for r in results if r['status'] == 'success')
    errors = sum(1 for r in results if r['status'] == 'error')
    total_time = sum(r.get('time', 0) for r in results)

    print(f"  ✅ Thành công:  {success}/{len(results)}")
    print(f"  ❌ Lỗi:        {errors}/{len(results)}")
    print(f"  ⏱️ Tổng thời gian: {total_time:.1f}s")
    if success > 0:
        print(f"  📈 TB/file:     {total_time/success:.1f}s")

    # Hiển thị bảng kết quả
    if success > 0:
        print(f"\n  {'File':<20} {'Loại VB':<12} {'Số hiệu':<20} {'Stamps':<7} {'Time':<8}")
        print(f"  {'-'*20} {'-'*12} {'-'*20} {'-'*7} {'-'*8}")
        for r in results:
            if r['status'] == 'success':
                ext = r['extraction']
                print(f"  {r['file']:<20} {ext.get('loai_van_ban',''):<12} "
                      f"{ext.get('so_hieu',''):<20} {r['stamps']:<7} {r['time']:<8.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test VietIDP Pipeline end-to-end")
    parser.add_argument("--pdf", type=str, help="Đường dẫn PDF cụ thể")
    parser.add_argument("--num", type=int, default=1, help="Số file PDF test (mặc định: 1)")
    args = parser.parse_args()
    main(args)
