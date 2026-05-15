# VietIDP Zero-to-Hero Q1 On-Prem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform `OCR-LLM_Research` into a world-class, Q1-paper-ready, 100% on-premise Vietnamese administrative document intelligence platform covering research data, OCR/LLM/VLM algorithms, benchmark governance, frontend, backend, database, distributed processing, security, Git/CI, deployment, and reproducible publication artifacts.

**Architecture:** Standardize on a single canonical stack: FastAPI backend, React/Vite frontend, PostgreSQL production database, durable local/distributed job processing, Docker/on-prem deployment, and a hybrid layout-aware OCR→LLM pipeline. Keep the current OCR+LLM system as the reproducible baseline, add strict benchmark governance and layout-aware field candidates, and treat VLM/document-parser models as controlled ablations until they beat the baseline under strict blind-set evaluation.

**Tech Stack:** Python 3.10, FastAPI, SQLAlchemy/Alembic, PostgreSQL, optional Redis/RQ or Celery only if restored intentionally, React 18, Vite, Axios, OpenCV, EasyOCR, VietOCR, PaddleOCR/PaddleOCR-VL optional, YOLO/DocLayout-style layout detection, Ollama/llama.cpp local LLM runtime, Qwen2.5 3B/7B, optional Qwen2.5-VL/Vintern/olmOCR ablations, Docker Compose, GitHub Actions/pre-commit, RTX 5070 8GB VRAM target.

---

## 1. Current-state diagnosis

The repository already has a strong prototype, but it is not yet Q1-paper-grade or enterprise-grade.

### Active strengths

- Main pipeline exists in `src/pipeline/ocr_llm_pipeline.py`: preprocess → YOLO stamp detection/removal → EasyOCR+VietOCR → Qwen2.5 via Ollama → JSON validation.
- OCR engine exists in `src/ocr/engine.py`, including a useful PDF text-layer shortcut.
- Local LLM stack exists in `src/llm/ollama_client.py` and `src/llm/prompts.py`.
- Experimental VLM path exists in `src/llm/qwen2_vl_inference.py`.
- Evaluation exists in `src/evaluation/benchmark.py`, `src/evaluation/profiler.py`, and `src/evaluation/report_generator.py`.
- FastAPI app exists in `src/api/fastapi_app.py`, routes in `src/api/routes.py`, DB models in `src/api/database.py`, and task compatibility layer in `src/api/tasks.py`.
- React workspace exists in `apps/frontend/src/pages/WorkspacePage.jsx`, with document viewer, extraction panel, overview, chat, upload, export, history, and dashboard components.

### Critical risks

- `data/test/labels/bench_000..099.json` exists, but the matching `bench_*.jpg` benchmark images are missing from the repo, so the saved benchmark cannot be rerun from current state.
- `scripts/generate_benchmark_data.py` creates synthetic auto-labeled documents, while `docs/scientific_paper_q1_draft.md` claims manually labeled noisy administrative documents. This must be corrected before Q1 submission.
- Current extraction F1 in `src/evaluation/benchmark.py` uses permissive substring matching; strict field-level metrics are required.
- The weakest field is `nguoi_ky`, with saved artifact evidence suggesting about 6% exact signer correctness.
- `src/evaluation/profiler.py` profiles one sample, not full benchmark distributions.
- FastAPI auth exists in `src/api/auth.py` and is imported in `src/api/routes.py`, but routes do not enforce it.
- `Config.API_KEY` defaults to empty, and `verify_api_key()` treats empty config as open access.
- `/uploads` is served publicly in `src/api/fastapi_app.py`, and frontend builds direct URLs in `apps/frontend/src/pages/WorkspacePage.jsx`.
- Legacy Express backend under `apps/backend/` is still runnable and unauthenticated.
- `src/api/tasks.py` is an in-memory thread queue, not true Celery/distributed processing, while `docker-compose.yml` still provisions Redis and `celery-worker`.
- `Dockerfile.backend` copies `data/` into the image, and `.dockerignore` does not exclude `data/`, `results/`, or `models/` broadly enough.
- `.gitignore` misses important active runtime paths such as `data/uploads/`, `backend/uploads/`, and `results/`.
- No `.github/workflows` CI pipeline exists; package test scripts are incomplete or placeholders.

---

## 2. Scientific policy for “điểm tuyệt đối”

The project can aim for perfect scores internally, but Q1 claims must be scientifically defensible.

### Required benchmark separation

1. **Optimization set**
   - Can include regenerated synthetic data, known legacy data, and development examples.
   - Can be used repeatedly for prompt tuning, OCR tuning, and model selection.
   - Perfect scores here are acceptable as engineering milestones, not as final scientific claims.

2. **Held-out validation set**
   - Used for ablation decisions and model selection.
   - Must have fixed manifest, labels, hashes, and split assignment.
   - Can be evaluated repeatedly, but all tuning decisions must be logged.

3. **Blind real-world test set**
   - Used once after model/config freeze.
   - Must contain real scan/photo/born-digital administrative documents, de-identified locally.
   - Must not be used for prompt tuning, model training, threshold tuning, or schema changes.

### Responsible target metrics

Current saved result: CER 23.54%, WER 25.60%, legacy extraction F1 0.7495, avg latency 16.89s/page, peak VRAM 2.16GB.

**Optimization/synthetic target:**
- CER: 12–16% initially, stretch <10%.
- Legacy debug extraction F1: 0.90–0.98.
- `nguoi_ky` exact: 55–80% depending on stamp/legibility.
- Latency: 7–12s/page warm-start.

**Held-out validation target:**
- Strict field macro F1: 0.80–0.88.
- Normalized field macro F1: 0.84–0.91.
- Signer exact: 45–70%.
- Report 95% bootstrap confidence intervals.

**Blind real-world target:**
- Strict field macro F1: 0.72–0.84.
- Normalized field macro F1: 0.78–0.88.
- No post-freeze tuning.

If any track reaches 100%, the report must state exactly which dataset, metric, split, and tuning policy produced that score.

---

## 3. Canonical architecture decisions

### Keep as canonical

- Backend: `src/api/fastapi_app.py`, `src/api/routes.py`.
- Frontend: `apps/frontend/` React/Vite app.
- Pipeline: `src/pipeline/ocr_llm_pipeline.py`, but extended with layout candidates and backend swappability.
- OCR baseline: current EasyOCR detector + VietOCR recognizer in `src/ocr/engine.py`.
- LLM baseline: local Ollama in `src/llm/ollama_client.py`.
- Database: PostgreSQL for production; SQLite only for explicit dev/test mode.
- Deployment: Docker Compose for local/on-prem starter, hardened for production profile.

### Retire or quarantine

- `apps/backend/` Express service: archive/quarantine; do not run in canonical deployment.
- Root `Dockerfile` if it targets old Node backend.
- `apps/frontend/src/pages/resultspage.jsx` if it remains mock/localStorage-driven.
- Celery/Redis docs and compose services unless actual durable worker integration is restored.
- GAN/Paddle/VLM/RAG claims unless supported by active code and strict benchmark evidence.

---

## 4. File ownership map

### AI/research pipeline

- Modify `src/pipeline/ocr_llm_pipeline.py` — canonical orchestrator; add layout regions, candidates, OCR backend selection, metadata output.
- Modify `src/ocr/engine.py` — preserve current behavior while routing through backend adapters and PDF text-layer shortcut.
- Create `src/ocr/backends/base.py` — OCR backend protocol.
- Create `src/ocr/backends/easy_vietocr.py` — current EasyOCR+VietOCR adapter.
- Create `src/ocr/backends/paddle.py` — optional PaddleOCR adapter with graceful dependency failure.
- Create `src/pipeline/layout_regions.py` — deterministic administrative document zones.
- Create `src/pipeline/field_candidates.py` — deterministic extraction candidates from OCR lines/regions.
- Modify `src/llm/prompts.py` — candidate-aware, no-hallucination prompts.
- Modify `src/llm/ollama_client.py` — schema validation, deterministic benchmark settings, repair retry.
- Create `src/llm/extraction_schema.py` — Pydantic schema for extraction JSON and evidence fields.
- Refactor `src/llm/qwen2_vl_inference.py` — optional VLM adapter for ablations.

### Evaluation/reproducibility

- Modify `src/evaluation/benchmark.py` — manifest-driven, strict metrics, no silent fallback.
- Modify `src/evaluation/profiler.py` — batch profiling, p50/p90/p95/max, cold/warm modes.
- Modify `src/evaluation/report_generator.py` — strict/normalized metrics, CIs, ablations, provenance.
- Create `src/evaluation/normalization.py` — Unicode/date/text normalization.
- Create `src/evaluation/extraction_metrics.py` — strict exact, normalized exact, token F1, char similarity.
- Create `src/evaluation/bootstrap.py` — confidence intervals.
- Create `src/evaluation/manifest.py` — file/label hashes, split checks, dataset metadata.
- Create `scripts/audit_benchmark_artifacts.py` — detect missing inputs and claim risks.
- Modify `scripts/generate_benchmark_data.py` — deterministic seed, manifest, richer synthetic templates.
- Create `scripts/build_dataset_manifest.py` — dataset hashing and validation.
- Create `scripts/run_ablation_matrix.py` — repeatable OCR/layout/LLM/VLM experiments.

### Backend/API/database

- Modify `src/api/auth.py` — fail closed when auth is required.
- Modify `src/api/routes.py` — enforce auth on all non-health document/chat/export endpoints; add safe upload validation; return safe errors.
- Modify `src/api/fastapi_app.py` — stop public static upload serving or protect it through authenticated endpoints.
- Modify `src/api/database.py` — stop implicit production SQLite fallback; prepare for migrations; normalize edited/raw/evidence fields.
- Modify `src/api/tasks.py` — choose either local thread mode for dev or durable queue mode for production.
- Create `migrations/` via Alembic — schema versioning.
- Create `src/api/storage.py` — raw upload, derived preview, result artifact paths and retention policy.
- Create `src/api/schemas.py` — request/response schemas separate from ORM models.

### Frontend

- Modify `apps/frontend/src/services/api.js` — use same-origin `/api` by default; support API key header if enabled; avoid hard-coded localhost exports.
- Modify `apps/frontend/vite.config.js` — proxy to FastAPI port 8000 or remove proxy if Axios uses explicit URL.
- Modify `apps/frontend/src/pages/WorkspacePage.jsx` — no direct anonymous `/uploads` assumptions; use authorized preview URLs; show candidate/evidence/confidence.
- Modify `apps/frontend/src/components/DocumentViewer.jsx` — support OCR overlays and field-to-bbox linking.
- Modify `apps/frontend/src/components/ExtractionPanel.jsx` — show raw vs edited fields, evidence, confidence, validation warnings.
- Modify `apps/frontend/src/components/OverviewPanel.jsx` — align fields with backend schema.
- Modify `apps/frontend/src/components/ChatPanel.jsx` — use RAG or safe context routing once backend supports it.
- Quarantine or rewrite `apps/frontend/src/pages/resultspage.jsx` if it remains mock-driven.

### Deployment/Git/CI/security

- Modify `docker-compose.yml` — remove invalid Celery worker or restore real durable queue; restrict internal ports; use production-safe credentials through env.
- Modify `Dockerfile.backend` — do not copy `data/` into image; mount runtime data as volumes.
- Modify `.dockerignore` — exclude `data/`, `results/`, `models/`, uploads, caches, logs by default.
- Modify `.gitignore` — ignore `data/uploads/`, `backend/uploads/`, `results/`, debug outputs, SQLite DBs, logs, caches, local model artifacts.
- Create `.github/workflows/ci.yml` — Python tests, frontend build/lint, artifact guard.
- Create `.pre-commit-config.yaml` — secret scan, large file guard, formatting/linting.
- Modify README/docs — one canonical dev/prod startup path and benchmark protocol.

---

## 5. Phase-by-phase implementation plan

### Phase 0 — Architecture freeze and repo hygiene

**Purpose:** Stop architectural drift before optimizing models.

- [ ] Mark FastAPI + React + PostgreSQL + local Ollama + `VietIDPPipeline` as the canonical stack in README.
- [ ] Add a short architecture decision record for retiring/quarantining `apps/backend/`.
- [ ] Update Windows scripts so they do not launch the legacy Node backend by default.
- [ ] Fix `apps/frontend/vite.config.js` proxy target from port 5000 to 8000 or remove it in favor of same-origin `/api`.
- [ ] Align `apps/frontend/src/services/api.js` with deployment: default to same-origin in Docker/prod and explicit `VITE_API_URL` only in dev.
- [ ] Update `.gitignore` and `.dockerignore` to block generated/sensitive runtime artifacts.
- [ ] Add an artifact audit script to list commit-eligible PDFs/images/results/logs/DB files.

**Acceptance criteria:** A new contributor can identify the single canonical stack in 10 minutes; running startup scripts no longer starts the wrong backend; generated artifacts are not commit-eligible.

**Verification:** run artifact audit; run frontend dev server against FastAPI; verify no legacy Node process is required.

---

### Phase 1 — Dataset governance and benchmark repair

**Purpose:** Make all research claims traceable and rerunnable.

- [ ] Create `src/evaluation/manifest.py` with manifest loading, SHA256 hashing, required fields, split leakage checks, missing file checks.
- [ ] Create `scripts/audit_benchmark_artifacts.py` to detect labels without images, results without manifest, and paper claims not backed by artifacts.
- [ ] Modify `src/evaluation/benchmark.py` to fail loudly if `data/test` has labels but no images; remove silent fallback to `data/raw` in official mode.
- [ ] Modify `scripts/generate_benchmark_data.py` to accept `--seed`, `--count`, `--output-dir`, `--split`, `--noise-profile`, and write manifest entries.
- [ ] Create three dataset tiers: `legacy_100`, `synthetic_regenerated`, `heldout_validation`, `blind_real_world`.
- [ ] Write annotation guidelines for real administrative documents: field definitions, null/illegible policy, dual annotation, adjudication, de-identification.
- [ ] Build manifests for the 150 real PDFs under `data/raw/pdf_test` once labels exist.

**Acceptance criteria:** Every benchmark run references a manifest hash; all active benchmark examples have input + label pairs; paper draft clearly distinguishes synthetic, validation, and blind real-world data.

**Verification:** dataset audit passes; regenerated synthetic data is reproducible from seed; missing-image benchmark run fails with a clear message.

---

### Phase 2 — Publication-grade metrics and reporting

**Purpose:** Replace optimistic debugging metrics with Q1-safe evaluation.

- [ ] Create `src/evaluation/normalization.py` for NFC Unicode normalization, whitespace collapse, punctuation cleanup, case folding, administrative date normalization, and optional accent-insensitive secondary scoring.
- [ ] Create `src/evaluation/extraction_metrics.py` with strict exact, normalized exact, token F1, character similarity, TP/FP/FN/missed/extra, macro/micro averages.
- [ ] Keep old substring matching only as `legacy_debug_f1`.
- [ ] Create `src/evaluation/bootstrap.py` for 95% bootstrap confidence intervals.
- [ ] Modify `src/evaluation/benchmark.py` to output per-field and per-document metrics, including separate `nguoi_ky`, document type, capture condition, and source type.
- [ ] Modify `src/evaluation/report_generator.py` to produce strict tables, normalized tables, CIs, failure examples, and dataset provenance.
- [ ] Add tests under `tests/evaluation/` for normalizers, strict matching, legacy matching, and bootstrap stability.

**Acceptance criteria:** Reports include strict exact, normalized exact, token F1, CER/WER, latency, VRAM, 95% CI, and per-field breakdown. Legacy `avg_f1=0.7495` can only appear under a legacy/debug label.

**Verification:** unit tests pass; saved baseline report regenerated with both old and strict metrics; substring containment no longer counts as strict correctness.

---

### Phase 3 — OCR and document parsing upgrade

**Purpose:** Reduce CER and solve layout/signer failures before over-tuning LLM prompts.

- [ ] Refactor `src/ocr/engine.py` to route through an `OCRBackend` contract while preserving current behavior.
- [ ] Add `src/ocr/backends/easy_vietocr.py` as the baseline adapter.
- [ ] Add optional `src/ocr/backends/paddle.py` for local PaddleOCR; absence of Paddle dependencies must not break default startup.
- [ ] Add `Config.OCR_BACKEND` and `Config.OCR_BACKEND_CANDIDATES`.
- [ ] Fix `src/pipeline/ocr_llm_pipeline.py` PDF path to use text-layer extraction for born-digital PDFs before rendering pages.
- [ ] Add document triage: born-digital PDF, scanned PDF, image, hybrid PDF.
- [ ] Add OCR line grouping and reading-order normalization.
- [ ] Run ablations for EasyOCR+VietOCR, PaddleOCR-only, Paddle detector+VietOCR, DPI, deskew, denoise, stamp removal on/off.

**Acceptance criteria:** CER drops on held-out validation; born-digital PDF latency improves significantly; OCR output contains backend, confidence, method, and line metadata.

**Verification:** `scripts/run_ablation_matrix.py` produces comparable OCR tables; worst 25 CER pages are reviewed; PDF text-layer cases skip unnecessary OCR.

---

### Phase 4 — Layout-aware field localization

**Purpose:** Improve key fields by exploiting Vietnamese administrative layout regularity.

- [ ] Create `src/pipeline/layout_regions.py` with deterministic zones: `header_left_agency`, `header_right_date`, `title_subject`, `body`, `signature_block`, `stamp_overlap`.
- [ ] Create `src/pipeline/field_candidates.py` with deterministic candidates:
  - `so_hieu` near `Số:`.
  - `ngay_ban_hanh` from top-right date patterns.
  - `co_quan_ban_hanh` from top-left lines excluding national motto.
  - `loai_van_ban` from centered title zone.
  - `trich_yeu` from subject/title-adjacent lines.
  - `nguoi_ky` from bottom-right name-like lines excluding titles and `(Đã ký)`.
- [ ] Modify `src/pipeline/ocr_llm_pipeline.py` to output `regions`, `field_candidates`, `evidence`, and confidence signals.
- [ ] Add a focused signer-zone OCR pass after stamp removal using crop expansion and multiple thresholding variants.
- [ ] Add tests proving national motto is not agency and titles are not signer names.

**Acceptance criteria:** `nguoi_ky`, `ngay_ban_hanh`, and `co_quan_ban_hanh` improve without degrading `so_hieu`; UI can show evidence/candidates for each field.

**Verification:** per-field validation metrics; signer-zone failure analysis; tests under `tests/pipeline/` pass.

---

### Phase 5 — Schema-guided local LLM extraction and fine-tuning

**Purpose:** Make LLM extraction deterministic, auditable, and trainable.

- [ ] Create `src/llm/extraction_schema.py` with versioned schema for required fields plus optional confidence/evidence.
- [ ] Modify `src/llm/prompts.py` to accept raw OCR plus field candidates; forbid hallucination; require empty string for missing/illegible fields.
- [ ] Modify `src/llm/ollama_client.py` to validate JSON through schema, retry once with a repair prompt, and expose deterministic benchmark settings.
- [ ] Build train-only QLoRA data: noisy OCR + candidates → adjudicated JSON.
- [ ] Modify `scripts/train_qlora.py` to save model metadata: dataset manifest hash, split, base model, quantization, seed, hyperparameters, commit SHA.
- [ ] Compare local models: `qwen2.5:3b`, `qwen2.5:7b` 4-bit, fine-tuned 3B/7B if serving path supports adapters.
- [ ] Add hard negatives: agency vs national motto, title vs signer, subject truncation, date format ambiguity.

**Acceptance criteria:** All successful extractions are schema-valid; hallucination/missingness are tracked; train/validation/blind leakage checks pass.

**Verification:** LLM schema tests pass; ablation table shows prompt-only vs candidate-aware vs fine-tuned performance.

---

### Phase 6 — Optional VLM/document-parser ablations

**Purpose:** Explore best global methods without destabilizing the production baseline.

- [ ] Refactor `src/llm/qwen2_vl_inference.py` as an adapter that returns the same extraction schema.
- [ ] Add optional adapters/configs for local or documented-hardware-limited ablations:
  - Qwen2.5-VL 3B/7B quantized.
  - Vintern-1B-v2 for Vietnamese OCR/VQA/document tasks.
  - PaddleOCR-VL 0.9B for multilingual document parsing.
  - olmOCR-2 7B/FP8 for OCR/Markdown conversion if feasible.
- [ ] Record model license, checksum, quantization, runtime, VRAM, latency, and failure modes.
- [ ] Keep VLM pseudo-labels out of validation/blind ground truth.

**Acceptance criteria:** VLMs appear only as reproducible ablation rows unless they beat the baseline under strict metrics and fit on target hardware.

**Verification:** ablation report includes strict metrics, latency, VRAM, and qualitative errors.

---

### Phase 7 — Backend security and API hardening

**Purpose:** Make the app safe for sensitive on-prem documents.

- [ ] Modify `src/api/auth.py` so production mode fails closed if auth is enabled but no key is configured.
- [ ] Add `Depends(verify_api_key)` to all non-health routes in `src/api/routes.py`.
- [ ] Add API-key header support to `apps/frontend/src/services/api.js` through environment config.
- [ ] Replace extension-only upload checks with MIME/magic-number validation and safe filename generation.
- [ ] Stop returning raw exception strings to clients in `src/api/fastapi_app.py` and `src/api/routes.py`; log detailed errors server-side only.
- [ ] Remove public `/uploads` static serving or replace with authenticated preview/download endpoints.
- [ ] Add per-document access policy hooks even if single-user API-key mode is the initial default.
- [ ] Quarantine `apps/backend/` legacy service or add the same auth/upload protections if it remains runnable.

**Acceptance criteria:** no unauthenticated document listing, upload, export, chat, edit, delete, or raw-preview access; upload validation rejects disguised files; user-visible errors do not leak filesystem/model internals.

**Verification:** API integration tests for unauthorized access; upload validation tests; manual attempt to fetch `/uploads/...` without auth fails.

---

### Phase 8 — Database, migrations, storage, and durable jobs

**Purpose:** Move from prototype persistence to production-grade state management.

- [ ] Introduce Alembic migrations for `src/api/database.py` models.
- [ ] Stop implicit production fallback from PostgreSQL to SQLite; make SQLite explicit dev/test mode only.
- [ ] Normalize storage into raw uploads, derived previews, OCR artifacts, extraction JSON, benchmark artifacts, and logs.
- [ ] Create `src/api/storage.py` for path generation, retention, and deletion.
- [ ] Extend schema for pages, OCR lines, field evidence, review edits, job state, audit logs, and benchmark runs.
- [ ] Decide task architecture:
  - local thread queue for single-user dev profile, or
  - durable Redis/RQ/Celery worker for production profile.
- [ ] If durable mode is chosen, persist job status, retries, progress, failure reason, and cancellation state.
- [ ] Ensure GPU concurrency is controlled: one heavy OCR/LLM job at a time by default on 8GB VRAM.

**Acceptance criteria:** schema changes are migration-controlled; job state survives API restart in production mode; deletion purges DB rows and associated files according to retention policy.

**Verification:** migration up/down test; restart API during async processing; delete document and verify files/rows are gone.

---

### Phase 9 — Frontend product-grade UX

**Purpose:** Turn the UI into a real human-in-the-loop IDP workspace.

- [ ] Make `WorkspacePage.jsx` the canonical document screen.
- [ ] Remove production dependency on mock/localStorage result flows in `resultspage.jsx`.
- [ ] Replace direct `/uploads` URLs with authenticated preview/download URLs.
- [ ] Add field confidence, evidence spans, candidate alternatives, and OCR bbox highlight interactions.
- [ ] Support multi-page preview with thumbnails and page-level OCR overlays.
- [ ] Add review workflow: raw extraction, edited extraction, verified flag, reviewer timestamp, export.
- [ ] Align `ExtractionPanel.jsx` and `OverviewPanel.jsx` with the versioned backend schema.
- [ ] Add clear upload states, durable job status, retry/error messages, and cancellation if backend supports it.
- [ ] Add researcher/admin views for benchmark reports and ablation comparisons if useful.

**Acceptance criteria:** user journey is coherent: upload → processing → review evidence → edit → verify → export/history/chat. No production screen uses mock results.

**Verification:** browser test through MCP/manual Playwright; frontend build passes; API contract tests validate expected response shape.

---

### Phase 10 — Deployment, on-prem operations, and privacy compliance

**Purpose:** Make the system genuinely on-premise and reproducible.

- [ ] Modify `Dockerfile.backend` to stop copying `data/` into image layers.
- [ ] Modify `.dockerignore` to exclude `data/`, `results/`, `models/`, uploads, caches, logs, notebooks outputs, and local DBs unless explicitly whitelisted.
- [ ] Modify `docker-compose.yml`:
  - do not expose Postgres/Redis/Ollama host ports by default,
  - remove invalid `celery-worker` or implement it correctly,
  - use env-provided credentials,
  - mount data/model/results volumes explicitly.
- [ ] Create dev and production compose profiles.
- [ ] Add local model registry: model name, version, quantization, checksum, license, storage path, download date.
- [ ] Add offline verification checklist: after weights are present, process documents with internet disabled.
- [ ] Add retention policy for raw uploads, derived previews, OCR full text, extracted JSON, debug artifacts, and benchmark outputs.
- [ ] Re-check legal references for 2026 Vietnamese personal-data and AI law; do not rely only on Nghị định 13/2023 if newer laws/decrees apply.

**Acceptance criteria:** clean machine with local model/data volumes can run offline; production profile does not leak services to host unnecessarily; privacy claims match actual storage/network behavior.

**Verification:** Docker build with empty runtime data; offline smoke processing; network request audit shows no external AI API calls.

---

### Phase 11 — Git, CI/CD, testing, and quality gates

**Purpose:** Prevent regressions and accidental data leakage.

- [ ] Add `.github/workflows/ci.yml` with Python tests, frontend lint/build, artifact guard, and Docker build smoke.
- [ ] Add `.pre-commit-config.yaml` for secret scan, large file blocking, formatting/linting, and forbidden path checks.
- [ ] Fix npm scripts:
  - root `package.json` should not have placeholder failing tests,
  - `apps/frontend/package.json` should include lint/build/test scripts,
  - legacy backend package should be archived or excluded.
- [ ] Add backend API tests for auth, upload validation, document CRUD, export, chat error handling.
- [ ] Add evaluation tests for metrics and manifests.
- [ ] Add frontend tests for upload flow, workspace rendering, extraction edit/save, and export link generation.
- [ ] Add periodic benchmark smoke job on a tiny de-identified fixture set.
- [ ] Require branch/PR discipline: small commits, no generated sensitive artifacts, no model weights, no raw document commits.

**Acceptance criteria:** CI blocks leaks and broken builds; all critical functions have tests; generated/sensitive artifacts cannot be committed accidentally.

**Verification:** CI green; pre-commit blocks sample PDF/result/log/model files; branch audit shows no unintended files.

---

### Phase 12 — Q1 paper package and public project readiness

**Purpose:** Convert engineering work into publishable, reproducible scientific contribution.

- [ ] Rewrite `docs/scientific_paper_q1_draft.md` so every result maps to a command, manifest hash, model version, and report artifact.
- [ ] Add reproducibility appendix: hardware, OS, CUDA, Python env, Docker profile, model checksums, seeds, dataset manifests.
- [ ] Add ablation tables:
  - preprocessing/stamp removal,
  - OCR backend,
  - layout candidates,
  - LLM prompt/schema/fine-tune,
  - optional VLM/document parser,
  - speed/VRAM.
- [ ] Add error taxonomy:
  - stamp overlap,
  - signer hidden/illegible,
  - agency vs national motto,
  - date OCR confusion,
  - subject truncation,
  - mobile perspective/blur,
  - multi-page reading-order issues.
- [ ] Add limitations and ethics/privacy section.
- [ ] Add README badges only after CI exists.
- [ ] Create a clean demo dataset that is de-identified and legally publishable.
- [ ] Create `docs/reproducibility.md`, `docs/dataset_protocol.md`, `docs/model_registry.md`, and `docs/security_model.md`.

**Acceptance criteria:** A reviewer can reproduce reported tables from code+manifests+models; paper claims do not overstate synthetic/legacy data; public project contains no sensitive raw data.

**Verification:** independent rerun from clean clone and local model/data volumes; paper-to-artifact traceability checklist passes.

---

## 6. Verification matrix

### Unit tests

```bash
pytest tests/evaluation/test_normalization.py -v
pytest tests/evaluation/test_extraction_metrics.py -v
pytest tests/evaluation/test_manifest.py -v
pytest tests/ocr/test_backend_contract.py -v
pytest tests/pipeline/test_layout_regions.py -v
pytest tests/pipeline/test_field_candidates.py -v
pytest tests/llm/test_extraction_schema.py -v
pytest tests/api/test_auth.py -v
pytest tests/api/test_upload_validation.py -v
```

Expected: all pass; no benchmark/paper claim may be updated while these fail.

### Benchmark integrity

```bash
python scripts/audit_benchmark_artifacts.py --input data/test --labels data/test/labels
python src/evaluation/benchmark.py --input data/test --ground-truth data/test/labels --official
```

Expected: if `bench_*.jpg` files are missing, both fail clearly. If restored, benchmark writes manifest-linked strict metrics.

### Synthetic regeneration

```bash
python scripts/generate_benchmark_data.py --seed 20260429 --count 100 --output-dir data/benchmarks/synthetic_regenerated --split validation --noise-profile mixed
python scripts/build_dataset_manifest.py --input data/benchmarks/synthetic_regenerated --labels data/benchmarks/synthetic_regenerated/labels --output data/benchmarks/synthetic_regenerated/manifest.json
python src/evaluation/benchmark.py --manifest data/benchmarks/synthetic_regenerated/manifest.json --output results/benchmark/synthetic_regenerated
```

Expected: deterministic manifest, no missing files, strict/normalized metrics saved.

### Ablation matrix

```bash
python scripts/run_ablation_matrix.py --manifest data/benchmarks/synthetic_regenerated/manifest.json --output results/ablation/synthetic_regenerated
```

Expected: comparable rows for OCR backend, layout on/off, LLM model/prompt variants, optional VLM/document parser variants.

### Performance profiling

```bash
python src/evaluation/profiler.py --manifest data/benchmarks/synthetic_regenerated/manifest.json --output results/benchmark/synthetic_regenerated/profiler_results.json
```

Expected: per-stage mean, median, p90, p95, max, cold/warm distinction, peak VRAM.

### Full-stack local smoke

```bash
uvicorn src.api.fastapi_app:app --host 0.0.0.0 --port 8000
cd apps/frontend && npm run dev
```

Then verify in browser:

- upload document,
- observe durable status,
- open workspace,
- inspect OCR/evidence/candidates,
- edit and save extraction,
- export JSON/CSV,
- ask chat question,
- check console/network errors.

### On-prem/offline proof

- Pre-download models into local `models/` or Ollama volume.
- Disconnect internet.
- Start local services.
- Process a de-identified PDF/image.
- Confirm no external AI/network calls occur.

---

## 7. Recommended execution order

1. **Architecture freeze and legacy quarantine.**
2. **Artifact ignore/audit and benchmark governance.**
3. **Strict metrics and manifest-driven benchmark.**
4. **PDF triage, OCR backend contracts, and text-layer shortcut.**
5. **Layout-aware field candidates and signer recovery.**
6. **Schema-guided LLM extraction and QLoRA metadata.**
7. **Backend auth, safe uploads, protected previews.**
8. **Migrations, storage policy, durable jobs.**
9. **Frontend evidence-based review UX.**
10. **Docker/on-prem hardening and offline validation.**
11. **CI/pre-commit/testing.**
12. **Paper rewrite, ablations, reproducibility appendix.**

This order prevents optimizing an invalid benchmark, fixes security before wider deployment, and aligns product engineering with publishable research.

---

## 8. Key “done” definition

The project is Q1/project-famous ready only when all are true:

- Every metric table is generated from a manifest-linked command.
- Data splits are frozen and leakage-checked.
- The blind test is evaluated only after final configuration freeze.
- The app can run fully offline with local models.
- No sensitive raw data, uploads, result JSONs, model weights, or DBs are committed accidentally.
- FastAPI routes are authenticated and raw uploads are not publicly served.
- DB schema is migration-controlled.
- Task processing is either explicitly local-dev-only or durable/restart-safe in production.
- Frontend shows evidence and confidence, not just final JSON.
- Docker/docs/scripts all describe the same active system.
- The paper honestly distinguishes synthetic, validation, blind real-world, legacy, and ablation results.

---

## 9. Full model retraining strategy

The user is willing to retrain every model if needed. The plan should use that willingness, but remain hardware-realistic.

### Hardware reality on RTX 5070 8GB

Training a base LLM/VLM from scratch is not realistic on the target laptop. It would require large multi-GPU infrastructure, massive corpora, and months of engineering. For this project, the best Q1-grade strategy is:

- train/fine-tune specialist document models from scratch where feasible;
- fine-tune or QLoRA compact open models where full training is not feasible;
- distill large/offline teacher outputs into smaller local specialist models;
- evaluate every training decision through strict held-out and blind benchmarks.

### Model training tracks

1. **Stamp detector**
   - Train/fine-tune YOLO on Vietnamese stamp boxes.
   - Data: synthetic stamps + real stamps from scanned administrative documents.
   - Metrics: mAP50, mAP50-95, recall on stamp-over-text cases.
   - Acceptance: high recall without excessive false positives in signature zone.

2. **Stamp removal / stamp segmentation**
   - Train a lightweight U-Net/SegFormer-small or improve HybridStampMatting.
   - Data: clean/stamped paired synthetic pages plus real manually masked stamp regions.
   - Metrics: OCR CER before/after removal, mask IoU, signer-zone readability.
   - Acceptance: improves OCR and signer extraction; does not erase black text.

3. **Document layout detector**
   - Train a small YOLO/DocLayout-style model for Vietnamese administrative zones.
   - Classes: agency header, national motto, document number, date, title, subject, body, recipient, signature block, stamp, appendix/table.
   - Metrics: mAP and downstream field F1, not mAP alone.
   - Acceptance: improves agency/date/signer extraction over deterministic layout baseline.

4. **OCR detection/recognition**
   - Fine-tune VietOCR on Vietnamese administrative line crops and signer-zone crops.
   - Optionally train a small detector or use Paddle detector + VietOCR recognizer.
   - Data: line crops with exact transcription; include diacritics, noisy scans, stamp overlap.
   - Metrics: CER/WER by zone, especially header and signature zones.
   - Acceptance: lowers CER on held-out validation without overfitting synthetic fonts.

5. **OCR post-correction model**
   - Train a small sequence correction model or constrained dictionary/rule system for administrative text.
   - Data: OCR noisy text → corrected text pairs from train split only.
   - Metrics: CER/WER reduction and no harmful corrections to identifiers.
   - Acceptance: improves natural text while preserving `so_hieu`, dates, names.

6. **Field candidate ranker**
   - Train a lightweight classifier/ranker to score OCR lines for each field.
   - Features: normalized text, bbox position, region id, font/line shape, OCR confidence, regex hits.
   - Metrics: top-1/top-3 candidate accuracy by field.
   - Acceptance: gives LLM better candidates and improves traceability.

7. **Text LLM extractor**
   - QLoRA fine-tune Qwen2.5 3B/7B or equivalent local model on OCR+candidates → JSON.
   - Data: train split only; include hard negatives and null/illegible cases.
   - Metrics: strict field exact, normalized exact, hallucination rate, malformed JSON rate.
   - Acceptance: beats prompt-only baseline on validation and remains stable offline.

8. **VLM/document parser ablation**
   - Fine-tune or evaluate compact VLMs only if they fit 8GB or can be run in quantized/offloaded mode.
   - Candidates: Qwen2.5-VL, Vintern-1B, PaddleOCR-VL, olmOCR-style OCR parser.
   - Metrics: strict extraction, OCR structure quality, latency, VRAM.
   - Acceptance: promoted only if it beats OCR→LLM baseline under strict metrics.

### Training governance

- Every trained model must have metadata: dataset manifest hash, code commit, base model, license, seed, hyperparameters, train/validation split, metrics, and hardware.
- No validation/blind sample can appear in training, pseudo-labeling, prompt examples, or model selection.
- All experiments must write immutable result artifacts under a versioned experiment directory.
- The final paper should report both the best model and strong baselines, not only the winning configuration.

---

## 10. Execution packages for subagent-driven implementation

Because this is a full research/product system, implementation should be split into packages. Each package should get a dedicated detailed plan before coding.

### Package A — Architecture, hygiene, and security baseline

Scope:
- quarantine legacy Express backend;
- fix `.gitignore` / `.dockerignore`;
- align Vite/FastAPI ports;
- enforce API auth;
- stop public upload serving;
- safe upload validation;
- safe error responses.

Done when:
- no unauthenticated document API access exists;
- generated/sensitive artifacts are blocked;
- only FastAPI + React is canonical.

### Package B — Dataset governance and strict evaluation

Scope:
- manifests;
- artifact audit;
- strict metrics;
- bootstrap CI;
- deterministic synthetic benchmark;
- real-data annotation protocol;
- report generator updates.

Done when:
- benchmark cannot run officially without manifest;
- old substring F1 is clearly legacy-only;
- all results are reproducible and traceable.

### Package C — OCR, preprocessing, and layout intelligence

Scope:
- OCR backend contract;
- PDF text-layer triage;
- Paddle/VietOCR ablations;
- layout regions;
- field candidates;
- signer-zone OCR recovery;
- stamp-removal ablations.

Done when:
- CER improves on validation;
- signer/date/agency fields improve;
- OCR output carries evidence and region metadata.

### Package D — LLM/VLM extraction and model training

Scope:
- extraction schema;
- candidate-aware prompts;
- JSON repair;
- QLoRA dataset and training metadata;
- local model comparison;
- optional VLM/document-parser ablations.

Done when:
- extraction is schema-valid;
- hallucination rate is measured;
- fine-tuned model or prompt pipeline beats baseline under strict metrics.

### Package E — Backend, database, storage, and durable jobs

Scope:
- Alembic migrations;
- storage abstraction;
- raw/preview/result retention;
- job persistence;
- restart-safe processing;
- GPU concurrency control;
- audit logs.

Done when:
- jobs survive restart in production mode;
- deletions purge DB and files;
- schema changes are migration-controlled.

### Package F — Frontend human-in-the-loop workspace

Scope:
- authorized previews;
- OCR overlays;
- evidence/candidate display;
- confidence warnings;
- raw vs edited JSON;
- verified review state;
- export/history/chat polish.

Done when:
- the product journey is upload → process → review evidence → edit → verify → export/chat;
- no production flow depends on mock data.

### Package G — Deployment, CI, and offline operations

Scope:
- dev/prod Docker profiles;
- no data copied into image layers;
- local model registry;
- CI workflow;
- pre-commit;
- offline smoke test;
- security/dependency scanning.

Done when:
- clean on-prem setup runs offline;
- CI blocks leaks and broken builds;
- docs match actual deployment.

### Package H — Q1 paper and public release package

Scope:
- corrected paper draft;
- dataset protocol;
- reproducibility appendix;
- ablation tables;
- error taxonomy;
- limitations/privacy/ethics;
- de-identified demo dataset.

Done when:
- every paper table maps to command + manifest + model metadata + result artifact;
- public repo contains no sensitive data.

---

## 11. Research sources to verify before publication

- PaddleOCR-VL 0.9B multilingual document parser: https://arxiv.org/abs/2510.14528 and https://huggingface.co/PaddlePaddle/PaddleOCR-VL
- Qwen2.5-VL: https://arxiv.org/abs/2502.13923 and https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- Vintern-1B Vietnamese multimodal model: https://arxiv.org/abs/2408.12480 and https://huggingface.co/5CD-AI/Vintern-1B-v2
- DocLayout-YOLO: https://arxiv.org/abs/2410.12628 and https://github.com/opendatalab/DocLayout-YOLO
- olmOCR 2: https://arxiv.org/abs/2510.19817 and https://github.com/allenai/olmocr
- VietOCR Transformer OCR: https://github.com/pbcquoc/vietocr and https://pbcquoc.github.io/vietocr/
- Vietnam personal-data and AI legal context to re-check with legal counsel before publication: https://thuvienphapluat.vn/van-ban/EN/Bo-may-hanh-chinh/Law-91-2025-QH15-Personal-Data-Protection/665440/tieng-anh.aspx, https://thuvienphapluat.vn/van-ban/EN/Cong-nghe-thong-tin/Decree-356-2025-ND-CP-elaborating-on-certain-articles-of-Law-on-personal-data-protection/689146/tieng-anh.aspx, https://congbao.chinhphu.vn/van-ban/luat-so-134-2025-qh15-468694.htm
