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
| BUG-011 | 2026-05-08 | P2 — High | math_worksheet_generation_from_source | compact_source: test cover/session heading pages included as Q#=0 blocks in output — seen in all 3 grades; cover pages match full-page raster criteria from BUG-008 fix but are not questions | 20260508_223823 | open |
| BUG-010 | 2026-05-08 | P1 — Critical | math_worksheet_generation_from_source | compact_source text_rich: answer choices and diagram content cut off at block bottom — reported across G3 (Q5,6,18,27), G4 (Q13,19,33,34), G5 (Q18,34,35) — two root causes: detector boundary exclusive fence + extractor float-rounding trim | 20260508_203059 | fix-applied | 2026-05-08 | P3 — Medium | math_worksheet_generation_from_source | compact_source NY text_rich: constructed-response questions (Q36–Q44) include large blank work areas — no trimming of "Show your work" / "Answer ___" space | 20260508_112102 | fix-applied |
| BUG-008 | 2026-05-08 | P2 — High | math_worksheet_generation_from_source | compact_source NY text_rich: full-page raster question pages (e.g. page 7 containing Q1/Q2) silently skipped — only text-extractable blocks detected | 20260508_112102 | fix-applied |
| BUG-007 | 2026-05-08 | P3 — Medium | math_worksheet_generation_from_source | compact_source NY text_rich: vector-drawn answer choice diagrams (Q23, Q25) still cropped — y_bottom from text labels only, shapes not fully included | 20260508_110539 | open |
| BUG-006 | 2026-05-08 | P2 — High | math_worksheet_generation_from_source | compact_source NY text_rich: NY_SIDEBAR_NUMBER_PATTERN produces false-positive question blocks from fraction numerals (e.g. "2" in "2/3") and credit-line numbers (e.g. "1" in "worth 1 credit") — wrong question numbers and spurious blocks | 20260508_110539 | open |
| BUG-005 | 2026-05-08 | P2 — High | math_worksheet_generation_from_source | compact_source: NY released-test PDF misclassified as `text_rich` — only 2 false-positive blocks detected instead of 28 real questions | 20260508_094204 | resolved |
| BUG-004 | 2026-04-27 | P4 — Low | math_worksheet_generation_from_source | compact_source: IMP-018 question number label sits slightly above the top of the question block image — label needs a small downward vertical offset to align with the block | n/a | open |
| BUG-003 | 2026-04-27 | P3 — Medium | math_worksheet_generation_from_source | compact_source: image_heavy blocks cropped prematurely — answer choices or diagram content cut off at block bottom | n/a | open |
| BUG-002 | 2026-04-27 | P2 — High | math_worksheet_generation_from_source | compact_source: image_heavy blocks cropped to full page height — large blank gap below last answer choice in EOG output | n/a | fix-verified |
| BUG-001 | 2026-03-23 | P2 — High | math_worksheet_generation_from_source | compact_source: intro content not stripped; blocks inconsistently sized; whitespace not trimmed from block bottom | 20260323_080238 | fix-applied |

---

## Resolved Bugs

| ID | Date Opened | Date Resolved | Severity | Feature | Summary | Root Cause | Fix Applied To |
|----|-------------|---------------|----------|---------|---------|------------|----------------|
| BUG-005 | 2026-05-08 | 2026-05-08 | P2 — High | math_worksheet_generation_from_source | NY PDF misclassified as text_rich \u2014 only 2 false-positive blocks | `_classify_format` used average word count; inflated by instruction pages | `block_detector.py` `_classify_format` \u2192 fraction-based majority vote; NY sidebar number pattern; answer key fence on text_rich path |

---

## Entry Template

When logging a new bug, add a row to the Open Bugs table AND create a detail block below:

```
### BUG-001

**Date:** YYYY-MM-DD
**Severity:** P1 / P2 / P3 / P4
**Classification:** Simple | Moderate | Deep  (see `.agent/governance/bug-fix-workflow.md`)
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

### BUG-011

**Date:** 2026-05-08  
**Severity:** P2 — High  
**Classification:** Moderate  
**Feature:** math_worksheet_generation_from_source  
**Mode:** compact_source_math  
**Run ID (first seen):** 20260508_223823  
**Status:** open

#### Description

Test cover pages and session heading pages are included as Q#=0 blocks in the compacted output across all three NY grade PDFs:

- **Grade 3**: page 6 ("Grade 3, 2023, Mathematics Test, Session 1" cover)
- **Grade 4**: pages 6 and 8 (cover page + session 2 heading page)
- **Grade 5**: pages 6 and 29 (cover page + session 2 heading page)

These pages contain the NY State Testing Program branding, grade/year/session metadata, "Name: ___" line, and the NY state map logo. They are not questions.

**Expected:** No cover or session heading pages in the output. Block count for each grade equals the actual question count only.  
**Actual:** Each run includes 1–2 extra Q#=0 blocks that are cover/heading pages. These appear in the output PDF as full-page images showing the test cover.

#### Root Cause

Layer: Missing filter. `_find_mixed_format_image_blocks()` (added in BUG-008 fix) correctly identifies full-page raster images as question blocks. However, it applies no filter to exclude intro/cover pages. Cover pages pass all current criteria: they are full-page raster images (>85% coverage), low pixel std-dev (solid white/grey branding), and word count ≤5 (logos and short labels extracted as ≤5 words by pdfplumber).

The answer key fence (`_find_answer_key_fence`) already excludes trailing pages. An equivalent leading-content fence is needed to skip pages before the first real question.

#### Steps to Reproduce

1. Run compact_runner on any NY Grade 3/4/5 released test PDF.
2. Inspect the boundary map in run.log — Q#=0 entries on the first content pages are cover/heading pages.
3. Open the output PDF — the first block on page 0 is the test cover image.

#### Impact

Students see the test cover page at the top of their worksheet. The cover takes up significant output page space and provides no study value. Also causes block count to be 1–2 higher than the real question count, breaking QA-DET count checks.

#### Fix

TBD. The Q#-gap approach (filter raster pages with no Q# gap in surrounding text blocks) was attempted on 2026-05-09 but incorrectly excluded real raster question pages (e.g. Grade 4 p6 = Q1/Q2) because they precede the first text-detected block. Reverted to maintain correct block counts. A new approach is needed that distinguishes cover pages from raster question pages without relying on Q# continuity with text markers.

---

### BUG-010

**Date:** 2026-05-08  
**Severity:** P1 — Critical  
**Classification:** Deep  
**Feature:** math_worksheet_generation_from_source  
**Mode:** compact_source_math  
**Run ID:** 20260508_203059  
**Status:** fix-applied

#### Description

Answer choices and diagram content visibly cut off at the bottom of blocks across all three grades:

- Grade 3: Q5, Q6, Q18, Q27
- Grade 4: Q13, Q19, Q33, Q34
- Grade 5: Q18, Q34, Q35

Two separate root causes acting together.

**Expected:** All answer choice rows (A/B/C/D) fully visible in each extracted block.  
**Actual:** Final answer choice row clipped — either the answer letter itself or the fraction/number on its line invisible in output.

#### Root Cause

Two bugs in the `text_rich` detection and extraction path:

**Bug A — Detector boundary fence exclusive (`block_detector.py`):**  
`_find_last_answer_choice_in_range` excluded answer choices whose `y_top` was `>= end_y` (the next question marker's y_top). In NY sidebar format the next question number label and the current question's first answer choice share the same y-coordinate. The `>=` form incorrectly excluded those choice lines from the current block, so `last_choice` was None and `y_bottom` fell back to the preliminary end — set by the next marker's `y_top`, exactly where 'A' started. Large gap: Q13 had 56px of answer choices cut off.

**Bug B — Extractor float-rounding clips one row (`block_extractor.py`):**  
`_crop_slice` computed `trim_pts = blank_rows * 72.0 / DPI`. Since 72/200 = 0.36pts, this is non-integer in PDF points. When fitz re-renders with the float clip boundary it rounds down by one pixel, removing the last content row. Small gap: all other reported questions lost exactly 1px of content.

#### Fix

`block_detector.py` — `_find_last_answer_choice_in_range`: changed `choice.y_top >= end_y` to `choice.y_top > end_y` (strict exclusive). Choices at exactly the boundary are now attributed to the current block.  
`block_extractor.py` — `_crop_slice`: subtract 1 safety row before converting blank_rows to pts (`safe_blank_rows = max(0, blank_rows - 1)`). Ensures float-rounding never removes a content row.

Verification run: `20260508_223823` — QA-EXT-04 regression passes, all P1/P2 QA scenarios PASS.

#### QA Sign-Off

**Fix-applied date:** 2026-05-08  
**Verification run:** 20260508_223823  
**Human verification required:** Open Grade 4 PDF and confirm Q13/Q19/Q33/Q34 answer choices are fully visible. Open Grade 3 and confirm Q5/Q6/Q18/Q27. Open Grade 5 and confirm Q18/Q34/Q35.

---

### BUG-009

**Date:** 2026-05-08
**Severity:** P3 — Medium
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source_math
**Run ID:** 20260508_112102
**Status:** fix-applied

#### Description

Constructed-response questions (NY Grade 4 2023, Q36–Q44) occupy nearly a full output page each. The body of each block consists of a short stem, optional diagram, and then a large blank rectangle reserved for student work ("Show your work", "Explain how you know.", "Answer ___ units"). In a printed drill/study worksheet this blank space wastes paper — students work on separate paper or on-screen.

**Expected:** y_bottom trimmed to just below the first work-area marker + ~2 blank lines.  
**Actual (before fix):** y_bottom = full page height (~686–742 pts); blocks 630+ pts tall.

#### Root Cause

Layer: Missing feature. The text_rich block detection path computed y_bottom as the last answer-choice line, which was correct for MC questions. Constructed-response questions have no A/B/C/D choices, so y_bottom defaulted to the next marker boundary or the page height, including the entire blank work area.

#### Fix

`_trim_constructed_response_blocks()` added to `block_detector.py`. Runs after `_expand_blocks_for_vector_choices`. Scans pdfplumber words for `CR_TRIM_MARKERS` prefixes; sets y_bottom = first match y_top + `CR_BLANK_LINES_KEEP` × `CR_LINE_HEIGHT_PTS`. Constants added to `config.py`. PRD US-08, spec §5.5, and design doc flowchart updated.

---

### BUG-008

**Date:** 2026-05-08
**Severity:** P2 — High
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source_math
**Run ID:** 20260508_112102
**Status:** fix-applied

#### Description

The NY Grade 4 2023 released-test PDF embeds some question pages (e.g. PDF page 7 containing Q1 and Q2) as full-page raster images with zero extractable text. The `text_rich` detection path scans only pdfplumber word positions; pages returning 0 words are invisible to the marker scan and their questions are silently omitted from the output.

**Expected:** Q1 and Q2 (and any other full-page raster question pages) included as blocks.  
**Actual (before fix):** Q1 and Q2 absent from all outputs; boundary map starts at Q5.

#### Root Cause

Layer: Missing feature. The `text_rich` path had no fallback for pages that pdfplumber cannot read as text, even when those pages contain question content.

#### Steps to Reproduce

1. Run `compact_source_math` on `NY_Math_Grade4_2023_Released_Test_Questions.pdf`.
2. Inspect boundary map — Q1 and Q2 absent.
3. `pdfplumber` on page index 6 returns 0 words; PyMuPDF finds a 1224×1584 full-page FlateDecode image.

#### Impact

All questions on raster-only pages silently omitted from output worksheet.

#### Fix

`_find_mixed_format_image_blocks()` added to `block_detector.py`. After text marker scanning, scans every page in [MIN_CONTENT_PAGE, fence) for: (a) 0 pdfplumber words, (b) ≥ `MIXED_FORMAT_IMAGE_MIN_COVERAGE` (85%) single embedded image, (c) pixel std-dev < `MIXED_FORMAT_IMAGE_MAX_PIXEL_STDDEV` (25) — rejects colourful instruction/header pages. Qualifying pages become full-page QuestionBlock entries merged into the final block list. Two new constants added to `block_detector.py`.

---

### BUG-007

**Date:** 2026-05-08
**Severity:** P3 — Medium
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source_math
**Run ID:** 20260508_110539
**Status:** open

#### Description

Questions with **vector-drawn** answer choices (e.g. Q23 “lines of symmetry”, Q25 “angle measurement” in the NY Grade 4 2023 released test) are still cropped before the bottom of the diagram shapes.

Run 20260508_110539 boundary map:
- Q23: y_bottom = 325.7 (page 12 height = 792). Shapes (drawings [0]...[4]) have y1 up to 325.2 — the crop is approximately correct here, but visually the lower two answer choices (B, D) were cut off in the screenshot shared by the teacher.
- Q25: y_bottom = 414.3. Shape y1 up to 414.0 — similar situation.

The `_expand_blocks_for_vector_choices` method was added (2026-05-08) and improved y_bottom materially (was 284 and 345 before expansion), but the teacher confirmed the shapes were still visually cut off at Q23. Further investigation needed.

#### Root Cause (preliminary)

Two possible causes:
1. `VECTOR_EXPANSION_MIN_GAP_PTS = 20.0` threshold may exclude some relevant drawings whose y1 only slightly exceeds the text y_bottom.
2. The large white-fill container rectangles (layout boxes) that frame the answer choices may be the outermost bounding boxes — their y1 values reach further than the actual drawn shapes, but they are now excluded by the white-fill filter. Need to verify whether the outermost container should be included.

#### Steps to Reproduce

1. `python -m src.orchestrator compact_source_math --pdf "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf" --grade 4 --subject Math --yes`
2. Open output PDF. Inspect Q23 and Q25 pages.
3. Compare shape extents with reported y_bottom in `source-boundary-map.md`.

#### Impact

Answer choice diagrams (shapes A/B/C/D) for geometry questions are cut off. Student sees incomplete choices.

#### Fix

To be determined. Likely: lower `VECTOR_EXPANSION_MIN_GAP_PTS`, or reconsider white-fill filter (include outermost layout containers that tightly wrap content).

---

### BUG-006

**Date:** 2026-05-08
**Severity:** P2 — High
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source_math
**Run ID:** 20260508_110539
**Status:** open

#### Description

The `NY_SIDEBAR_NUMBER_PATTERN` (`^\s*(\d{1,2})\s*$`) added for NY released-test support produces **false-positive question markers** from:

1. **Fraction numerals** — questions with fractions (e.g. "2/3") render numerator and denominator on separate lines in pdfplumber. A standalone "2" or "1" line matches the pattern and is detected as Q2 or Q1.
   - Example: page 9 — Q2 block at y=300.2 is a false positive from fraction data inside the line-plot question (Q13). The block labeled Q2 absorbs part of Q13's lower content.

2. **Credit-line numbers** — constructed-response pages start with "This question is worth 1 credit." The standalone "1" matches and creates a Q1 block. 
   - Example: page 21 (Q36) is detected as Q1 instead of Q36; block spans 716 pts (full page) because Q1 has wrong y_top from the credit text.

Visible in run 20260508_110539 boundary map:
- `Q2`: page 9, y_top=300 (should not exist — no Q2 in this partial release)
- `Q1`: page 21, y_top=75, height=716 (should be Q36)

#### Root Cause

`NY_SIDEBAR_NUMBER_PATTERN` is too permissive. It matches ANY 1–2 digit standalone line. Fraction components and credit-score tokens are indistinguishable from question numbers by the current pattern alone.

#### Impact

Spurious blocks consume space in the output PDF. Wrong question numbers are displayed. Blocks labeled Q1/Q2 crowd out or overlap legitimate questions. Detected count appears higher than actual released question count.

#### Fix (proposed)

Add context guards to `_find_all_question_markers` for the NY sidebar path:
1. **Fraction guard**: before accepting a standalone number as a question marker, verify the line immediately above is NOT a fraction denominator (i.e., does not itself consist only of digits). A fraction renders as `"2"` above `"3"` — both standalone; a question number has a multi-word stem above it.
2. **Credit-line guard**: if the stem line above the number contains "credit" (case-insensitive), reject the match.
3. **Sequence guard**: reject a sidebar number if it is lower than the previously accepted question number on the same page (fractions near an earlier question produce out-of-order numbers).

---

### BUG-005

**Date:** 2026-05-08
**Severity:** P2 — High
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source_math
**Run ID:** 20260508_094204
**Status:** resolved
**Resolved:** 2026-05-08 — verified run 20260508_113051 (27 blocks, 3 pages)

#### Description

`NY_Math_Grade4_2023_Released_Test_Questions.pdf` (32 pages, 28 questions) was processed by `compact_source_math`. The pipeline produced a 1-page output containing only 2 blocks. The source-boundary-map showed `Q2023` (page 31) and `Q44` (page 31) — clearly false positives, not real question blocks.

**Expected:** ~28 question blocks detected, output spanning multiple pages.  
**Actual:** 2 false-positive blocks; output = 1 page.

#### Root Cause

**Layer:** Code — `_classify_format` in `block_detector.py`.

The classifier sampled the first 10 pages (after `MIN_CONTENT_PAGE`) and computed an **average** word count. The NY 2023 PDF has 2–3 word-rich instruction/cover pages at the start; these inflated the average above `IMAGE_HEAVY_AVG_WORDS_THRESHOLD` (10), causing the PDF to be classified as `text_rich`. In the `text_rich` path:
- `QUESTION_LINE_PATTERN` = `r"^\s*(\d+)(?:[\.)\]\s|\s+[A-Z])"` matched `"2023 Released"` ("2023" + space + uppercase "R") on page 31
- And matched `"44"` from a page-footer or answer-key entry on the same page
- No actual question-numbered lines (e.g., `"1."`, `"2."`) were found because the real questions are embedded as raster images with no extractable text

The correct classification was `image_heavy` (one visual question per page), which would have triggered the image-heavy path and produced 28 blocks.

#### Steps to Reproduce

1. `python -m src.orchestrator compact_source_math --pdf "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf" --grade 4 --subject Math`
2. Observe `2 question blocks detected` in console output
3. Open `.agent/evals/runs/math_worksheet_generation_from_source/20260508_094204/NY_Math_Grade4_2023_Released_Test_Questions_source-boundary-map.md` — shows Q2023 and Q44 on page 31

#### Impact

All NY released-test PDFs (and any other hybrid-format exam PDF with word-rich instruction pages followed by image-based question pages) are silently misclassified. The output PDF is useless.

#### Fix

**`block_detector.py`:** Changed `_classify_format` from average-based to **fraction-based majority vote**. Added constant `IMAGE_HEAVY_MIN_FRACTION = 0.5`. Now: count how many sampled pages have `<= IMAGE_HEAVY_PAGE_MAX_WORDS` words; if fraction `>= 0.5` → `image_heavy`. This is robust to instruction pages inflating the count.

**`orchestrator.py`:** Added **human question-count gate** after Stage 2. Shows detected count + low-count warning; operator confirms `[Y/n]` before extraction. Added `auto_confirm: bool = False` param and `--yes`/`-y` CLI flag.

**`scripts/compact_runner.py`:** Fixed mode name `compact_source` → `compact_source_math`. Added `--yes` to subprocess call.

#### Verification

```bash
python -m src.orchestrator compact_source_math \
  --pdf "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf" \
  --grade 4 --subject Math
```

Expected after fix:
- Human gate appears with `[Y/n]` prompt
- Detected count is ~28 blocks (not 2)
- Output PDF spans multiple pages
- `source-boundary-map.md` shows 28 question blocks with sequential `Q1`–`Q28` numbering

Only the human who ran this test may advance status from `fix-applied` → `resolved`.

---

### BUG-004

**Date:** 2026-04-27
**Severity:** P4 — Low
**Feature:** math_worksheet_generation_from_source
**Mode:** compact_source
**Run ID:** n/a
**Status:** open
**Related:** IMP-018 (question number overlay feature)

#### Description

The question number label added by IMP-018 is positioned slightly above the top edge of the question block image rather than being visually flush with (or just inside) the block content. The label appears to float above the block rather than sitting at the same vertical level as the block's top.

- **Expected:** The question number label (e.g., "1.") is vertically aligned with the top of the question block so it reads as part of the block — not above it.
- **Actual:** The label's vertical position is a few points too high, causing it to appear detached from the block image.

#### Steps to Reproduce

1. Run `compact_source` on any EOG-format exam PDF with `--question-start` or default question numbering active.
2. Open the compacted output PDF.
3. Inspect any question block — the number label sits slightly above the top edge of the block image.

#### Impact

Cosmetic only. The question number is legible and correct; it is just misaligned by a small vertical offset. Does not affect student ability to use the output.

#### Root Cause (fill in when known)

Likely the `y` coordinate passed to `page.insert_text` places the text baseline at the block's `y_top` rather than a few points below it. A small positive offset (e.g., `QUESTION_LABEL_FONT_SIZE` pts or a fixed constant) should bring the label into alignment.

#### Fix

Leave blank — deferred.

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
