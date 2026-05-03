from __future__ import annotations

import statistics
import sys
import tempfile
import types
import unittest
from pathlib import Path

if "numpy" not in sys.modules:
    numpy_stub = types.ModuleType("numpy")
    numpy_stub.mean = lambda values: sum(values) / len(values)
    numpy_stub.median = lambda values: statistics.median(values)
    numpy_stub.zeros = lambda shape, dtype=int: [[dtype() for _ in range(shape[1])] for _ in range(shape[0])]
    numpy_stub.ndarray = list
    sys.modules["numpy"] = numpy_stub

from src.evaluation.benchmark import BenchmarkRunner
from src.evaluation.report_generator import generate_html_report


class BootstrapEvaluationTests(unittest.TestCase):
    def test_bootstrap_metric_path_ci_is_deterministic_and_handles_edge_cases(self):
        from src.evaluation.bootstrap import bootstrap_ci_from_metric_path, bootstrap_percentile_ci

        self.assertEqual(
            bootstrap_percentile_ci([], seed=7),
            {"lower": None, "upper": None, "confidence": 0.95, "iterations": 1000, "seed": 7, "sample_size": 0},
        )
        self.assertEqual(
            bootstrap_percentile_ci([0.42], seed=7),
            {"lower": 0.42, "upper": 0.42, "confidence": 0.95, "iterations": 1000, "seed": 7, "sample_size": 1},
        )
        with self.assertRaises(ValueError):
            bootstrap_percentile_ci([], iterations=0)
        with self.assertRaises(ValueError):
            bootstrap_percentile_ci([0.42], confidence=1.5)

        results = [
            {"strict_extraction_metrics": {"macro": {"normalized_exact_match": 0.1}}},
            {"strict_extraction_metrics": {"macro": {"normalized_exact_match": 0.5}}},
            {"strict_extraction_metrics": {"macro": {"normalized_exact_match": 0.9}}},
        ]

        ci = bootstrap_ci_from_metric_path(
            results,
            "strict_extraction_metrics.macro.normalized_exact_match",
            seed=123,
            iterations=200,
        )
        self.assertEqual(
            ci,
            bootstrap_ci_from_metric_path(
                results,
                "strict_extraction_metrics.macro.normalized_exact_match",
                seed=123,
                iterations=200,
            ),
        )
        self.assertLessEqual(ci["lower"], ci["upper"])
        self.assertEqual(ci["sample_size"], 3)
        from src.evaluation.bootstrap import metric_values_from_results

        mixed_results = [
            {"a": {"b": 1}},
            {"a": {"b": "not numeric"}},
            {"a": 3},
            {"x": {"b": 4}},
            {"a": {"b": 2.5}},
        ]
        self.assertEqual(metric_values_from_results(mixed_results, "a.b"), [1.0, 2.5])

    def test_benchmark_summary_includes_bootstrap_confidence_intervals(self):
        runner = BenchmarkRunner(output_dir=".")
        results = [
            {
                "status": "success",
                "processing_time": 1.0,
                "cer": 0.10,
                "wer": 0.20,
                "legacy_debug_extraction_f1": {"f1": 0.30},
                "strict_extraction_metrics": {
                    "macro": {
                        "strict_exact_match": 0.40,
                        "normalized_exact_match": 0.50,
                        "token_f1": 0.60,
                        "character_similarity": 0.70,
                    }
                },
            },
            {
                "status": "success",
                "processing_time": 2.0,
                "cer": 0.20,
                "wer": 0.30,
                "legacy_debug_extraction_f1": {"f1": 0.50},
                "strict_extraction_metrics": {
                    "macro": {
                        "strict_exact_match": 0.60,
                        "normalized_exact_match": 0.70,
                        "token_f1": 0.80,
                        "character_similarity": 0.90,
                    }
                },
            },
        ]

        summary = runner._compute_summary(results, total_time=3.0, vram_peak=1.25)

        self.assertEqual(summary["avg_cer"], 0.15)
        self.assertEqual(summary["legacy_debug_avg_f1"], 0.4)
        self.assertEqual(summary["strict_macro_normalized_exact_match"], 0.6)
        self.assertEqual(summary["confidence_intervals"]["avg_cer"]["sample_size"], 2)
        self.assertEqual(summary["confidence_intervals"]["strict_macro_token_f1"]["seed"], 42)
        self.assertLessEqual(
            summary["confidence_intervals"]["strict_macro_character_similarity"]["lower"],
            summary["confidence_intervals"]["strict_macro_character_similarity"]["upper"],
        )

    def test_report_generator_renders_manifest_and_confidence_interval_provenance(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "report.html"
            data = {
                "timestamp": "2026-05-01T12:00:00<script>alert(1)</script>",
                "official": True,
                "manifest_path": "/tmp/<script>manifest</script>.json",
                "manifest_sha256": "abc123<img src=x onerror=alert(1)>",
                "summary": {
                    "total_files": "2<script>",
                    "success_rate": "100<script>%",
                    "avg_time": "1.5<script>",
                    "median_time": "1.5<script>",
                    "vram_peak_gb": "1.25<script>",
                    "avg_cer": 0.15,
                    "avg_wer": 0.25,
                    "legacy_debug_avg_f1": 0.4,
                    "strict_macro_exact_match": 0.5,
                    "strict_macro_normalized_exact_match": 0.6,
                    "strict_macro_token_f1": 0.7,
                    "strict_macro_character_similarity": 0.8,
                    "confidence_intervals": {
                        "avg_cer": {"lower": 0.11, "upper": 0.19, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                        "legacy_debug_avg_f1": {"lower": 0.31, "upper": 0.49, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                        "strict_macro_exact_match": {"lower": 0.42, "upper": 0.58, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                        "strict_macro_normalized_exact_match": {"lower": 0.52, "upper": 0.68, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                        "strict_macro_token_f1": {"lower": 0.61, "upper": 0.79, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                        "strict_macro_character_similarity": {"lower": 0.72, "upper": 0.88, "confidence": 0.95, "iterations": 1000, "seed": 42, "sample_size": 2},
                    },
                },
                "results": [
                    {
                        "filename": "doc-1<script>.pdf",
                        "status": "success<script>",
                        "processing_time": 1.5,
                        "num_pages": 1,
                        "total_stamps": 0,
                        "text_length": 100,
                        "cer": 0.15,
                        "wer": 0.25,
                        "legacy_debug_extraction_f1": {"f1": 0.4},
                        "strict_extraction_metrics": {"macro": {"normalized_exact_match": 0.6, "token_f1": 0.7}},
                        "extraction": {"loai_van_ban": "Quyết <b>định</b>", "so_hieu": "123<QĐ>"},
                    }
                ],
            }

            generate_html_report(data, str(output_path))

            html = output_path.read_text(encoding="utf-8")
            self.assertIn("Official benchmark", html)
            self.assertIn("/tmp/&lt;script&gt;manifest&lt;/script&gt;.json", html)
            self.assertIn("abc123&lt;img src=x onerror=alert(1)&gt;", html)
            self.assertNotIn("<script>", html)
            self.assertNotIn("<img src=x", html)
            self.assertIn("2&lt;script&gt;", html)
            self.assertIn("100&lt;script&gt;%", html)
            self.assertIn("1.5&lt;script&gt;s", html)
            self.assertIn("1.25&lt;script&gt; GB", html)
            self.assertIn("doc-1&lt;script&gt;.pdf", html)
            self.assertIn("Quyết &lt;b&gt;định&lt;/b&gt;", html)
            self.assertIn("123&lt;QĐ&gt;", html)
            self.assertIn("95% CI", html)
            self.assertIn("0.1100–0.1900", html)
            self.assertIn("Strict Exact", html)
            self.assertIn("0.4200–0.5800", html)
            self.assertIn("Strict Char Sim", html)
            self.assertIn("0.7200–0.8800", html)


if __name__ == "__main__":
    unittest.main()
