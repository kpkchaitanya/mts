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
| IMP-023 | 2026-05-08 | enhancement | P1 — must have | global | Single run folder + consolidated log — one invocation of compact_runner with multiple inputs produces one shared run folder containing all output PDFs; one `run.log` per run consolidating compaction report, pack layouts, telemetry, and source bound map | done |
| IMP-022 | 2026-05-08 | dx | P1 — must have | global | Functional QA scenarios — define explicit QA checklist per pipeline: what to check, how to check it, what pass looks like; run after every code change before closing a bug or feature | done |
| IMP-021 | 2026-05-08 | dx | P2 — should have | global | Single run file — eliminate bin/ folder for PYTHONPYCACHEPREFIX; use `PYTHONDONTWRITEBYTECODE=1` in .env instead; remove bin/ from repo and .gitignore | open |
| IMP-020 | 2026-05-08 | dx | P1 — must have | global | POC-first workflow — before touching spec/design/code on any bug or feature, run a minimal proof-of-concept script that reproduces the issue or validates the fix; only proceed to full implementation once POC confirms the approach | open |
| IMP-019 | 2026-05-08 | dx | P1 — must have | global | Fix classification — before fixing any bug, classify it as Simple (isolated, 1–3 lines, no logic change) or Deep (logic, architecture, data flow); Simple fixes proceed immediately; Deep fixes require: understand → strategize → POC → implement → verify; never jump to code on a Deep fix | done |
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

### IMP-023

**Date:** 2026-05-08
**Type:** enhancement
**Priority:** P1 — must have
**Feature:** global
**Status:** open

#### Description

When `compact_runner.py` is given multiple `--inputs`, it spawns a separate orchestrator subprocess per file. Each subprocess creates its own timestamped run folder (`20260508_131850`, `20260508_131913`, `20260508_131933`, …). The result is a cluttered artifacts directory — one folder per grade, each with its own `run.log`, `run-telemetry.json`, and report files.

Two changes needed:

1. **Single run folder** — one invocation of `compact_runner` with N inputs produces one shared run folder (named from the batch start time). All output PDFs land in that folder, named by source file stem + col count.
2. **Consolidated log** — one `run.log` per run that merges the content of all per-file artifacts into a single readable document: compaction report (`compaction_report.md`), pack layouts (`*_pack_layouts.csv`), run telemetry (`run-telemetry.json`), and source bound map (`*_source_bound_map.md`). Each file's section is clearly headed with the source filename. No separate artifact files per input.

#### Success Criteria

1. `python scripts/compact_runner.py --inputs g3.pdf g4.pdf g5.pdf --columns 2` produces exactly one run folder, e.g. `.agent/evals/runs/math_worksheet_generation_from_source/20260508_134500/`.
2. That folder contains: `g3_Compacted_2col.pdf`, `g4_Compacted_2col.pdf`, `g5_Compacted_2col.pdf`, and one `run.log`.
3. `run.log` has a clearly headed section per input file and consolidates: compaction report, pack layouts, telemetry, and source bound map for that file.
4. Single-input invocations are unaffected — behavior identical to today.

#### Motivation

Today's session ran grades 3, 4, 5 as three separate commands and produced 3 separate folders. Reviewing outputs required navigating 3 folders. A teacher or operator reviewing a batch run should find all outputs in one place.

#### Authority Layer to Update

- `scripts/compact_runner.py` — batch run ID, shared output path passed to each subprocess
- `src/orchestrator.py` — accept `--run-id` and `--output-dir` overrides so the runner can inject a shared folder
- `src/utils/artifact_writer.py` — support append mode for shared `run.log`

---

### IMP-022

**Date:** 2026-05-08
**Type:** dx
**Priority:** P1 — must have
**Feature:** global
**Status:** open

#### Description

There is no written QA checklist for the compact_source pipeline. After code changes, verification is ad-hoc — we run the pipeline and look at the output. This causes regressions to go unnoticed and makes it unclear what "done" means for a bug fix.

Define a formal set of functional QA scenarios: one per pipeline stage, plus end-to-end. Each scenario states what to check, how to check it (command or code snippet), and what a PASS result looks like.

#### Success Criteria

1. A `qa-scenarios.md` document exists in `.agent/specs/compact_source/` covering all 4 pipeline stages: detection, extraction, packing, reporting.
2. Each scenario has: input, command/check, expected output, pass/fail criterion.
3. QA scenarios are run and recorded after every bug fix or feature implementation before closing the item.
4. At minimum these scenarios are covered:
   - Detection: correct block count for Grade 3/4/5 EOG PDFs
   - Extraction: image dimensions match expected DPI (e.g. 1700px wide at 200 DPI on letter page)
   - Packing 1-col: page count reasonable (≤ ~1 page per block)
   - Packing 2-col: page count roughly half of 1-col
   - No infinite loop: any single PDF completes in under 60s
   - Image sharpness: embedded PNG width ≥ 1200px at 200 DPI settings
   - Output file size: > 100 KB (not blank)

#### Authority Layer to Update

- new file: `.agent/specs/compact_source/qa-scenarios.md`
- governance: reference from `compact_source-spec.md`

---

### IMP-021

**Date:** 2026-05-08
**Type:** dx
**Priority:** P2 — should have
**Feature:** global
**Status:** open

#### Description

`PYTHONPYCACHEPREFIX=./bin` in `.env` redirects all `__pycache__` folders into `bin/`. This creates a `bin/Users/neeli/...` deeply nested mirror of the source tree inside the repo — noise in the workspace tree with no benefit that outweighs the cost.

Replace with `PYTHONDONTWRITEBYTECODE=1` to suppress `.pyc` generation entirely. Remove `bin/` from the repo and from `.gitignore`.

#### Success Criteria

1. `.env` sets `PYTHONDONTWRITEBYTECODE=1`; `PYTHONPYCACHEPREFIX` removed.
2. `bin/` folder deleted from repo.
3. `.gitignore` updated accordingly.
4. Pipeline runs cleanly with no `.pyc` files generated anywhere.

#### Motivation

Reported during today's debug session: the `bin/` tree caused confusion when checking workspace structure; it also means stale `.pyc` files can silently override source changes (as observed with the DPI config fix).

#### Authority Layer to Update

- `.env`
- `.gitignore`

---

### IMP-020

**Date:** 2026-05-08
**Type:** dx
**Priority:** P1 — must have
**Feature:** global
**Status:** open

#### Description

When a bug fix or feature is non-trivial, the current workflow jumps directly from identifying the issue to editing source files. This caused today's session to apply an inverted fix (changing `not col_blocks` instead of `col_blocks`), which was deployed, produced wrong output, and required a second correction cycle.

Introduce a mandatory POC step: before any spec, design, or code change on a Deep fix, write a minimal self-contained script (e.g. `scripts/poc_<issue>.py`) that either reproduces the bug or validates the proposed fix against a real input. Only proceed to full implementation once the POC produces the expected result.

#### Success Criteria

1. For every Deep fix (see IMP-019), a POC script is created in `scripts/` before source is modified.
2. POC script output is recorded in the bug detail block before the fix is applied.
3. After the fix, the same POC script is re-run and its output confirms the fix.
4. POC scripts are kept in `scripts/` and committed — they become regression tests.

#### Authority Layer to Update

- governance: add POC step to the bug-fix workflow in `.agent/governance/`
- `bugs.md` entry template: add POC fields

---

### IMP-019

**Date:** 2026-05-08
**Type:** dx
**Priority:** P1 — must have
**Feature:** global
**Status:** open

#### Description

All bug fixes are currently treated identically regardless of complexity. A 1-line typo fix and a layout-engine infinite loop get the same "read traceback → edit → rerun" process. This caused today's infinite-loop bug to take multiple attempts: the fix was applied without a strategy phase, the inverted logic was not caught before deployment, and a second fix was needed.

Introduce a fix classification step at the start of every bug fix:

- **Simple** — isolated change, 1–5 lines, no logic or data-flow change (e.g. wrong default value, off-by-one in a constant). Proceed directly to edit + verify.
- **Deep** — involves logic, control flow, architecture, or multiple interacting components. Required workflow: **Understand → Strategize → POC → Implement → Verify**. Never skip to code.

Classification must be stated explicitly before any edit is made. If uncertain, treat as Deep.

#### Success Criteria

1. Bug-fix checklist in `.agent/governance/` includes a classification step with Simple/Deep definitions.
2. Agent always states classification and, for Deep fixes, states the strategy before touching any file.
3. Deep fixes always include a POC step (see IMP-020).
4. The inverted-fix class of error (applying the logical complement of the intended fix) is eliminated.

#### Motivation

Today's `_compute_layout` infinite-loop fix used `and not col_blocks` instead of `and col_blocks` — the exact opposite of the correct condition. This was a Deep fix applied without a strategy or POC phase. The error was only caught because the output was visually inspected.

#### Authority Layer to Update

- new/updated: `.agent/governance/bug-fix-workflow.md`
- `bugs.md` entry template: add Classification field

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
