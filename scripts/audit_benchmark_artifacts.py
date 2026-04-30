# -*- coding: utf-8 -*-
"""Audit benchmark artifacts before running or publishing VietIDP results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.manifest import INPUT_SUFFIXES, DatasetManifest, ManifestError


def list_inputs(input_dir: Path) -> dict[str, Path]:
    if not input_dir.exists():
        return {}
    return {path.stem: path for path in sorted(input_dir.iterdir()) if path.is_file() and path.suffix.lower() in INPUT_SUFFIXES}


def list_labels(labels_dir: Path) -> dict[str, Path]:
    if not labels_dir.exists():
        return {}
    return {path.stem: path for path in sorted(labels_dir.glob("*.json")) if path.is_file()}


def audit_pairing(input_dir: Path, labels_dir: Path) -> list[str]:
    issues: list[str] = []
    inputs = list_inputs(input_dir)
    labels = list_labels(labels_dir)

    for label_id, label_path in labels.items():
        if label_id not in inputs:
            issues.append(f"label without input: {label_path}")

    for input_id, input_path in inputs.items():
        if labels and input_id not in labels:
            issues.append(f"input without label: {input_path}")

    if labels and not inputs:
        issues.append(f"labels exist in {labels_dir} but no benchmark inputs were found in {input_dir}")

    return issues


def audit_results(results_dir: Path | None) -> list[str]:
    if not results_dir or not results_dir.exists():
        return []

    issues: list[str] = []
    for result_path in sorted(results_dir.rglob("*.json")):
        try:
            with result_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:
            continue
        if "benchmark" in result_path.name.lower() and not payload.get("manifest_sha256"):
            issues.append(f"benchmark result without manifest hash: {result_path}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit VietIDP benchmark artifacts")
    parser.add_argument("--input", default="data/test", help="Benchmark input directory")
    parser.add_argument("--labels", default="data/test/labels", help="Benchmark label directory")
    parser.add_argument("--manifest", default=None, help="Manifest JSON to validate")
    parser.add_argument("--results", default=None, help="Optional results directory to audit")
    parser.add_argument("--allow-missing-labels", action="store_true", help="Do not require labels in manifest validation")
    args = parser.parse_args()

    issues = audit_pairing(Path(args.input), Path(args.labels))
    issues.extend(audit_results(Path(args.results) if args.results else None))

    if args.manifest:
        try:
            manifest = DatasetManifest.load(args.manifest)
            manifest.validate(require_labels=not args.allow_missing_labels)
        except ManifestError as exc:
            issues.append(str(exc))

    if issues:
        print("[FAIL] Benchmark artifact audit found issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("[SUCCESS] Benchmark artifact audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
