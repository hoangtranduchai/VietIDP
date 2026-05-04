# VietIDP Dataset Protocol

This protocol defines how VietIDP datasets are built, split, audited, and reported so benchmark claims remain traceable and reproducible.

## Dataset tiers

### 1. Optimization and synthetic development set

Purpose:
- Tune prompts, preprocessing, OCR settings, layout candidates, and model choices.
- Run frequent engineering regressions.
- Generate deterministic synthetic fixtures for pipeline and metric development.

Allowed:
- Repeated evaluation during development.
- Prompt and rule tuning.
- Synthetic data regeneration with fixed seed and manifest.
- Error analysis and targeted hard-negative creation.

Prohibited:
- Reporting as blind real-world performance.
- Mixing with validation or blind test examples.
- Using validation/blind samples as prompt examples, synthetic templates, training data, or pseudo-label seeds.

Required metadata:
- Manifest JSON with `manifest_sha256`.
- Generator seed for synthetic data.
- Source type such as `synthetic`, `legacy`, or `development`.
- Split value such as `optimization` or `train`.

Example:

```bash
python scripts/generate_benchmark_data.py --seed 20260429 --count 100 --output-dir data/benchmarks/synthetic_regenerated --split optimization --noise-profile mixed
python scripts/audit_benchmark_artifacts.py --input data/benchmarks/synthetic_regenerated --labels data/benchmarks/synthetic_regenerated/labels --manifest data/benchmarks/synthetic_regenerated/manifest.json
python src/evaluation/benchmark.py --manifest data/benchmarks/synthetic_regenerated/manifest.json --output results/benchmark/synthetic_regenerated
```

Acceptable claim wording:
- "On the deterministic synthetic optimization set generated with seed 20260429, the system achieved ..."
- "This result is an engineering milestone, not blind real-world performance."

### 2. Held-out validation set

Purpose:
- Select model variants and ablations after development decisions.
- Estimate expected performance before blind testing.
- Compare OCR/layout/LLM variants under strict metrics.

Allowed:
- Repeated evaluation with decision logs.
- Model selection and ablation comparison.
- Failure analysis after each frozen run.

Prohibited:
- Training, prompt examples, rule tuning, threshold tuning, or schema changes using validation examples without resetting the split governance.
- Copying validation documents into optimization or training directories.

Required metadata:
- Manifest JSON with input and label SHA256 hashes.
- Split value `validation`.
- Source type such as `real_scan`, `born_digital`, `hybrid_pdf`, or `deidentified_real`.
- Decision log outside the manifest recording what changed after each validation run.

Example:

```bash
python scripts/build_dataset_manifest.py --input data/benchmarks/heldout_validation --labels data/benchmarks/heldout_validation/labels --output data/benchmarks/heldout_validation/manifest.json --dataset-name heldout_validation --split validation --source-type deidentified_real
python scripts/audit_benchmark_artifacts.py --input data/benchmarks/heldout_validation --labels data/benchmarks/heldout_validation/labels --manifest data/benchmarks/heldout_validation/manifest.json
python src/evaluation/benchmark.py --manifest data/benchmarks/heldout_validation/manifest.json --official --output results/benchmark/heldout_validation
```

Acceptable claim wording:
- "On the held-out validation split with manifest `<hash>`, strict macro normalized exact match was ..."
- "Validation data was used for model selection; blind-test results are reported separately."

### 3. Blind real-world test set

Purpose:
- Produce final post-freeze performance claims for publication or external review.
- Estimate real-world generalization on a post-freeze blind sample of administrative documents.

Allowed:
- One official evaluation after pipeline/model/config freeze.
- Reporting metrics with manifest hash, model version, command, and result artifact.
- Post-run error taxonomy after the official result is frozen.

Prohibited:
- Any pre-freeze tuning on blind examples.
- Training, prompt examples, threshold tuning, layout tuning, or schema changes using blind examples.
- Re-running after fixes and presenting the later run as the original blind result.

Required metadata:
- Manifest JSON with file and label hashes.
- Split value `blind_real_world`.
- Source type values for capture type and document origin.
- Freeze record: code commit, model registry entry, runtime config, and benchmark command.
- Legal/privacy review before any public release or sample publication.

Example:

```bash
python scripts/build_dataset_manifest.py --input data/benchmarks/blind_real_world --labels data/benchmarks/blind_real_world/labels --output data/benchmarks/blind_real_world/manifest.json --dataset-name blind_real_world --split blind_real_world --source-type deidentified_real
python scripts/audit_benchmark_artifacts.py --input data/benchmarks/blind_real_world --labels data/benchmarks/blind_real_world/labels --manifest data/benchmarks/blind_real_world/manifest.json
python src/evaluation/benchmark.py --manifest data/benchmarks/blind_real_world/manifest.json --official --output results/benchmark/blind_real_world
python src/evaluation/report_generator.py --input results/benchmark/blind_real_world/benchmark_results.json --output results/benchmark/blind_real_world/report.html
```

Acceptable claim wording:
- "After freezing commit `<commit>` and model `<model_version>`, the blind real-world test set with manifest `<hash>` achieved ..."
- "No prompt, model, OCR, threshold, or schema tuning used blind examples before this run."

## Manifest requirements

Every official benchmark must use a manifest with:
- `schema_version`
- `manifest_sha256`
- dataset metadata
- entries with `id`, `input_path`, `input_sha256`, `label_path`, `label_sha256`, `split`, and `source_type`

The benchmark CLI enforces `--manifest` when `--official` is used. Official runs must fail when:
- no manifest is provided,
- labels exist without matching inputs,
- inputs exist without labels,
- file hashes do not match,
- the same input hash appears in multiple splits within the manifest.

## Split leakage rules

Do not allow the same source document, image, PDF page, synthetic template instance, or manually transcribed label to appear across multiple split roles.

Automated manifest validation currently checks exact input SHA256 reuse across splits within the manifest. Human governance review must also consider:
- duplicated source PDFs rendered to different images,
- copied crops or page images,
- labels reused for synthetic prompt examples,
- pseudo-labels derived from validation or blind examples,
- cross-manifest reuse that exact per-manifest hashing cannot detect.

When leakage is found:
1. quarantine the affected examples,
2. rebuild manifests,
3. rerun audits,
4. disclose if any previously reported metric was affected.

## Result artifact rules

Benchmark result JSON must include:
- timestamp,
- official flag,
- manifest path,
- manifest SHA256,
- scalar metrics,
- confidence intervals,
- per-document results,
- strict and legacy/debug metric separation.

Report files should show:
- manifest provenance,
- strict exact and normalized metrics,
- legacy debug metric labels,
- confidence intervals,
- per-field failure examples when available.

## Publication claim checklist

Before writing a metric in a paper or README, record:
- command used,
- manifest hash,
- result artifact path,
- model name/version/checksum,
- code commit,
- hardware/runtime,
- whether the split is optimization, validation, or blind.

Never claim synthetic or validation performance as blind real-world performance.
