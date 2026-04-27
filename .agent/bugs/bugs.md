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
| BUG-003 | 2026-04-27 | P3 — Medium | math_worksheet_generation_from_source | compact_source: image_heavy blocks cropped prematurely — answer choices or diagram content cut off at block bottom | n/a | open |
| BUG-002 | 2026-04-27 | P2 — High | math_worksheet_generation_from_source | compact_source: image_heavy blocks cropped to full page height — large blank gap below last answer choice in EOG output | n/a | fix-verified |
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

---

### BUG-003

**Date:** 2026-04-27
**Severity:** P3 — Medium
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source
**Run ID:** n/a (observed in gr_3 EOG output — screenshot evidence)
**Status:** open

#### Description

In the compacted gr_3 EOG output, some question blocks are cropped too aggressively at the bottom. Content that belongs to the block — answer choices or the lower portion of a diagram — is visually cut off before the block ends.

**Examples from gr_3 EOG (screenshots provided):**

- A question comparing two fractions shows answer choices A–D but the bottom choice (D) is partially or fully cropped.
- A question with a diagram (kite shapes, circles) shows the question stem and some choices, but the crop cuts into the final answer row.
- A number-pattern question shows the sequence and blank cells, but part of the lower portion of the image content is missing.

- Expected: Each extracted block includes the full question stem, all answer choice lines (A through D), and any associated diagram or figure — with only the blank gap below D and above the footer removed.
- Actual: The block's bottom crop line falls above the last answer choice or diagram content, truncating the question.

#### Steps to Reproduce

1. Run `compact_source` on `gr_3` EOG source PDF
2. Open the compacted output PDF
3. Inspect individual question blocks — some will have the bottom answer choice(s) cut off

#### Impact

Affected questions are rendered incomplete in the student-facing output. Answer choice D (and sometimes C) is missing or partially shown. This is a quality defect — students cannot answer truncated questions.

Scope: affects a subset of `image_heavy` pages in EOG-style inputs where the rendered content extends lower than the footer-detection heuristic estimates. Frequency appears to be a minority of questions in a given file.

#### Root Cause (fill in when known)

Likely a tension between the two-stage trimming pipeline:
1. `_find_image_heavy_y_bottom()` sets `y_bottom` at `footer_top - BLOCK_BOTTOM_PADDING`
2. The pixel-trimmer in `block_extractor.py` then scans up from `y_bottom` and removes blank pixel rows

If the content bottom is very close to (or below) `footer_top - BLOCK_BOTTOM_PADDING` — e.g., a question whose last answer choice sits unusually close to the footer — the crop line may fall inside the answer area rather than just below it. The pixel-trimmer would then cut into live content if blank rows are found between the content mid-section and the crop line.

Needs investigation with coordinate logging on affected pages.

#### Fix

Leave blank — deferred.

---

### BUG-002

**Date:** 2026-04-27
**Severity:** P2 — High
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source
**Run ID:** n/a (reproduced visually — screenshot evidence)
**Status:** fix-verified (2026-04-27, run 20260427_092907)
**Related:** BUG-001 (same root class — imprecise block bottom boundary — but in the `image_heavy` path which BUG-001 never touched)

#### Description

In `image_heavy` (EOG) format, `_detect_image_heavy_blocks()` sets `PageSlice.y_bottom = page_height` for every block — the full page bottom. The actual question content ends at the bottom of the last visible content element (answer choices or embedded diagram). Everything below that (blank space + "N of 40" page footer) is captured in the block image and packed into the output PDF, producing a large dead zone on every question block.

- **Expected:** Each image-heavy block is cropped to end at the bottom of the last visible content element on the page (text answer choices, embedded raster image, or vector drawing), plus `BLOCK_BOTTOM_PADDING`.
- **Actual:** Each block extends to the full page bottom, capturing ~30–40% dead whitespace per block.

**Screenshot evidence (2026-04-27):**

Page 1 of output — question "Which number sentence will 9+6=15 help solve?" with text answer choices A–D. Large blank gap (circled in red) between last answer choice ("D 15+9=__") and "1 of 40" footer occupies approximately 40% of the block height.

Page 2 of output — question "Two sets of circles are shown." with embedded raster images (Set S and Set T circle diagrams) and text fraction answer choices A–D. Also shows a blank gap below the last answer choice before the "2 of 40" footer.

**Key observation from page 2:** Content includes both embedded raster images (circle diagrams rendered as PNG/JPEG in the PDF) and text answer choices. The correct `y_bottom` must be the maximum bottom edge across ALL content types — text blocks, embedded images, and vector drawings. A text-only approach would miss the diagram images; an image-only approach would miss text-only pages. PyMuPDF querying all three content types (`get_text("blocks")`, `get_image_info()`, `get_drawings()`) is the correct and complete solution.

#### Steps to Reproduce

1. Run `compact_source` on an EOG-format exam PDF (image-heavy, one question per page with "N of 40" footer).
2. Open the 1-column compacted output PDF.
3. Observe: large blank gap between the last answer choice and the bottom of each question block.

#### Impact

Every `compact_source` run on an EOG-format source produces output with significant wasted space per block. The page-reduction goal of `compact_source` is not achieved for this format.

#### Root Cause

Code bug in `block_detector.py` — `_detect_image_heavy_blocks()`.
`PageSlice.y_bottom` is hard-coded to `page_heights[page_idx]` (full page height).
No content-aware bottom boundary detection exists for the `image_heavy` path, unlike the `text_rich` path which was fixed by BUG-001.

#### Fix

**`src/utils/image_utils.py`** — New shared module. Provides `count_bottom_blank_rows`, `blank_bottom_fraction`, and `count_bottom_blank_rows_from_pixmap`. Replaces the duplicated `_count_bottom_blank_rows` method that existed only in `block_extractor.py`.

**`src/compact_source/block_extractor.py`** — Removed `_count_bottom_blank_rows` method. Now calls `count_bottom_blank_rows_from_pixmap` from `image_utils`.

**`src/compact_source/block_detector.py`** — Added `import fitz`. Added `_find_image_heavy_y_bottom(fitz_page, page_height)` method that queries all three PyMuPDF content types (`get_text("blocks")`, `get_image_info()`, `get_drawings()`) and returns `max_content_y + BLOCK_BOTTOM_PADDING`. Updated `_detect_image_heavy_blocks()` to open a fitz document alongside pdfplumber and call `_find_image_heavy_y_bottom` per qualifying page instead of hard-coding `y_bottom = page_height`.

**`src/config.py`** — Added `WHITESPACE_WARN_THRESHOLD = 0.15` (overridable via env var).

**`src/compact_source/reporter.py`** — Added `_build_whitespace_section()` method. Updated `generate()` and `_build_compaction_report()` to accept `extracted_blocks` and include the whitespace section in the report. Whitespace failures contribute to `passed = False`.

**`src/orchestrator.py`** — Passes `extracted_blocks=extracted_blocks` to `reporter.generate()`.

**`tests/test_image_utils.py`** — New unit tests TC-WS-01 through TC-WS-06.

**Verification instruction:**

Run the pipeline on any EOG exam PDF:
```powershell
python -m src.orchestrator compact_source --pdf docs/exams/<EOG-file>.pdf
```

Open the `compaction-report.md` in the run output folder (`.agent/evals/runs/math_worksheet_generation_from_source/<run-id>/`).

**What to look for:**
1. **Whitespace Efficiency section** present in the report.
2. **All blocks show < 15% blank** (e.g., "5.2% | ✓ OK") — previously they would have shown ~40%.
3. **Overall verdict: PASS** (whitespace check passes).
4. Visual inspection of `compacted-source.pdf`: no large blank gaps below answer choices.

Run unit tests:
```powershell
python -m pytest tests/test_image_utils.py -v
```
All 7 tests must pass.
