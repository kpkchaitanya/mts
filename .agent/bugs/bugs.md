# bugs.md — MTS Bug Log

**Scope:** All features and workflows within the MTS AI-native system
**Version:** v1
**Status:** Active

---

## How to Log a Bug

Copy the entry template below. Add new bugs at the **top** of the Open Bugs table (newest first).

**Severity levels:**

| Level | Meaning |
|-------|---------|
| P1 — Critical | Wrong answer reaches a student; pipeline halts unexpectedly |
| P2 — High | Output is incorrect or unusable; workaround exists |
| P3 — Medium | Output is degraded but still usable; quality is below standard |
| P4 — Low | Minor formatting, cosmetic, or labeling issue |

**Status values:** `open` · `in-progress` · `fix-applied` · `resolved` · `wont-fix`

| Status | Meaning |
|--------|---------|
| `open` | Bug confirmed, no fix yet |
| `in-progress` | Fix is being worked on |
| `fix-applied` | Code has been changed — **awaiting manual verification by a human** |
| `resolved` | Fix verified by running the pipeline and confirming the output |
| `wont-fix` | Acknowledged but not being addressed |

---

## Open Bugs

| ID | Date | Severity | Feature | Summary | Run ID | Status |
|----|------|----------|---------|---------|--------|--------|
| BUG-001 | 2026-03-23 | P2 — High | math_worksheet_generation_from_source | compact_source: intro content not stripped; blocks inconsistently sized; whitespace not trimmed from block bottom | 20260323_080238 | fix-applied |

---

## Resolved Bugs

| ID | Date Opened | Date Resolved | Severity | Feature | Summary | Root Cause | Fix Applied To |
|----|-------------|---------------|----------|---------|---------|------------|----------------|
| — | — | — | — | — | — | — | — |

---

## Entry Template

When logging a new bug, add a row to the Open Bugs table AND create a detail block below:

```
### BUG-001

**Date:** YYYY-MM-DD
**Severity:** P1 / P2 / P3 / P4
**Feature:** <feature name, e.g. math_worksheet_generation_from_source>
**Mode:** <compact_source | generate_worksheet | both>
**Run ID:** <run folder name, e.g. 20260323_080156> (or "n/a" if not tied to a run)
**Status:** open

#### Description

<What went wrong. Be specific: what was the input, what was the actual output, what was the expected output.>

#### Steps to Reproduce

1. <Step 1>
2. <Step 2>

#### Impact

<Who is affected and how. e.g. "All compact_source runs on multi-column PDFs produce misaligned crops.">

#### Root Cause (fill in when known)

<Which layer is responsible: spec gap · agent logic · pipeline ordering · code bug · external library>

#### Fix

<What was changed and in which file/spec/agent. Leave blank until resolved.>
```

---

## Bug Detail Records

---

### BUG-001

**Date:** 2026-03-23
**Severity:** P2 — High
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source
**Run ID:** 20260323_080238 (observed across multiple runs)
**Status:** fix-applied — pending verification

#### Description

Three related extraction quality failures, all caused by imprecise block boundary detection:

**Issue 1 — Introduction content not stripped**
Content appearing before Q1 (cover page, instructions, headers, test metadata) is being included in the output. The first question's top boundary is not being correctly set to the Q1 marker's y-coordinate.

- Expected: Output begins exactly at Q1; all pre-question content is stripped.
- Actual: Introduction/cover content appears before Q1 in the compacted PDF.

**Issue 2 — Inconsistent block sizes**
Some question blocks are extracted at a height that is disproportionately smaller or larger compared to neighboring blocks. Blocks that should be visually similar in height vary significantly.

- Expected: Each block height reflects its actual content (stem + diagram if any + answer choices A–D), consistently applied.
- Actual: Some blocks appear too compressed; others too tall, suggesting the bottom boundary detection is unreliable across questions.

**Issue 3 — Excessive whitespace inside extracted blocks (most critical)**
The bottom boundary of each block is being set to the y-coordinate of the *next* question marker, not the y-coordinate of the *last answer choice*. This captures the blank space that exists between questions in the original source and carries that whitespace into the compacted output — directly defeating the purpose of `compact_source`.

- Expected: Each block is cropped to end immediately below the last answer choice (D), with minimal padding only.
- Actual: Each block includes the full trailing whitespace gap that existed between that question and the next in the source. The output retains large inter-block gaps.

#### Steps to Reproduce

1. Run `compact_source` on any multi-question state exam PDF with standard formatting (cover page + numbered questions with A/B/C/D choices)
2. Open the compacted output PDF
3. Observe: intro content before Q1 present; large gaps between question blocks; block heights inconsistent

#### Impact

- Issue 1: Every `compact_source` run on a source with a cover page produces a polluted output.
- Issue 2: Visual inconsistency makes the output look unpolished and harder to read.
- Issue 3: The primary goal of `compact_source` — eliminating whitespace to reduce page count — is not achieved. Page reduction is significantly below what is possible.

#### Root Cause

**Spec gap + code bug — both layers.**

The spec (§3A, Step 2) defines block boundaries using consecutive question marker y-coordinates:
> "Use the y-coordinates of consecutive question markers to define the top and bottom of each block."

This is the root cause of all three issues:
- For Issue 1: the first question's top boundary is not reliably anchored to the Q1 marker — pre-question content is included.
- For Issues 2 & 3: the bottom boundary of each block is the *next question's y-top*, not the *last answer choice's y-bottom*. This is a fundamentally wrong anchor point — it captures inter-question whitespace as part of the block.

The spec in Step 3 says "minimal padding below the last answer choice" but Step 2 provides the wrong y-coordinates for Step 3 to crop against. The two steps are inconsistent.

**The correct bottom boundary for every block is the y-coordinate of the last answer choice (e.g., "D. ..."), not the y-coordinate of the next question marker.**

#### Fix

**`config.py`** — Added `MAX_QUESTION_SPAN_PAGES = 2`. Markers with no detectable answer choices that span more than 2 pages are discarded as non-question content.

**`block_detector.py`** — Full rewrite of boundary detection logic:
- Added `ANSWER_CHOICE_PATTERN` (matches A./B./C./D./F./G./H./J. at line start).
- Added `BLOCK_BOTTOM_PADDING = 6.0` pts below the last answer choice.
- Added `_AnswerChoiceLine` dataclass tracking `y_top` and `y_bottom` of each choice line.
- Updated `_extract_lines_with_coords` to return `(y_top, y_bottom, text)` — the `y_bottom` of each line is now available for tight crop boundaries.
- Renamed `_find_question_markers` → `_find_all_question_markers` (no longer deduplicates eagerly — dedup happens after validation so false-positive early markers don't suppress real questions).
- Added `_find_answer_choices` — scans full document for answer choice lines.
- Added `_find_last_answer_choice_in_range` — returns the last choice within a block's span.
- Added `_compute_prelim_end` and `_make_slices` helpers.
- Replaced `_build_blocks` with a two-pass algorithm: Pass 1 validates markers (filter + dedup); Pass 2 builds blocks with tight bottom boundaries anchored to last answer choice.

**Spec §3A Step 2–3** — Updated to describe answer-choice-based bottom boundary and non-question marker filtering.
