# backlog.md â€” MTS Feature Improvement Backlog

**Scope:** All features and workflows within the MTS AI-native system
**Version:** v1
**Status:** Active

---

## How to Log an Improvement

An improvement is anything that makes the system better but is **not a bug** â€” new capability, quality upgrade, workflow efficiency, or developer experience.

Add new items at the **top** of the Open Items table (newest first).

**Type values:**

| Type | Meaning |
|------|---------|
| `feature` | Net-new capability that does not exist yet |
| `enhancement` | Improvement to existing behavior |
| `eval` | Improvement to evaluation rubric or scoring |
| `spec` | Clarification or expansion of a spec |
| `dx` | Developer experience â€” tooling, templates, workflow clarity |

**Priority values:** `P1 â€” must have` Â· `P2 â€” should have` Â· `P3 â€” nice to have`

**Status values:** `open` Â· `in-progress` Â· `done` Â· `deferred`

---

## Open Items

| ID | Date | Type | Priority | Feature | Summary | Status |
|----|------|------|----------|---------|---------|--------|
> **compact_source-specific items** have been moved to `.agent/specs/compact_source/backlog.md` (CS-001 through CS-024). Cross-references to original IMP IDs are preserved there. Only global / cross-feature items remain below.

| ID | Date | Type | Priority | Feature | Summary | Status |
|----|------|------|----------|---------|---------|--------|| IMP-026 | 2026-05-10 | knowledge | P2 — should have | global | Exam format knowledge gap — exam structure knowledge (STAAR, EOG, NY Regents: format, page layout, block types, answer key conventions) is scattered across specs/PRDs; consolidate into `knowledge/exam-formats.md` as a Layer 3 domain knowledge asset; all specs should reference it rather than re-define format rules | open |
| IMP-025 | 2026-05-10 | dx | P2 — should have | global | Doc size violations — split 4 oversized governance/spec docs per standards.md §8: `holistic-ai-native-cognitive-architecture.md` (1710 lines), `holistic-ai-product-management-framework.md` (598 lines), `agent.md` (498 lines), `compact_source-spec.md` (613 lines); strip inline duplication from agent.md §4 (already in standards.md) | open || IMP-023 | 2026-05-08 | enhancement | P1 â€” must have | global | Single run folder + consolidated log â€” one `compact_runner` invocation with N inputs produces one shared run folder; one `run.log` per run | done |
| IMP-022 | 2026-05-08 | dx | P1 â€” must have | global | Functional QA scenarios â€” explicit QA checklist per pipeline stage; run after every code change before closing a bug or feature | done |
| IMP-021 | 2026-05-08 | dx | P2 â€” should have | global | Single run file â€” eliminate `PYTHONPYCACHEPREFIX=./bin`; use `PYTHONDONTWRITEBYTECODE=1` in `.env`; remove `bin/` from repo and `.gitignore` | open |
| IMP-020 | 2026-05-08 | dx | P1 â€” must have | global | POC-first workflow â€” before touching spec/design/code on any Deep bug or feature, write and run a minimal POC script; only proceed to full implementation once POC confirms the approach | open |
| IMP-019 | 2026-05-08 | dx | P1 â€” must have | global | Fix classification â€” classify every bug fix as Simple / Moderate / Deep before any edit; Deep fixes require Understand â†’ Strategize â†’ POC â†’ Implement â†’ Verify | done |
| IMP-016 | 2026-04-26 | dx | P2 | global | CONTRIBUTING.md and dev setup guide | open |
| IMP-015 | 2026-04-26 | dx | P2 | global | CI pipeline â€” GitHub Actions: lint, typecheck, test on push | open |
| IMP-014 | 2026-04-26 | dx | P2 | global | Dependency lockfile via pip-tools (`requirements.lock`) | open |
| IMP-013 | 2026-04-26 | dx | P2 | global | mypy type-checking enforced in CI | open |
| IMP-007 | 2026-04-26 | enhancement | P1 | global | Exception taxonomy (`src/exceptions.py`) â€” typed exceptions, not bare Exception | open |
| IMP-006 | 2026-04-26 | enhancement | P1 | global | Input validation â€” validate PDF before pipeline (readable, not corrupted, not password-protected) | open |
| IMP-005 | 2026-04-26 | enhancement | P1 | global | API resilience â€” exponential backoff + jitter on all Claude API calls | open |
| IMP-004 | 2026-04-26 | enhancement | P1 | global | Structured logging â€” replace bare `print()` with `logging` module; per-run log file | open |
| IMP-002 | 2026-04-26 | dx | P1 | global | Test suite â€” pytest, unit + integration, Claude API mocked | open |

---

## SDLC Phase Plan

> **compact_source phase plan (Phases 1â€“5)** has been moved to `.agent/specs/compact_source/backlog.md`. The global phase plan below covers only cross-feature engineering phases.

Work is sequenced into 6 incremental phases. Each phase builds on the previous and delivers a testable, observable system increment.

### Phase 1 â€” Foundation (Spec + PRD)
*Theme: Define before building. Every clause must be testable.*

| Item | Description |
|------|-------------|
| IMP-001 | Write `compact_source-prd.md` (teacher personas, user stories, success metrics, non-goals) |
| IMP-001 | Refactor spec v6 into a `compact_source`-only spec with format detection contract and edge case catalogue |

**Gate:** Spec has no untestable clauses. Every acceptance criterion maps to an eval dimension.
**Gate Status:** âœ… PASSED â€” 2026-04-26 â€” `compact_source-prd.md` and `compact_source-spec.md` created in `.agent/specs/compact_source/`

---

### Phase 2 â€” Observability (Telemetry + Logging)
*Theme: If you canâ€™t measure it, you canâ€™t improve it.*

| Item | Description |
|------|-------------|
| IMP-003 | Emit `run-telemetry.json` per run (format detected, block count, page/size stats, stage timings, defects) |
| IMP-004 | Replace all bare `print()` with `logging` module; write per-run `run.log` to artifacts folder |

**Gate:** Every run produces machine-readable telemetry. Batch runs produce a `summary.json`.

---

### Phase 3 â€” Resilience (Robustness + Safety)
*Theme: The pipeline should never crash silently.*

| Item | Description |
|------|-------------|
| IMP-005 | Add exponential backoff + jitter to `ClaudeClient` â€” configurable max retries, per-call timeout |
| IMP-006 | Add `validate_input()` at top of pipeline â€” PDF readable, not corrupted, not password-protected |
| IMP-007 | Create `src/exceptions.py` â€” typed exception hierarchy (DetectionError, ExtractionError, PackingError, ValidationError) |

**Gate:** No bare `Exception` raises in pipeline. All Claude failures are retried before escalating.

---

### Phase 4 â€” Quality (Eval + Gate)
*Theme: The system must know when it has done a good job.*

| Item | Description |
|------|-------------|
| IMP-002 | Build test suite â€” unit tests per module, integration test end-to-end, Claude API mocked |
| IMP-008 | Build `evaluator.py` â€” scores output on 5 dimensions, writes `eval-score.json` and `eval-report.md` |
| IMP-009 | Add quality gate to pipeline â€” if eval score < threshold, block PASS and trigger repair or escalation |

**Gate:** Every run has an eval score. No run passes without meeting the threshold.

---

### Phase 5 â€” Self-Improvement (Learn + Heal)
*Theme: The system gets better without human intervention on known defect classes.*

| Item | Description |
|------|-------------|
| IMP-010 | Register golden PDFs; run comparator automatically on every matching run |
| IMP-011 | Build learnings extractor â€” reads telemetry + eval, classifies failures, appends to `learnings.md` |
| IMP-012 | Build self-healing engine â€” repair playbook, auto-retry with targeted fix, escalate to `bugs.md` |

**Gate:** The system auto-recovers from at least 3 known defect classes. All failures produce a structured `learnings.md` entry.

---

### Phase 6 â€” CI/CD (Automation + Enforcement)
*Theme: Quality is enforced automatically, not by convention.*

| Item | Description |
|------|-------------|
| IMP-013 | Add mypy type-checking to CI |
| IMP-014 | Add pip-tools lockfile for reproducible installs |
| IMP-015 | GitHub Actions CI â€” lint, typecheck, test on every push |
| IMP-016 | Write CONTRIBUTING.md â€” dev setup, test instructions, architecture overview |

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

<What triggered this â€” a weak eval score, teacher feedback, a failed run, an observed pattern?>

#### Success Criteria

<How will you know this improvement is done? What would a PASS eval look like?>

#### Proposed Approach

<High-level implementation idea. Leave blank if unknown â€” the spec revision process will fill this in.>

#### Authority Layer to Update

<Which document(s) need to change: spec Â· eval Â· agent Â· workflow Â· governance>
```

---

## Improvement Detail Records

---

### IMP-023

**Date:** 2026-05-08
**Type:** enhancement
**Priority:** P1 â€” must have
**Feature:** global
**Status:** open

#### Description

When `compact_runner.py` is given multiple `--inputs`, it spawns a separate orchestrator subprocess per file. Each subprocess creates its own timestamped run folder (`20260508_131850`, `20260508_131913`, `20260508_131933`, â€¦). The result is a cluttered artifacts directory â€” one folder per grade, each with its own `run.log`, `run-telemetry.json`, and report files.

Two changes needed:

1. **Single run folder** â€” one invocation of `compact_runner` with N inputs produces one shared run folder (named from the batch start time). All output PDFs land in that folder, named by source file stem + col count.
2. **Consolidated log** â€” one `run.log` per run that merges the content of all per-file artifacts into a single readable document: compaction report (`compaction_report.md`), pack layouts (`*_pack_layouts.csv`), run telemetry (`run-telemetry.json`), and source bound map (`*_source_bound_map.md`). Each file's section is clearly headed with the source filename. No separate artifact files per input.

#### Success Criteria

1. `python scripts/compact_runner.py --inputs g3.pdf g4.pdf g5.pdf --columns 2` produces exactly one run folder, e.g. `.agent/evals/runs/math_worksheet_generation_from_source/20260508_134500/`.
2. That folder contains: `g3_Compacted_2col.pdf`, `g4_Compacted_2col.pdf`, `g5_Compacted_2col.pdf`, and one `run.log`.
3. `run.log` has a clearly headed section per input file and consolidates: compaction report, pack layouts, telemetry, and source bound map for that file.
4. Single-input invocations are unaffected â€” behavior identical to today.

#### Motivation

Today's session ran grades 3, 4, 5 as three separate commands and produced 3 separate folders. Reviewing outputs required navigating 3 folders. A teacher or operator reviewing a batch run should find all outputs in one place.

#### Authority Layer to Update

- `scripts/compact_runner.py` â€” batch run ID, shared output path passed to each subprocess
- `src/orchestrator.py` â€” accept `--run-id` and `--output-dir` overrides so the runner can inject a shared folder
- `src/utils/artifact_writer.py` â€” support append mode for shared `run.log`

---

### IMP-022

**Date:** 2026-05-08
**Type:** dx
**Priority:** P1 â€” must have
**Feature:** global
**Status:** open

#### Description

There is no written QA checklist for the compact_source pipeline. After code changes, verification is ad-hoc â€” we run the pipeline and look at the output. This causes regressions to go unnoticed and makes it unclear what "done" means for a bug fix.

Define a formal set of functional QA scenarios: one per pipeline stage, plus end-to-end. Each scenario states what to check, how to check it (command or code snippet), and what a PASS result looks like.

#### Success Criteria

1. A `qa-scenarios.md` document exists in `.agent/specs/compact_source/` covering all 4 pipeline stages: detection, extraction, packing, reporting.
2. Each scenario has: input, command/check, expected output, pass/fail criterion.
3. QA scenarios are run and recorded after every bug fix or feature implementation before closing the item.
4. At minimum these scenarios are covered:
   - Detection: correct block count for Grade 3/4/5 EOG PDFs
   - Extraction: image dimensions match expected DPI (e.g. 1700px wide at 200 DPI on letter page)
   - Packing 1-col: page count reasonable (â‰¤ ~1 page per block)
   - Packing 2-col: page count roughly half of 1-col
   - No infinite loop: any single PDF completes in under 60s
   - Image sharpness: embedded PNG width â‰¥ 1200px at 200 DPI settings
   - Output file size: > 100 KB (not blank)

#### Authority Layer to Update

- new file: `.agent/specs/compact_source/qa-scenarios.md`
- governance: reference from `compact_source-spec.md`

---

### IMP-021

**Date:** 2026-05-08
**Type:** dx
**Priority:** P2 â€” should have
**Feature:** global
**Status:** open

#### Description

`PYTHONPYCACHEPREFIX=./bin` in `.env` redirects all `__pycache__` folders into `bin/`. This creates a `bin/Users/neeli/...` deeply nested mirror of the source tree inside the repo â€” noise in the workspace tree with no benefit that outweighs the cost.

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
**Priority:** P1 â€” must have
**Feature:** global
**Status:** open

#### Description

When a bug fix or feature is non-trivial, the current workflow jumps directly from identifying the issue to editing source files. This caused today's session to apply an inverted fix (changing `not col_blocks` instead of `col_blocks`), which was deployed, produced wrong output, and required a second correction cycle.

Introduce a mandatory POC step: before any spec, design, or code change on a Deep fix, write a minimal self-contained script (e.g. `scripts/poc_<issue>.py`) that either reproduces the bug or validates the proposed fix against a real input. Only proceed to full implementation once the POC produces the expected result.

#### Success Criteria

1. For every Deep fix (see IMP-019), a POC script is created in `scripts/` before source is modified.
2. POC script output is recorded in the bug detail block before the fix is applied.
3. After the fix, the same POC script is re-run and its output confirms the fix.
4. POC scripts are kept in `scripts/` and committed â€” they become regression tests.

#### Authority Layer to Update

- governance: add POC step to the bug-fix workflow in `.agent/governance/`
- `bugs.md` entry template: add POC fields

---

### IMP-019

**Date:** 2026-05-08
**Type:** dx
**Priority:** P1 â€” must have
**Feature:** global
**Status:** done

#### Description

All bug fixes are currently treated identically regardless of complexity. A 1-line typo fix and a layout-engine infinite loop get the same "read traceback â†’ edit â†’ rerun" process. This caused today's infinite-loop bug to take multiple attempts: the fix was applied without a strategy phase, the inverted logic was not caught before deployment, and a second fix was needed.

Introduce a fix classification step at the start of every bug fix:

- **Simple** â€” isolated change, 1â€“5 lines, no logic or data-flow change (e.g. wrong default value, off-by-one in a constant). Proceed directly to edit + verify.
- **Deep** â€” involves logic, control flow, architecture, or multiple interacting components. Required workflow: **Understand â†’ Strategize â†’ POC â†’ Implement â†’ Verify**. Never skip to code.

Classification must be stated explicitly before any edit is made. If uncertain, treat as Deep.

#### Success Criteria

1. Bug-fix checklist in `.agent/governance/` includes a classification step with Simple/Deep definitions.
2. Agent always states classification and, for Deep fixes, states the strategy before touching any file.
3. Deep fixes always include a POC step (see IMP-020).
4. The inverted-fix class of error (applying the logical complement of the intended fix) is eliminated.

#### Motivation

Today's `_compute_layout` infinite-loop fix used `and not col_blocks` instead of `and col_blocks` â€” the exact opposite of the correct condition. This was a Deep fix applied without a strategy or POC phase. The error was only caught because the output was visually inspected.

#### Authority Layer to Update

- new/updated: `.agent/governance/bug-fix-workflow.md`
- `bugs.md` entry template: add Classification field

---

> **compact_source detail records** (IMP-018, IMP-017, IMP-012, IMP-011, IMP-010, IMP-009, IMP-008, IMP-003, IMP-001) have been moved to `.agent/specs/compact_source/backlog.md`. Cross-references to original IMP IDs are preserved there.

