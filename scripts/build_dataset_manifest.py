# -*- coding: utf-8 -*-
"""Build a SHA256-linked dataset manifest for VietIDP benchmarks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation.manifest import build_manifest_payload, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build VietIDP dataset manifest")
    parser.add_argument("--input", required=True, help="Directory containing benchmark inputs")
    parser.add_argument("--labels", default=None, help="Directory containing label JSON files")
    parser.add_argument("--output", required=True, help="Manifest output JSON path")
    parser.add_argument("--dataset-name", default="vietidp_dataset", help="Dataset name for manifest metadata")
    parser.add_argument("--split", default="unknown", help="Split name: train, validation, blind, etc.")
    parser.add_argument("--source-type", default="unknown", help="Source type: synthetic, real_scan, born_digital, etc.")
    args = parser.parse_args()

    payload = build_manifest_payload(
        args.input,
        args.labels,
        output_path=args.output,
        dataset_name=args.dataset_name,
        split=args.split,
        source_type=args.source_type,
    )
    path = write_manifest(payload, args.output)
    print(f"[SUCCESS] Manifest written: {path}")
    print(f"[INFO] Entries: {len(payload['entries'])}")
    print(f"[INFO] Manifest SHA256: {payload['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
