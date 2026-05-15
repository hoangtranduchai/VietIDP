# -*- coding: utf-8 -*-
from __future__ import annotations

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
from html import escape
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _format_metric(value):
    return f"{value:.4f}" if isinstance(value, (int, float)) else 'N/A'


def _html(value) -> str:
    return escape(str(value), quote=True)


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _legacy_debug_f1(result: dict):
    legacy = result.get('legacy_debug_extraction_f1') or result.get('f1_score')
    if isinstance(legacy, dict):
        return legacy.get('f1')
    return None


def _summary_metric(summary: dict, preferred_key: str, fallback_key: str | None = None):
    value = summary.get(preferred_key)
    if value is None and fallback_key:
        value = summary.get(fallback_key)
    return _format_metric(value)


def _summary_value(summary: dict, key: str, default='N/A', suffix: str = '') -> str:
    value = summary.get(key, default)
    return f"{_html(value)}{suffix}"


def _summary_percent(summary: dict, key: str) -> str:
    value = summary.get(key, 0)
    if isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    return _html(value)


def _metric_ci(summary: dict, metric_key: str) -> str:
    ci = (summary.get('confidence_intervals') or {}).get(metric_key) or {}
    lower = ci.get('lower')
    upper = ci.get('upper')
    if not isinstance(lower, (int, float)) or not isinstance(upper, (int, float)):
        return ''
    confidence = ci.get('confidence') if isinstance(ci.get('confidence'), (int, float)) else 0.95
    confidence_pct = int(round(confidence * 100))
    return f"{confidence_pct}% CI: {lower:.4f}–{upper:.4f}"


def _card_subtitle(base_text: str, ci_text: str) -> str:
    if not ci_text:
        return base_text
    return f"{base_text}<br>{ci_text}"


def generate_html_report(data: dict, output_path: str):
    """Sinh báo cáo HTML từ benchmark results."""
    summary = data.get('summary', {})
    results = data.get('results', [])
    timestamp = _html(data.get('timestamp', datetime.now().isoformat()))
    manifest_path = _html(data.get('manifest_path') or 'N/A')
    manifest_sha256 = _html(data.get('manifest_sha256') or 'N/A')
    official_flag = 'Yes' if data.get('official') else 'No'
    provenance = _safe_dict(data.get('provenance'))
    model = _safe_dict(provenance.get('model'))
    runtime = _safe_dict(provenance.get('runtime'))
    hardware = _safe_dict(provenance.get('hardware'))
    model_name = _html(model.get('ollama_model') or 'N/A')
    ocr_model = _html(model.get('vietocr_model') or 'N/A')
    model_checksum = _html(model.get('checksum') or 'N/A')
    command = _html(provenance.get('command') or 'N/A')
    code_commit = _html(provenance.get('code_commit') or 'N/A')
    split = _html(provenance.get('split') or 'N/A')
    source_type = _html(provenance.get('source_type') or 'N/A')
    runtime_summary = _html(
        f"Python {runtime.get('python_version', 'N/A')} | OCR DPI {runtime.get('ocr_dpi', 'N/A')} | "
        f"LLM temp {runtime.get('ollama_temperature', 'N/A')}"
    )
    if hardware.get('gpu_name'):
        hardware_summary = _html(hardware.get('gpu_name'))
    elif hardware.get('cuda_available') is False:
        hardware_summary = 'CUDA unavailable'
    else:
        hardware_summary = 'N/A'

    # Build table rows
    rows_html = ""
    for r in results:
        status_class = 'success' if r.get('status') == 'success' else 'fail'
        cer = _format_metric(r.get('cer'))
        wer = _format_metric(r.get('wer'))
        legacy_f1 = _format_metric(_legacy_debug_f1(r))
        strict_macro = r.get('strict_extraction_metrics', {}).get('macro', {})
        strict_normalized = _format_metric(strict_macro.get('normalized_exact_match'))
        strict_token_f1 = _format_metric(strict_macro.get('token_f1'))

        extraction = r.get('extraction', {})
        doc_type = _html(extraction.get('loai_van_ban', ''))
        doc_id = _html(extraction.get('so_hieu', ''))
        filename = _html(r.get('filename', ''))
        status_text = _html(r.get('status', 'unknown'))
        processing_time = _html(r.get('processing_time', 'N/A'))
        num_pages = _html(r.get('num_pages', ''))
        total_stamps = _html(r.get('total_stamps', ''))
        text_length = _html(r.get('text_length', ''))

        rows_html += f"""
        <tr>
            <td>{filename}</td>
            <td><span class="badge {status_class}">{status_text}</span></td>
            <td>{processing_time}s</td>
            <td>{num_pages}</td>
            <td>{total_stamps}</td>
            <td>{text_length}</td>
            <td>{cer}</td>
            <td>{wer}</td>
            <td>{legacy_f1}</td>
            <td>{strict_normalized}</td>
            <td>{strict_token_f1}</td>
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
        <p class="subtitle">Generated: {timestamp} | Model: {model_name} | OCR: {ocr_model}</p>
        <div style="background:white;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:#94a3b8;margin-bottom:8px">Benchmark Provenance</div>
            <div style="font-size:13px;color:#334155;line-height:1.7">
                <div><strong>Official benchmark:</strong> {official_flag}</div>
                <div><strong>Manifest path:</strong> <span style="font-family:monospace">{manifest_path}</span></div>
                <div><strong>Manifest SHA256:</strong> <span style="font-family:monospace">{manifest_sha256}</span></div>
                <div><strong>Split/source:</strong> {split} / {source_type}</div>
                <div><strong>Command:</strong> <span style="font-family:monospace">{command}</span></div>
                <div><strong>Code commit:</strong> <span style="font-family:monospace">{code_commit}</span></div>
                <div><strong>Model checksum:</strong> <span style="font-family:monospace">{model_checksum}</span></div>
                <div><strong>Runtime:</strong> {runtime_summary}</div>
                <div><strong>Hardware:</strong> {hardware_summary}</div>
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-label">Total Files</div>
                <div class="card-value">{_summary_value(summary, 'total_files', 0)}</div>
                <div class="card-sub">{_summary_percent(summary, 'success_rate')} success rate</div>
            </div>
            <div class="card">
                <div class="card-label">Avg Processing</div>
                <div class="card-value">{_summary_value(summary, 'avg_time', 0, 's')}</div>
                <div class="card-sub">Median: {_summary_value(summary, 'median_time', 0, 's')}</div>
            </div>
            <div class="card">
                <div class="card-label">Peak VRAM</div>
                <div class="card-value">{_summary_value(summary, 'vram_peak_gb', 0, ' GB')}</div>
                <div class="card-sub">RTX 5070 (8GB)</div>
            </div>
            <div class="card">
                <div class="card-label">Avg CER</div>
                <div class="card-value">{_format_metric(summary.get('avg_cer'))}</div>
                <div class="card-sub">{_card_subtitle('Character Error Rate', _metric_ci(summary, 'avg_cer'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Avg WER</div>
                <div class="card-value">{_format_metric(summary.get('avg_wer'))}</div>
                <div class="card-sub">{_card_subtitle('Word Error Rate', _metric_ci(summary, 'avg_wer'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Legacy Debug F1</div>
                <div class="card-value">{_summary_metric(summary, 'legacy_debug_avg_f1', 'avg_f1')}</div>
                <div class="card-sub">{_card_subtitle('Substring legacy metric', _metric_ci(summary, 'legacy_debug_avg_f1'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Strict Exact</div>
                <div class="card-value">{_format_metric(summary.get('strict_macro_exact_match'))}</div>
                <div class="card-sub">{_card_subtitle('Macro exact match', _metric_ci(summary, 'strict_macro_exact_match'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Strict Normalized</div>
                <div class="card-value">{_format_metric(summary.get('strict_macro_normalized_exact_match'))}</div>
                <div class="card-sub">{_card_subtitle('Macro normalized exact', _metric_ci(summary, 'strict_macro_normalized_exact_match'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Strict Token F1</div>
                <div class="card-value">{_format_metric(summary.get('strict_macro_token_f1'))}</div>
                <div class="card-sub">{_card_subtitle('Macro token overlap', _metric_ci(summary, 'strict_macro_token_f1'))}</div>
            </div>
            <div class="card">
                <div class="card-label">Strict Char Sim</div>
                <div class="card-value">{_format_metric(summary.get('strict_macro_character_similarity'))}</div>
                <div class="card-sub">{_card_subtitle('Macro character similarity', _metric_ci(summary, 'strict_macro_character_similarity'))}</div>
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
                    <th>Legacy Debug F1</th>
                    <th>Strict Norm</th>
                    <th>Token F1</th>
                    <th>Doc Type</th>
                    <th>Doc ID</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            VietIDP v3.0 — Benchmark Report | Khoa CNTT, ĐH Bách khoa, ĐHĐN
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
