# compact_source-backlog.md — compact_source Feature Backlog

**Feature:** `compact_source`
**Folder:** `.agent/specs/compact_source/`
**Version:** v1
**Date:** 2026-05-10
**Status:** Active

> This backlog contains only `compact_source`-specific improvement items.
> Global / cross-feature items remain in `.agent/improvements/backlog.md`.
> Global IMP-NNN IDs are cross-referenced where applicable.

---

## How to Add an Item

Add new items at the top of the Open Items table (newest first). Status values: `open` · `in-progress` · `done` · `deferred`.

---

## Open Items

| ID | Date | Type | Priority | Summary | Global Ref | Status |
|----|------|------|----------|---------|------------|--------|
| CS-024 | 2026-05-10 | spec | P1 | QA scenarios for US-05 (STAAR text-rich) — EARS written; need STAAR Grade 3/4/5 PDFs; write QA-STAAR-01 through QA-STAAR-04 (format detection, block count, extraction quality, 2-col pack); currently zero QA coverage for STAAR path (RISK-01) | IMP-024 | in-progress |
| CS-021 | 2026-05-08 | dx | P2 | Single run file — eliminate `PYTHONPYCACHEPREFIX=./bin` in `.env`; use `PYTHONDONTWRITEBYTECODE=1`; remove `bin/` from repo and `.gitignore` | IMP-021 | open |
| CS-020 | 2026-05-08 | dx | P1 | POC-first workflow — before touching spec/design/code on any Deep bug or feature, write a minimal POC script to validate the approach | IMP-020 | open |
| CS-012 | 2026-04-26 | feature | P1 | Self-healing engine — classify defect from telemetry, apply repair playbook, auto-retry, escalate to `bugs.md` on third failure | IMP-012 | open |
| CS-011 | 2026-04-26 | feature | P1 | Learnings extractor — reads telemetry + eval after every run; classifies failures; appends structured entry to `learnings.md` | IMP-011 | open |
| CS-010 | 2026-04-26 | feature | P1 | Golden file registry — register reference PDFs; run comparator automatically on every matching run | IMP-010 | open |
| CS-009 | 2026-04-26 | feature | P1 | Quality gate — block PASS if eval score below threshold; trigger repair or escalation | IMP-009 | open |
| CS-008 | 2026-04-26 | feature | P1 | Evaluator module (`evaluator.py`) — 5-dimension scoring after every run; writes `eval-score.json` and `eval-report.md` | IMP-008 | open |
| CS-007 | 2026-04-26 | enhancement | P1 | Exception taxonomy (`src/exceptions.py`) — typed exceptions: `ValidationError`, `DetectionError`, `ExtractionError`, `PackingError`, `ReportingError`; no bare `Exception` raises | IMP-007 | open |
| CS-006 | 2026-04-26 | enhancement | P1 | Input validation — `validate_input()` before pipeline starts: PDF readable, not corrupted, not password-protected; raises `ValidationError` with specific message | IMP-006 | open |
| CS-005 | 2026-04-26 | enhancement | P1 | API resilience — exponential backoff + jitter on all Claude API calls; configurable max retries and per-call timeout | IMP-005 | open |
| CS-004 | 2026-04-26 | enhancement | P1 | Structured logging — replace all bare `print()` with `logging` module; write per-run `run.log` to artifact folder | IMP-004 | open |
| CS-003 | 2026-04-26 | feature | P1 | Run telemetry — machine-readable `run-telemetry.json` per run; `batch-telemetry.json` for folder runs; schema defined in `compact_source-lld.md §6` | IMP-003 | open |
| CS-002 | 2026-04-26 | dx | P1 | Test suite — pytest unit + integration tests; `BlockDetector`, `PdfPacker`, `Reporter` all covered; Claude API mocked | IMP-002 | open |

---

## Closed / Done Items

| ID | Date | Type | Priority | Summary | Global Ref | Status |
|----|------|------|----------|---------|------------|--------|
| CS-023 | 2026-05-08 | enhancement | P1 | Single run folder — one `compact_runner` invocation with N inputs produces one shared run folder + one `run.log` | IMP-023 | done |
| CS-022 | 2026-05-08 | dx | P1 | Functional QA scenarios — explicit QA checklist per pipeline stage; run after every code change; `compact_source-qa-scenarios.md` created | IMP-022 | done |
| CS-019 | 2026-05-08 | dx | P1 | Fix classification — bug fixes classified Simple/Moderate/Deep before any edit; Deep fixes require Understand → Strategize → POC → Implement → Verify | IMP-019 | done |
| CS-018 | 2026-04-27 | feature | P2 | Question number labels — for `image_heavy` PDFs, overlay sequential "N." labels at top-left of each block in output PDF; `--question-start N`; `--no-question-numbers` | IMP-018 | done |
| CS-017 | 2026-04-27 | eval | P1 | Block height efficiency checker — flag blocks ≥ 95% of page height as `⚠ OVERSIZED` in compaction report; FAIL verdict if any present | IMP-017 | done |
| CS-001 | 2026-04-26 | spec | P1 | PRD + refined spec — create `compact_source-prd.md`; refactor spec into `compact_source`-only document with format detection contract and edge case catalogue | IMP-001 | done |

---

## SDLC Phase Plan

Work is sequenced into 6 incremental phases. Each phase builds on the previous and delivers a testable, observable system increment. See `compact_source-hld.md §5` for the holistic platform impact diagram.

### Phase 1 — Foundation ✅ COMPLETE
*Define before building. Every clause must be testable.*

| Item | Deliverable |
|------|------------|
| CS-001 | `compact_source-prd.md` + `compact_source-spec.md` |

**Gate:** Spec has no untestable clauses. Every acceptance criterion maps to an eval dimension.
**Gate Status:** ✅ PASSED — 2026-04-26

---

### Phase 2 — Observability 🔲 PLANNED
*If you can't measure it, you can't improve it.*

| Item | Deliverable |
|------|------------|
| CS-003 | `run-telemetry.json` per run; `batch-telemetry.json` for folder runs |
| CS-004 | Replace all `print()` with `logging`; write `run.log` to artifact folder |

**Design:** `compact_source-lld.md §6–§7`
**Platform:** `platform/observability/platform-observability-spec.md`
**Gate:** Every run produces machine-readable telemetry. Batch runs produce `batch-telemetry.json`.

---

### Phase 3 — Resilience 🔲 PLANNED
*The pipeline should never crash silently.*

| Item | Deliverable |
|------|------------|
| CS-005 | Exponential backoff + jitter on Claude API calls |
| CS-006 | `validate_input()` at top of pipeline |
| CS-007 | `src/exceptions.py` — typed exception hierarchy |

**Platform:** `platform/resilience/platform-resilience-spec.md`
**Gate:** No bare `Exception` raises. All Claude failures retried before escalation.

---

### Phase 4 — Quality 🔲 PLANNED
*The system must know when it has done a good job.*

| Item | Deliverable |
|------|------------|
| CS-002 | pytest suite — unit + integration; Claude API mocked |
| CS-008 | `evaluator.py` — 5-dimension scoring; `eval-score.json`; `eval-report.md` |
| CS-009 | Quality gate — block PASS if eval score < threshold |

**Platform:** `platform/quality/platform-quality-spec.md`
**Gate:** Every run has an eval score. No run passes without meeting threshold.

---

### Phase 5 — Self-Improvement 🔲 PLANNED
*The system gets better without human intervention on known defect classes.*

| Item | Deliverable |
|------|------------|
| CS-010 | Golden file registry + auto-comparator per run |
| CS-011 | Learnings extractor — classify failures → `learnings.md` |
| CS-012 | Self-healing engine — repair playbook, auto-retry |

**Platform:** `platform/self-improvement/platform-self-improvement-spec.md`
**Gate:** System auto-recovers from ≥ 3 known defect classes. All failures produce structured `learnings.md` entry.

---

### Phase 6 — CI/CD 🔲 PLANNED
*Quality is enforced automatically, not by convention.*

These are global items tracked in `.agent/improvements/backlog.md`:

| Global ID | Deliverable |
|-----------|------------|
| IMP-013 | mypy type-checking in CI |
| IMP-014 | pip-tools lockfile |
| IMP-015 | GitHub Actions CI — lint · typecheck · test on push |
| IMP-016 | CONTRIBUTING.md — dev setup + architecture overview |

**Gate:** Every push is automatically linted, type-checked, and tested.
