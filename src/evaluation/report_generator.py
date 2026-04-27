# -*- coding: utf-8 -*-
"""
VietIDP Report Generator
==========================
Sinh báo cáo HTML tự động từ kết quả benchmark.

Sử dụng:
    conda activate vietidp
    cd /d E:\OCR-LLM_Research\OCR-LLM_Research
    python src/evaluation/report_generator.py --input results/benchmark/benchmark_results.json
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def generate_html_report(data: dict, output_path: str):
    """Sinh báo cáo HTML từ benchmark results."""
    summary = data.get('summary', {})
    results = data.get('results', [])
    timestamp = data.get('timestamp', datetime.now().isoformat())

    # Build table rows
    rows_html = ""
    for r in results:
        status_class = 'success' if r.get('status') == 'success' else 'fail'
        cer = f"{r.get('cer', 'N/A'):.4f}" if isinstance(r.get('cer'), (int, float)) else 'N/A'
        wer = f"{r.get('wer', 'N/A'):.4f}" if isinstance(r.get('wer'), (int, float)) else 'N/A'
        f1 = 'N/A'
        if r.get('f1_score'):
            f1 = f"{r['f1_score'].get('f1', 0):.4f}"

        extraction = r.get('extraction', {})
        doc_type = extraction.get('loai_van_ban', '')
        doc_id = extraction.get('so_hieu', '')

        rows_html += f"""
        <tr>
            <td>{r.get('filename', '')}</td>
            <td><span class="badge {status_class}">{r.get('status', 'unknown')}</span></td>
            <td>{r.get('processing_time', 'N/A')}s</td>
            <td>{r.get('num_pages', '')}</td>
            <td>{r.get('total_stamps', '')}</td>
            <td>{r.get('text_length', '')}</td>
            <td>{cer}</td>
            <td>{wer}</td>
            <td>{f1}</td>
            <td>{doc_type}</td>
            <td style="font-family:monospace;font-size:12px">{doc_id}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VietIDP Benchmark Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: #f8fafc; color: #1e293b; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
        h1 {{ font-size: 28px; font-weight: 700; color: #001e40; margin-bottom: 4px; }}
        .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 32px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .card-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 8px; }}
        .card-value {{ font-size: 28px; font-weight: 700; color: #001e40; }}
        .card-sub {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        th {{ text-align: left; padding: 12px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
        td {{ padding: 10px 14px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }}
        tr:hover td {{ background: #f8fafc; }}
        .badge {{ padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
        .badge.success {{ background: #f0fdf4; color: #16a34a; }}
        .badge.fail {{ background: #fef2f2; color: #dc2626; }}
        .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>VietIDP Benchmark Report</h1>
        <p class="subtitle">Generated: {timestamp} | Model: Qwen2.5-7B + VietOCR + YOLOv8x</p>

        <div class="cards">
            <div class="card">
                <div class="card-label">Total Files</div>
                <div class="card-value">{summary.get('total_files', 0)}</div>
                <div class="card-sub">{summary.get('success_rate', 0)*100:.1f}% success rate</div>
            </div>
            <div class="card">
                <div class="card-label">Avg Processing</div>
                <div class="card-value">{summary.get('avg_time', 0)}s</div>
                <div class="card-sub">Median: {summary.get('median_time', 0)}s</div>
            </div>
            <div class="card">
                <div class="card-label">Peak VRAM</div>
                <div class="card-value">{summary.get('vram_peak_gb', 0)} GB</div>
                <div class="card-sub">RTX 5070 (8GB)</div>
            </div>
            <div class="card">
                <div class="card-label">Avg CER</div>
                <div class="card-value">{summary.get('avg_cer', 'N/A') if summary.get('avg_cer') is None else f"{summary['avg_cer']:.4f}"}</div>
                <div class="card-sub">Character Error Rate</div>
            </div>
            <div class="card">
                <div class="card-label">Avg WER</div>
                <div class="card-value">{summary.get('avg_wer', 'N/A') if summary.get('avg_wer') is None else f"{summary['avg_wer']:.4f}"}</div>
                <div class="card-sub">Word Error Rate</div>
            </div>
            <div class="card">
                <div class="card-label">Avg F1</div>
                <div class="card-value">{summary.get('avg_f1', 'N/A') if summary.get('avg_f1') is None else f"{summary['avg_f1']:.4f}"}</div>
                <div class="card-sub">Extraction Accuracy</div>
            </div>
        </div>

        <h2 style="font-size:18px;font-weight:600;color:#001e40;margin-bottom:16px">Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Status</th>
                    <th>Time</th>
                    <th>Pages</th>
                    <th>Stamps</th>
                    <th>Chars</th>
                    <th>CER</th>
                    <th>WER</th>
                    <th>F1</th>
                    <th>Doc Type</th>
                    <th>Doc ID</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            VietIDP NeuralIDP Enterprise v3.0 — Benchmark Report
        </div>
    </div>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Report saved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VietIDP Report Generator")
    parser.add_argument("--input", default="results/benchmark/benchmark_results.json")
    parser.add_argument("--output", default="results/benchmark/report.html")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input not found: {args.input}")
        print("   Run benchmark first: python src/evaluation/benchmark.py")
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    generate_html_report(data, args.output)
