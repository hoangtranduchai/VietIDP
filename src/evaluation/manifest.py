# -*- coding: utf-8 -*-
"""Dataset manifest utilities for reproducible VietIDP evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

INPUT_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


class ManifestError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def manifest_content_hash(payload: dict) -> str:
    return canonical_json_hash({key: value for key, value in payload.items() if key != "manifest_sha256"})


@dataclass(frozen=True)
class ManifestEntry:
    id: str
    input_path: Path
    input_sha256: str
    label_path: Path | None = None
    label_sha256: str | None = None
    split: str | None = None
    source_type: str | None = None

    @classmethod
    def from_dict(cls, entry: dict, root: Path) -> "ManifestEntry":
        if not entry.get("id"):
            raise ManifestError("Manifest entry missing id")
        if not entry.get("input_path"):
            raise ManifestError(f"Manifest entry {entry.get('id')} missing input_path")
        if not entry.get("input_sha256"):
            raise ManifestError(f"Manifest entry {entry.get('id')} missing input_sha256")

        label_path = entry.get("label_path")
        return cls(
            id=str(entry["id"]),
            input_path=(root / entry["input_path"]).resolve(),
            input_sha256=str(entry["input_sha256"]),
            label_path=(root / label_path).resolve() if label_path else None,
            label_sha256=str(entry["label_sha256"]) if entry.get("label_sha256") else None,
            split=str(entry["split"]) if entry.get("split") else None,
            source_type=str(entry["source_type"]) if entry.get("source_type") else None,
        )

    def validate_files(self, require_label: bool = False, verify_hashes: bool = True) -> list[str]:
        errors: list[str] = []
        if not self.input_path.exists():
            errors.append(f"{self.id}: missing input {self.input_path}")
        elif verify_hashes and sha256_file(self.input_path) != self.input_sha256:
            errors.append(f"{self.id}: input hash mismatch {self.input_path}")

        if require_label and not self.label_path:
            errors.append(f"{self.id}: missing label_path")
        if self.label_path:
            if not self.label_path.exists():
                errors.append(f"{self.id}: missing label {self.label_path}")
            elif verify_hashes and self.label_sha256 and sha256_file(self.label_path) != self.label_sha256:
                errors.append(f"{self.id}: label hash mismatch {self.label_path}")
        return errors


@dataclass(frozen=True)
class DatasetManifest:
    path: Path
    root: Path
    metadata: dict
    entries: list[ManifestEntry]
    manifest_sha256: str
    computed_sha256: str
    schema_version: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> "DatasetManifest":
        manifest_path = Path(path).resolve()
        with manifest_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        root_value = payload.get("root") or "."
        root = (manifest_path.parent / root_value).resolve()
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ManifestError("Manifest must contain an entries list")

        entries = [ManifestEntry.from_dict(entry, root) for entry in raw_entries]
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        manifest_sha256 = str(payload.get("manifest_sha256") or "")
        computed_sha256 = manifest_content_hash(payload)
        schema_version = str(payload["schema_version"]) if payload.get("schema_version") else None
        return cls(manifest_path, root, metadata, entries, manifest_sha256, computed_sha256, schema_version)

    def validate(self, require_labels: bool = True, verify_hashes: bool = True, check_split_leakage: bool = True) -> None:
        errors: list[str] = []
        seen_ids: set[str] = set()
        seen_by_split: dict[str, set[str]] = {}

        if self.schema_version != "vietidp-manifest-v1":
            errors.append("manifest missing or unsupported schema_version")
        if not self.manifest_sha256:
            errors.append("manifest missing manifest_sha256")
        elif self.manifest_sha256 != self.computed_sha256:
            errors.append("manifest_sha256 does not match manifest contents")
        if not self.metadata:
            errors.append("manifest missing metadata")
        elif require_labels:
            if not self.metadata.get("split"):
                errors.append("manifest metadata missing split")
            if not self.metadata.get("source_type"):
                errors.append("manifest metadata missing source_type")

        for entry in self.entries:
            if entry.id in seen_ids:
                errors.append(f"duplicate entry id {entry.id}")
            seen_ids.add(entry.id)
            if require_labels and not entry.label_sha256:
                errors.append(f"{entry.id}: missing label_sha256")
            if require_labels and not entry.split:
                errors.append(f"{entry.id}: missing split")
            if require_labels and not entry.source_type:
                errors.append(f"{entry.id}: missing source_type")
            errors.extend(entry.validate_files(require_label=require_labels, verify_hashes=verify_hashes))
            if entry.split and entry.input_sha256:
                seen_by_split.setdefault(entry.input_sha256, set()).add(entry.split)

        if check_split_leakage:
            for input_hash, splits in seen_by_split.items():
                if len(splits) > 1:
                    errors.append(f"input hash {input_hash} appears in multiple splits: {sorted(splits)}")

        if errors:
            raise ManifestError("Manifest validation failed:\n" + "\n".join(f"- {error}" for error in errors))

    def iter_files(self, limit: int | None = None) -> Iterable[ManifestEntry]:
        yield from self.entries[:limit]


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_manifest_payload(
    input_dir: str | Path,
    labels_dir: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
    dataset_name: str = "vietidp_dataset",
    split: str = "unknown",
    source_type: str = "unknown",
) -> dict:
    input_root = Path(input_dir).resolve()
    label_root = Path(labels_dir).resolve() if labels_dir else None
    manifest_path = Path(output_path).resolve() if output_path else input_root / "manifest.json"
    root = manifest_path.parent.resolve()

    input_files = sorted(path for path in input_root.iterdir() if path.is_file() and path.suffix.lower() in INPUT_SUFFIXES)
    entries = []
    for input_path in input_files:
        label_path = label_root / f"{input_path.stem}.json" if label_root else None
        entry = {
            "id": input_path.stem,
            "input_path": _relative(input_path, root),
            "input_sha256": sha256_file(input_path),
            "split": split,
            "source_type": source_type,
        }
        if label_path and label_path.exists():
            entry["label_path"] = _relative(label_path, root)
            entry["label_sha256"] = sha256_file(label_path)
        entries.append(entry)

    payload = {
        "schema_version": "vietidp-manifest-v1",
        "root": ".",
        "metadata": {
            "dataset_name": dataset_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input_dir": _relative(input_root, root),
            "labels_dir": _relative(label_root, root) if label_root else None,
            "split": split,
            "source_type": source_type,
        },
        "entries": entries,
    }
    payload["manifest_sha256"] = manifest_content_hash(payload)
    return payload


def write_manifest(payload: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["manifest_sha256"] = manifest_content_hash(payload)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return path
