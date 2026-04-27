# backlog.md — MTS Feature Improvement Backlog

**Scope:** All features and workflows within the MTS AI-native system
**Version:** v1
**Status:** Active

---

## How to Log an Improvement

An improvement is anything that makes the system better but is **not a bug** — new capability, quality upgrade, workflow efficiency, or developer experience.

Add new items at the **top** of the Open Items table (newest first).

**Type values:**

| Type | Meaning |
|------|---------|
| `feature` | Net-new capability that does not exist yet |
| `enhancement` | Improvement to existing behavior |
| `eval` | Improvement to evaluation rubric or scoring |
| `spec` | Clarification or expansion of a spec |
| `dx` | Developer experience — tooling, templates, workflow clarity |

**Priority values:** `P1 — must have` · `P2 — should have` · `P3 — nice to have`

**Status values:** `open` · `in-progress` · `done` · `deferred`

---

## Open Items

| ID | Date | Type | Priority | Feature | Summary | Status |
|----|------|------|----------|---------|---------|--------|
| IMP-018 | 2026-04-27 | feature | P2 — should have | compact_source | Question number overlay — for image_heavy PDFs (EOG) the question number is embedded in the footer ("N of 40") and is lost when the footer is cropped; packer must overlay sequential number labels ("1.", "2.", …) as white-backed text in the top-left of each block in the output PDF; `--question-start N` allows user to shift the sequence; `--no-question-numbers` suppresses; auto-enabled for `is_image_heavy=True`, suppressed for text_rich | done |
| IMP-017 | 2026-04-27 | eval | P1 | compact_source | Block height efficiency checker — post-run check measures `extracted block height / page height` per block; flags any block ≥ 95% (`IMAGE_HEAVY_HEIGHT_WARN_FRACTION`) in compaction report; image_heavy format only; auto-heal deferred to IMP-018 | done |
| IMP-016 | 2026-04-26 | dx | P2 | global | CONTRIBUTING.md and dev setup guide | open |
| IMP-015 | 2026-04-26 | dx | P2 | global | CI pipeline — GitHub Actions: lint, typecheck, test on push | open |
| IMP-014 | 2026-04-26 | dx | P2 | global | Dependency lockfile via pip-tools (`requirements.lock`) | open |
| IMP-013 | 2026-04-26 | dx | P2 | global | mypy type-checking enforced in CI | open |
| IMP-012 | 2026-04-26 | feature | P1 | compact_source | Self-healing engine — classify defect, apply repair, retry, escalate | open |
| IMP-011 | 2026-04-26 | feature | P1 | compact_source | Learnings extractor — auto-populate learnings.md after every eval | open |
| IMP-010 | 2026-04-26 | feature | P1 | compact_source | Golden file registry — register reference PDFs, run comparator on every run | open |
| IMP-009 | 2026-04-26 | feature | P1 | compact_source | Quality gate — block PASS if eval score below threshold | open |
| IMP-008 | 2026-04-26 | feature | P1 | compact_source | Evaluator module (`evaluator.py`) — 5-dimension scoring after every run | open |
| IMP-007 | 2026-04-26 | enhancement | P1 | global | Exception taxonomy (`src/exceptions.py`) — typed exceptions, not bare Exception | open |
| IMP-006 | 2026-04-26 | enhancement | P1 | global | Input validation — validate PDF before pipeline (readable, not corrupted, not password-protected) | open |
| IMP-005 | 2026-04-26 | enhancement | P1 | global | API resilience — exponential backoff + jitter on all Claude API calls | open |
| IMP-004 | 2026-04-26 | enhancement | P1 | global | Structured logging — replace bare print() with logging module, per-run log file | open |
| IMP-003 | 2026-04-26 | feature | P1 | compact_source | Run telemetry — machine-readable run-telemetry.json in every run folder | open |
| IMP-002 | 2026-04-26 | dx | P1 | global | Test suite — pytest, unit + integration, Claude API mocked | open |
| IMP-001 | 2026-04-26 | spec | P1 | compact_source | PRD + refined spec — separate compact_source PRD and spec, add format detection contract | done |

---

## SDLC Phase Plan

Work is sequenced into 6 incremental phases. Each phase builds on the previous and delivers a testable, observable system increment.

### Phase 1 — Foundation (Spec + PRD)
*Theme: Define before building. Every clause must be testable.*

| Item | Description |
|------|-------------|
| IMP-001 | Write `compact_source-prd.md` (teacher personas, user stories, success metrics, non-goals) |
| IMP-001 | Refactor spec v6 into a `compact_source`-only spec with format detection contract and edge case catalogue |

**Gate:** Spec has no untestable clauses. Every acceptance criterion maps to an eval dimension.
**Gate Status:** ✅ PASSED — 2026-04-26 — `compact_source-prd.md` and `compact_source-spec.md` created in `.agent/specs/compact_source/`

---

### Phase 2 — Observability (Telemetry + Logging)
*Theme: If you can’t measure it, you can’t improve it.*

| Item | Description |
|------|-------------|
| IMP-003 | Emit `run-telemetry.json` per run (format detected, block count, page/size stats, stage timings, defects) |
| IMP-004 | Replace all bare `print()` with `logging` module; write per-run `run.log` to artifacts folder |

**Gate:** Every run produces machine-readable telemetry. Batch runs produce a `summary.json`.

---

### Phase 3 — Resilience (Robustness + Safety)
*Theme: The pipeline should never crash silently.*

| Item | Description |
|------|-------------|
| IMP-005 | Add exponential backoff + jitter to `ClaudeClient` — configurable max retries, per-call timeout |
| IMP-006 | Add `validate_input()` at top of pipeline — PDF readable, not corrupted, not password-protected |
| IMP-007 | Create `src/exceptions.py` — typed exception hierarchy (DetectionError, ExtractionError, PackingError, ValidationError) |

**Gate:** No bare `Exception` raises in pipeline. All Claude failures are retried before escalating.

---

### Phase 4 — Quality (Eval + Gate)
*Theme: The system must know when it has done a good job.*

| Item | Description |
|------|-------------|
| IMP-002 | Build test suite — unit tests per module, integration test end-to-end, Claude API mocked |
| IMP-008 | Build `evaluator.py` — scores output on 5 dimensions, writes `eval-score.json` and `eval-report.md` |
| IMP-009 | Add quality gate to pipeline — if eval score < threshold, block PASS and trigger repair or escalation |

**Gate:** Every run has an eval score. No run passes without meeting the threshold.

---

### Phase 5 — Self-Improvement (Learn + Heal)
*Theme: The system gets better without human intervention on known defect classes.*

| Item | Description |
|------|-------------|
| IMP-010 | Register golden PDFs; run comparator automatically on every matching run |
| IMP-011 | Build learnings extractor — reads telemetry + eval, classifies failures, appends to `learnings.md` |
| IMP-012 | Build self-healing engine — repair playbook, auto-retry with targeted fix, escalate to `bugs.md` |

**Gate:** The system auto-recovers from at least 3 known defect classes. All failures produce a structured `learnings.md` entry.

---

### Phase 6 — CI/CD (Automation + Enforcement)
*Theme: Quality is enforced automatically, not by convention.*

| Item | Description |
|------|-------------|
| IMP-013 | Add mypy type-checking to CI |
| IMP-014 | Add pip-tools lockfile for reproducible installs |
| IMP-015 | GitHub Actions CI — lint, typecheck, test on every push |
| IMP-016 | Write CONTRIBUTING.md — dev setup, test instructions, architecture overview |

**Gate:** Every push is automatically linted, type-checked, and tested. No manual gate-keep required.

---


---

## Entry Template

When logging an improvement, add a row to the Open Items table AND create a detail block below:

```
### IMP-001

**Date:** YYYY-MM-DD
**Type:** feature | enhancement | eval | spec | dx
**Priority:** P1 / P2 / P3
**Feature:** <feature name, or "global" if system-wide>
**Status:** open

#### Description

<What should be improved and why. Focus on the outcome for students or teachers, not the implementation.>

#### Motivation

<What triggered this — a weak eval score, teacher feedback, a failed run, an observed pattern?>

#### Success Criteria

<How will you know this improvement is done? What would a PASS eval look like?>

#### Proposed Approach

<High-level implementation idea. Leave blank if unknown — the spec revision process will fill this in.>

#### Authority Layer to Update

<Which document(s) need to change: spec · eval · agent · workflow · governance>
```

---

## Improvement Detail Records

---

### IMP-018

**Date:** 2026-04-27
**Type:** feature
**Priority:** P2 — should have
**Feature:** compact_source
**Status:** done

#### Description

For image-heavy PDFs (EOG format) each source page embeds the question content as a full-page raster image. The question number is text in the page footer ("1 of 40", "2 of 40", …) — not embedded in the image itself. When BUG-002 was fixed, the footer crop correctly eliminates the blank gap below the content, but it also permanently removes the only location where the question number appeared. The compacted output PDF therefore has no question numbers on any block.

Students and teachers using the compacted output cannot identify which question they are working on.

#### Evidence

- Visual inspection of gr_3 EOG compacted output (run 20260427_092907): all 15 blocks show question content only — no question numbers visible.
- `QuestionBlock.question_number` is assigned sequentially from 1 during `_detect_image_heavy_blocks()` and propagates to `ExtractedBlock.question_number`, but `PdfPacker._render()` inserts only the image; it never writes the number into the output PDF.
- gr_3 source footer text: "1 of 40", "2 of 40", … "40 of 40" — these are the sole location of question numbers in the EOG source format.

#### Success Criteria

1. Each block in the output PDF displays its question number as a text label (e.g., "1.") at the top-left corner, overlaid on the block image with a white background for legibility.
2. `--question-start N` shifts the entire label sequence — first block shows "N.", second "N+1.", etc.
3. `--no-question-numbers` suppresses labeling entirely (round-trip fidelity mode).
4. Labels are auto-enabled when `is_image_heavy=True` and auto-suppressed for text-rich PDFs where numbers are embedded in the image content.
5. Labels survive a round-trip: opening the output PDF with a text extractor returns the label text.
6. Unit tests: TC-PP-01 … TC-PP-05 (see spec §13).

#### Proposed Approach

- `PdfPacker.__init__`: add `add_question_numbers: bool = False`, `question_start: int = 1`
- `PdfPacker._render`: after `page.insert_image(rect, …)`, draw white-backed text label using PyMuPDF `page.draw_rect` + `page.insert_text` with `overlay=True`
- `run_compact_source`: add matching params; auto-detect: `add_question_numbers = True if is_image_heavy and caller did not override`
- `src/config.py`: add `QUESTION_LABEL_FONT_SIZE = 10.0`
- CLI: `--no-question-numbers` flag, `--question-start N`

#### Authority Layer to Update

- spec §5 (new testable claim), §6 (packing stage), §12 (config table), §13 (TC-PP-01 … TC-PP-05)
- design §3 (packer rendering step)
- program.md harness engineering table (test count update)
