# compact_source-spec.md

**Feature:** `compact_source`
**Version:** v2
**Status:** Active
**Date:** 2026-05-10

---

## 1. Overview

`compact_source` takes a source math exam PDF and produces a print-ready PDF that:
- Contains all question-content blocks from the source, in original order
- Preserves all rendered content pixel-for-pixel (no re-rendering, no text extraction)
- Packs blocks more densely than the source (fewer output pages)
- Supports 1-column and 2-column layout

This spec is exclusively for `compact_source`. For `generate_worksheet`, see the v6 monolithic spec.

---

## 2. Pipeline Stages

```
Input PDF
    │
    ▼
[Stage 1] Format Detection      → format: "image_heavy" | "text_rich"
    │
    ▼
[Stage 2] Block Detection       → list of (start_page, end_page) block spans
    │
    ▼
[Stage 3] Block Extraction      → list of raster images, one per block
    │
    ▼
[Stage 4] Page Packing          → output PDF with blocks arranged in columns
    │
    ▼
[Stage 5] Reporting             → compaction-report.md + source-boundary-map.md
    │
    ▼
Output PDF
```

Each stage is independently testable. Stage failure MUST raise a typed exception (see §10).

---

## 3. Input Contract

| Parameter | Type | Required | Default | Constraints |
|-----------|------|----------|---------|-------------|
| `source_pdf` | file path or folder path | Yes | — | Must be readable, not encrypted, ≥ 1 page |
| `columns` | int | No | 1 | Must be 1 or 2 |
| `scale_factor` | float (%) | No | 100 | Must be > 0 and ≤ 200 |
| `max_pages` | int | No | None | Must be > 0 |
| `grade` | int | No | 0 | Label only; no effect on pipeline |
| `subject` | str | No | `""` | Label only; no effect on pipeline |
| `question_list` | str | No | `"ALL"` | `"ALL"`, `"1-10"`, or `"1,3,5"` |

**Validation rules (enforced before pipeline starts):**
- `source_pdf` must be a readable file or directory
- If file: must end in `.pdf`; must be openable with pdfplumber without exception; must not be password-protected
- `columns` must be 1 or 2; any other value raises `ValidationError`
- `scale_factor` must be a positive float; 0 or negative raises `ValidationError`
- If folder: all `.pdf` files in the folder are processed; non-PDF files are silently skipped

---

## 4. Format Detection Contract

### 4.1 Definition

| Format | Description | Typical Source |
|--------|-------------|---------------|
| `image_heavy` | Exam where content pages contain ≤ 5 words (question content is a raster image, not selectable text) | EOG (NC), SOL (VA), MCAP (MD) |
| `text_rich` | Exam where content pages contain > 10 words on average (questions are rendered as text and graphics; text is selectable) | STAAR (TX), PARCC |

### 4.2 Classification Algorithm

1. Open the PDF with pdfplumber
2. Sample the first `IMAGE_HEAVY_SAMPLE_PAGES` (default: 10) pages starting at `MIN_CONTENT_PAGE`
3. For each sampled page, count words using `pdfplumber` `page.extract_words()`
4. Count how many sampled pages have `word_count <= IMAGE_HEAVY_PAGE_MAX_WORDS` → call this `image_heavy_page_count`
5. Compute `fraction = image_heavy_page_count / pages_sampled`
6. If `fraction >= IMAGE_HEAVY_MIN_FRACTION` (default: 0.5) → classify as `"image_heavy"`
7. Otherwise → classify as `"text_rich"`

**Rationale for fraction-based approach:** An average-based threshold (prior approach) is fragile for PDFs that mix word-rich cover/instruction pages with image-heavy question pages. A majority vote counts how many pages individually look like image-heavy pages, making it robust to a small number of instruction pages at the start of the document.

**Example:** An NY released test PDF with 3 instruction pages (50+ words each) and 7 image-based question pages (≤5 words each) in the first 10 sampled pages yields `fraction = 0.70 ≥ 0.5` → correctly classified as `"image_heavy"`.

**Testable claim:** Given a valid EOG 2014 grade 3 PDF, `_classify_format()` MUST return `"image_heavy"`. Given a valid STAAR 2022 grade 3 PDF, MUST return `"text_rich"`. Given an NY released-test PDF with ≥50% image-based question pages in the sample window, MUST return `"image_heavy"`.

### 4.3 Constants

| Constant | Default | Meaning |
|----------|---------|---------|
| `IMAGE_HEAVY_SAMPLE_PAGES` | 10 | Number of pages to sample for classification (starting at `MIN_CONTENT_PAGE`) |
| `IMAGE_HEAVY_MIN_FRACTION` | 0.5 | Fraction of sampled pages that must qualify as image-heavy for the PDF to be classified `image_heavy` |
| `IMAGE_HEAVY_AVG_WORDS_THRESHOLD` | 10 | Retained constant (no longer used by classifier; kept for backward compatibility) |
| `IMAGE_HEAVY_PAGE_MAX_WORDS` | 5 | Max words on a page to count that page as an image-heavy page during classification |

### 4.4 Format Detection Failure Modes

| Situation | Behavior |
|-----------|----------|
| PDF has < 3 non-blank pages | Classify as `"image_heavy"` (conservative) |
| pdfplumber raises exception during sampling | Raise `DetectionError` with message identifying the page and exception |
| All sampled pages have 0 words | Classify as `"image_heavy"` |
| Sampled pages include word-rich cover/instruction pages followed by image-heavy question pages | Fraction-based vote correctly classifies as `"image_heavy"` when ≥50% of sampled pages are image-heavy |

---

## 4.5 Human Question-Count Gate

After block detection completes and before block extraction begins, the pipeline MUST pause for operator confirmation when running in interactive mode.

**Purpose:** Block detection can mis-classify hybrid-format PDFs or fail to match a non-standard question numbering pattern. A human gate prevents extraction of a wrong or near-empty block set from proceeding silently to produce a useless output PDF.

**Contract:**

| Condition | Behavior |
|-----------|----------|
| `auto_confirm=False` AND `sys.stdin.isatty()` is `True` | Print detected count, source page count, format, and low-count warning (if applicable); prompt operator `[Y/n]`; abort on `n`/`no` |
| `auto_confirm=True` | Skip gate entirely; pipeline continues without prompting |
| `sys.stdin.isatty()` is `False` (pipe/redirect) | Skip gate silently (non-interactive context) |
| Detected count < 3 OR detected count / source pages < 0.5 | Print a `WARNING: LOW COUNT` warning regardless of `auto_confirm` |

**CLI:**
- `--yes` / `-y` sets `auto_confirm=True` for a run
- Default: `auto_confirm=False` (gate is active)

**Testable claims:**
- When `auto_confirm=False` and stdin is a TTY, the pipeline MUST NOT proceed to extraction without reading operator input
- When `auto_confirm=True`, no input prompt is issued and the pipeline proceeds immediately
- When detected count < 3, a `WARNING` message MUST appear in the console log regardless of `auto_confirm`

---

## 5. Block Detection Contract

### 5.1 image_heavy Path

1. Find the answer key fence (§5.3)
2. Open the source PDF with PyMuPDF (`fitz.open`) in parallel with the pdfplumber pass — one document handle, iterated alongside the word-count loop
3. Iterate pages 0 through `fence_page - 1`
4. For each page, extract word count from pdfplumber
5. Include page as a block if and only if: `0 < word_count <= IMAGE_HEAVY_PAGE_MAX_WORDS`
6. Each included page becomes exactly one `QuestionBlock` with a single `PageSlice` where:
   - `y_top = 0.0`
   - `y_bottom` = result of `_find_image_heavy_y_bottom(fitz_page, page_height, pdfplumber_words)` (see §5.4)

**Testable claims:**
- Blank pages (0 words) MUST NOT be included
- Section-break notice pages (e.g., "The first section of the test ends here.", 8 words) MUST NOT be included
- Answer key pages MUST NOT be included
- Given EOG 2014 gr_3: block count MUST equal 40
- Given EOG 2014 gr_4: block count MUST equal 50
- Given EOG 2014 gr_5: block count MUST equal 50
- Given any EOG question page, the **extracted** block `total_height_pts` MUST be < `IMAGE_HEAVY_HEIGHT_WARN_FRACTION` (95%) × page height

### 5.2 text_rich Path

1. Open PDF with pdfplumber
2. For each page, extract words and their bounding boxes
3. Find lines that begin with a question-number pattern (e.g., `^\d+\.?\s` or `^Q\d+`)
4. Each question-number line starts a new block
5. A block ends at the line before the next question number, or at the end of the page, or at the answer key fence
6. Claude vision fallback: if fewer than `MIN_QUESTIONS_FALLBACK` (default: 3) blocks are found by text analysis, send page renders to Claude for boundary detection

**Testable claims:**
- Given STAAR 2022 gr_3: block count MUST equal 32
- Given STAAR 2022 gr_4: block count MUST equal 35
- Given STAAR 2022 gr_5: block count MUST equal 36
- No block may span more than `DEFAULT_MAX_BLOCK_PAGES` (default: 2) pages

### 5.4 image_heavy Content-Bottom Helper — `_find_image_heavy_y_bottom`

Returns the `y_bottom` for a single `image_heavy` page using a two-strategy approach.

**Primary strategy — footer exclusion (preferred):**

EOG question pages embed the question as a full-page raster image, so `get_image_info()` always returns a bbox spanning the entire page. The correct anchor is the pdfplumber **footer word position**.

1. Collect all words in the bottom `IMAGE_HEAVY_FOOTER_ZONE_FRACTION` (15%) of the page from `pdfplumber_words`
2. Join their text; if it matches `IMAGE_HEAVY_FOOTER_PATTERN` (`^\d+ of \d+$`) → confirmed footer
3. Return `max(0, footer_top - BLOCK_BOTTOM_PADDING)`

**Fallback strategy — PyMuPDF content bboxes:**

Used when no footer match is found (defensive guard).

| PyMuPDF Query | Content Type Covered |
|---|---|
| `fitz_page.get_text("blocks")` (footer-filtered) | Text blocks, excluding footer zone |
| `fitz_page.get_image_info()` | Embedded raster images |
| `fitz_page.get_drawings()` | Vector drawings |

1. Take `max_y` across all three content types
2. If `max_y > 0`: return `min(max_y + BLOCK_BOTTOM_PADDING, page_height)`
3. Else: return `page_height`

**Testable claims:**
- Footer-containing page: `y_bottom` = `footer_top - BLOCK_BOTTOM_PADDING`
- `y_bottom` < `page_height` when content occupies < 100% of page
- Blank page (no content): `y_bottom` = `page_height` (safe fallback)
- `y_bottom` never exceeds `page_height`

---

### 5.3 Answer Key Fence

The answer key fence is the index of the first page (0-based) that should NOT be included in block detection output.

**Detection algorithm:**
1. Iterate pages from the end of the PDF backward
2. For each page, extract text and check if it contains both the word `"answer"` and the word `"key"` (case-insensitive)
3. The first such page (scanning backward) becomes the candidate fence
4. The fence is the minimum page index that contains an answer key indicator

**If no fence is found:** `fence_page = total_page_count` (include all pages)

**Testable claim:** Given an EOG PDF with an answer key at page 47 (0-based), `_find_answer_key_fence()` MUST return 47. Given a STAAR PDF with no answer key, MUST return `total_page_count`.

---

## 5.5 Constructed-Response Block Trimming

### 5.5.1 Motivation

Some exam formats (notably NY released tests) contain constructed-response questions that occupy a full output page. The body of such a block consists of a short stem, optional diagram(s), followed by instructions ("Show your work", "Explain how you know.", "Answer ___  units") and then a large blank rectangle reserved for student work. In a printed drill worksheet this blank space is wasted; trimming it to 1–2 blank lines reclaims the space.

### 5.5.2 Constructed-Response Block Identification

A `text_rich` block is a candidate for trimming when pdfplumber text extraction for that block span contains at least one line whose lowercase text **starts with or equals** any string in `CR_TRIM_MARKERS`:

```
CR_TRIM_MARKERS = [
    "answer",
    "show your work",
    "explain",
    "describe",
    "justify",
    "write your answer",
]
```

Matching is case-insensitive and applied to the stripped line text. A line matches if `line.lower().startswith(marker)`.

**Note:** The NY "This question is worth N credit(s)." line is a helpful contextual indicator but is NOT itself a trim marker — it appears at the top of the block (before the stem) and must not be used as a crop boundary.

### 5.5.3 Trim Algorithm — `_trim_constructed_response_blocks()`

Called after `_expand_blocks_for_vector_choices()` and before the final block list is returned from `detect()`.

For each block `b` in the detected block list:

1. Iterate over all pdfplumber words in `b`'s page span; collect lines from `b.y_top` or the block's stem start downward.
2. Scan lines in order. Find the **first** line whose text matches any `CR_TRIM_MARKERS` entry (case-insensitive prefix match).
3. If no match: skip this block (no trimming applied).
4. If match found at line with bounding box top `trim_y`:
   - `new_y_bottom = trim_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS`
   - `new_y_bottom = min(new_y_bottom, b.y_bottom)` — never extend below existing boundary
   - `new_y_bottom = max(new_y_bottom, trim_y + CR_LINE_HEIGHT_PTS)` — always keep at least 1 line of padding
   - Apply: `b.y_bottom = new_y_bottom`

For multi-page blocks (where the trim marker may be on a page following the stem page): the same logic applies using the slice coordinates of the last page in the block. The last page's `y_bottom` is updated; preceding pages' `y_bottom` values are unchanged.

### 5.5.4 Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `CR_BLANK_LINES_KEEP` | 2 | Number of blank line heights to preserve below the first trim marker |
| `CR_LINE_HEIGHT_PTS` | 12.0 | Assumed single line height in points used for blank-line padding computation |
| `CR_TRIM_MARKERS` | see §5.5.2 | List of lowercase prefix strings that identify the crop boundary |

### 5.5.5 Applicability

| Format | Trimming Active? | Rationale |
|--------|-----------------|-----------|
| `text_rich` | ✓ Yes | Constructed-response markers are detectable from pdfplumber text |
| `image_heavy` | ✗ No | Block text is not extractable (questions are embedded rasters); trimming cannot be applied safely |

### 5.5.6 Testable Claims

- Given a NY released-test `text_rich` block containing "Answer ___ units", `y_bottom` MUST be ≤ `trim_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS`
- Given a block with no `CR_TRIM_MARKERS` present, `y_bottom` MUST be unchanged after `_trim_constructed_response_blocks()`
- `new_y_bottom` MUST NOT exceed the pre-trim `y_bottom`
- `new_y_bottom` MUST be at least `trim_y + CR_LINE_HEIGHT_PTS` (minimum 1-line pad)
- For `image_heavy` blocks, `_trim_constructed_response_blocks()` MUST NOT modify any block boundary

### 5.5.7 Edge Cases

| ID | Situation | Expected Behavior |
|----|-----------|-------------------|
| EC-CR-01 | Trim marker is the very first line in the block (malformed block) | Trim to `trim_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS`; accept the result (stem may have been mis-detected) |
| EC-CR-02 | Multiple trim markers on the same block page | Use the **first** (topmost) match as the crop boundary |
| EC-CR-03 | "Answer" appears in the stem text (e.g., "What answer best explains...") | The line will match; this is a known acceptable false positive — the next-line heuristic is not required for v1 |
| EC-CR-04 | Block spans two pages; trim marker is on the second page | Update only the last-page `y_bottom`; leave the first page slice unchanged |
| EC-CR-05 | `CR_BLANK_LINES_KEEP = 0` | Keep exactly 0 lines below the trim marker (crop immediately at `trim_y`) |

---

## 6. Block Extraction Contract

1. For each detected block (start_page, end_page):
   a. Render each page in the span to a raster image at `PDF_RENDER_DPI` (default: 96)
   b. Crop the rendered image to the block's bounding box
   c. Store the result as a PIL Image in memory
2. The block image MUST be pixel-faithful — no scaling, no color conversion, no re-encoding at this stage
3. Block images are stored ordered by source page/position

**Testable claim:** The pixel dimensions of an extracted block image are proportional to `PDF_RENDER_DPI * block_height_inches × PDF_RENDER_DPI * block_width_inches`.

---

## 7. Page Packing Contract

### 7.1 Output Page Dimensions

Output pages use the same dimensions as A4 or the source page dimensions, whichever produces the more compact output. Default: match source page width.

### 7.2 Scale Factor

- `scale_factor = 100` means each block image is scaled to exactly fill the column width
- `scale_factor = 80` means each block is scaled to 80% of the column width
- Column width = (page content width - margins - inter-column gap) / columns

### 7.3 max_pages

- If `max_pages` is specified, the system computes the minimum scale needed to fit all blocks within `max_pages` pages
- If both `scale_factor` and `max_pages` are given, the more restrictive (smaller resulting image size) wins

### 7.4 2-Column Layout

- Each page is divided into 2 equal columns with a 10pt inter-column gap
- Blocks are filled left-column first, then right-column
- A block that does not fit in the remaining space of a column causes a column advance; if both columns on a page are full, a new page is started
- A block is never split across columns or pages

### 7.5 Output PDF Compression

- Output PDF MUST be saved with `deflate=True` and `garbage=4`
- Output file MUST be ≤ 5 MB for a standard 30–50 question exam at 96 DPI

### 7.6 Question Number Overlay

**Motivation:** For `image_heavy` (EOG-style) PDFs the question number is embedded in the page footer as text ("N of M"). The footer is removed as part of the BUG-002 fix. The compacted output therefore contains no question numbers — a student-facing quality defect.

**Contract:**

- When `add_question_numbers=True`, `PdfPacker._render()` MUST write a text label (e.g., "1.") at the top-left corner of each block image in the output PDF.
- The label MUST have a white-filled background rectangle so it is legible over any image content.
- The label for block with `question_number=N` is `"{question_start + N - 1}."` where `question_start` defaults to 1.
- `question_start` MUST be respected: if `question_start=5` and `question_number=1`, the label MUST be `"5."` and NOT `"1."`.
- When `add_question_numbers=False`, NO label text is written. The output PDF MUST contain no injected question number text.
- `PdfPacker()` constructed with no arguments MUST default to `add_question_numbers=False`. Auto-enabling is the orchestrator's responsibility.
- The orchestrator MUST auto-enable (`add_question_numbers=True`) when `detection_result.is_image_heavy=True` and the caller has not explicitly passed `add_question_numbers`.
- The orchestrator MUST NOT auto-enable for `text_rich` PDFs (question numbers are already embedded in the block images).
- Label text MUST be extractable by a PDF text reader (i.e., written as PDF text, not as an image).
- Font size is controlled by `QUESTION_LABEL_FONT_SIZE` (default 10 pts).
- CLI flags: `--no-question-numbers` suppresses labeling; `--question-start N` sets the start offset.

### 7.7 Output Naming

Output file name MUST follow the pattern:
```
{source_stem}_Compacted_{N}col_{run_id}.pdf
```
where:
- `source_stem` = source PDF filename without extension
- `N` = number of columns (1 or 2)
- `run_id` = timestamp-based unique run identifier (format: `YYYYMMDD_HHMMSS`)

---

## 8. Reporting Contract

### 8.1 Compaction Report (`{stem}_compaction-report.md`)

Must contain:
- Source filename and path
- Run ID and timestamp
- Format detected (`image_heavy` or `text_rich`)
- Block count
- Input page count → output page count
- Input file size → output file size, delta, percentage
- List of all blocks (start page, end page, question number if available)
- **Block Height Efficiency section** (image_heavy format only, when extracted blocks are provided):
  - Per-block row: `Q# | block_height/page_height% | ✓ OK / ⚠ OVERSIZED`
  - Summary: `N of total blocks exceed height threshold`
  - Threshold: `IMAGE_HEAVY_HEIGHT_WARN_FRACTION` (default 95%)
  - If any block flagged: overall verdict is FAIL

### 8.2 Source Boundary Map (`{stem}_source-boundary-map.md`)

Must contain:
- One row per detected block
- Columns: block index, start page, end page, word count (for image_heavy), question number (for text_rich)

### 8.3 File Size Row Format

```
Input:  <input_size>  →  Output: <output_size>  (<delta> saved, <pct>% reduction)
```
If output is larger:
```
Input:  <input_size>  →  Output: <output_size>  (<delta> larger, +<pct>%)
```

---

## 9. Output Artifacts

All output artifacts for a run are written to:
```
.agent/evals/runs/math_worksheet_generation_from_source/{run_id}/bin/
```

| Artifact | Description |
|----------|-------------|
| `{stem}_Compacted_{N}col_{run_id}.pdf` | Compacted output PDF |
| `{stem}_compaction-report.md` | Human-readable compaction summary |
| `{stem}_source-boundary-map.md` | Per-block boundary table |

For folder (batch) runs, all PDFs in the batch share the same `run_id` and write to the same `bin/` folder.

---

## 10. Exception Taxonomy

| Exception | Stage | Trigger |
|-----------|-------|---------|
| `ValidationError` | Pre-pipeline | Unreadable file, wrong type, bad parameter |
| `DetectionError` | Stage 1–2 | Cannot classify format; block detection produces 0 blocks |
| `ExtractionError` | Stage 3 | Page render fails; block image is empty |
| `PackingError` | Stage 4 | Output PDF cannot be written; disk full |

All exceptions must:
- Carry a human-readable message and the offending input (file path, page index, parameter name)
- Propagate to the CLI layer, which prints the message and exits with code 1
- Never be silently swallowed

---

## 11. Edge Case Catalogue

| ID | Situation | Expected Behavior |
|----|-----------|-------------------|
| EC-01 | PDF is password-protected | `ValidationError` before pipeline starts |
| EC-02 | PDF has 0 pages | `ValidationError` before pipeline starts |
| EC-03 | PDF has no detectable blocks (e.g., only a cover page) | `DetectionError`; report states 0 blocks; exit code 1 |
| EC-04 | Answer key is the first page (malformed PDF) | Fence = 0; 0 blocks detected; `DetectionError` |
| EC-05 | Block image renders as pure white (blank raster) | Block is included (may be intentional blank question); no special handling |
| EC-06 | Source PDF has mixed formats (some pages image-heavy, some text-rich) | Fraction-based majority vote classifies as `image_heavy` when ≥50% of sampled pages have ≤5 words; one format is chosen for the whole document |
| EC-13 | Block detection produces a suspiciously low count (< 3 blocks, or < 0.5 blocks per source page) | Human gate displays a `WARNING: LOW COUNT` message; operator must confirm or abort before extraction proceeds |
| EC-07 | `--pdf` folder contains no `.pdf` files | `ValidationError` with message "No PDF files found in folder" |
| EC-08 | Single block is taller than one full output page at scale 100 | Block is placed on its own page, scaled down to fit page height instead of column width |
| EC-09 | `scale_factor=0` | `ValidationError` before pipeline starts |
| EC-10 | Claude API unavailable (network error) | Retry with exponential backoff (Phase 3); after max retries, raise `DetectionError` |
| EC-11 | `max_pages=1` but blocks don't fit at minimum viable scale | Pack as many as possible on 1 page; emit warning in report; do not truncate blocks silently |
| EC-12 | PDF with only blank pages | Classify as `image_heavy`; detect 0 blocks; `DetectionError` |

---

## 12. Configuration Reference

All constants are defined in `src/config.py` and can be overridden via environment variables (`.env`).

| Constant | Default | Env Var | Description |
|----------|---------|---------|-------------|
| `PDF_RENDER_DPI` | 96 | `PDF_RENDER_DPI` | Raster resolution for page renders |
| `BLOCK_SCALE_FACTOR` | 100 | — | Default scale factor (%) |
| `DEFAULT_MAX_BLOCK_PAGES` | 2 | — | Max pages a single text_rich block can span |
| `IMAGE_HEAVY_SAMPLE_PAGES` | 10 | — | Pages sampled for format classification |
| `IMAGE_HEAVY_AVG_WORDS_THRESHOLD` | 10 | — | Avg words/page threshold for image_heavy classification |
| `IMAGE_HEAVY_PAGE_MAX_WORDS` | 5 | — | Max words on a page to qualify as an image_heavy block |
| `COMPARATOR_RENDER_DPI` | (follows PDF_RENDER_DPI) | — | DPI used for visual comparison renders |
| `IMAGE_HEAVY_FOOTER_ZONE_FRACTION` | 0.15 | — | Bottom fraction of page height treated as footer zone |
| `IMAGE_HEAVY_FOOTER_PATTERN` | `^\d+ of \d+$` | — | Regex matching page-number footer ("N of M") |
| `IMAGE_HEAVY_HEIGHT_WARN_FRACTION` | 0.95 | `IMAGE_HEAVY_HEIGHT_WARN_FRACTION` | Max extracted block height / page height before flagging in report |
| `QUESTION_LABEL_FONT_SIZE` | 10.0 | `QUESTION_LABEL_FONT_SIZE` | Font size (pts) for the question number text label overlaid on each image_heavy block |
| `WHITESPACE_WARN_THRESHOLD` | 0.15 | `WHITESPACE_WARN_THRESHOLD` | Retained for image_utils pixel-level checks; no longer used by reporter |
| `CR_BLANK_LINES_KEEP` | 2 | — | Number of blank line heights to preserve below the first constructed-response trim marker |
| `CR_LINE_HEIGHT_PTS` | 12.0 | — | Assumed line height in points used for blank-line padding in constructed-response trimming |
| `COMPARATOR_SIMILARITY_THRESHOLD` | 0.97 | — | Minimum page-level structural similarity score (SSIM) required for a page to be considered PASS |

---

## 13. Testability Checklist

Every clause in this spec that makes a claim about behavior MUST map to a test case in the test suite (Phase 4, IMP-002).

| Clause | Test Case ID (to be assigned in Phase 4) |
|--------|------------------------------------------|
| `_classify_format()` returns `"image_heavy"` for EOG gr_3 | TC-FD-01 |
| `_classify_format()` returns `"text_rich"` for STAAR gr_3 | TC-FD-02 |
| EOG gr_3 yields 40 blocks | TC-BD-01 |
| EOG gr_4 yields 50 blocks | TC-BD-02 |
| EOG gr_5 yields 50 blocks | TC-BD-03 |
| STAAR gr_3 yields 32 blocks | TC-BD-04 |
| STAAR gr_4 yields 35 blocks | TC-BD-05 |
| STAAR gr_5 yields 36 blocks | TC-BD-06 |
| Blank pages excluded from image_heavy blocks | TC-BD-07 |
| Section-break pages excluded (≤ 5 words) | TC-BD-08 |
| Answer key fence excludes answer key pages | TC-BD-09 |
| EOG extracted block height < 95% of page height (BUG-002 regression) | TC-BD-10 |
| image_heavy y_bottom < page_height when content at 60% of page (footer-detection strategy) | TC-BD-11 |
| BUG-002 regression: hardcoded page_height fraction ≥ threshold; fixed y_bottom fraction < threshold | TC-BD-11 |
| image_heavy y_bottom uses max across text + drawings (lowest element wins) | TC-BD-12 |
| image_heavy y_bottom: blank page → page_height fallback | TC-BD-13 |
| image_heavy y_bottom never exceeds page_height | TC-BD-14 |
| `ValidationError` on encrypted PDF | TC-VAL-01 |
| `ValidationError` on empty folder | TC-VAL-02 |
| `ValidationError` on `scale_factor=0` | TC-VAL-03 |
| `ValidationError` on `columns=3` | TC-VAL-04 |
| Output named `{stem}_Compacted_{N}col_{run_id}.pdf` | TC-OUT-01 |
| Output ≤ 5 MB for 50-question exam at 96 DPI | TC-OUT-02 |
| File size row present in compaction report | TC-RPT-01 |
| `add_question_numbers=True` → label "1." present in PDF text (TC-PP-01) | TC-PP-01 |
| `add_question_numbers=False` → no label text in PDF (TC-PP-02) | TC-PP-02 |
| `question_start=5` + `question_number=1` → label is "5.", not "1." (TC-PP-03) | TC-PP-03 |
| multi-block pack → each block labeled with its own question_number (TC-PP-04) | TC-PP-04 |
| `PdfPacker()` default constructor → `add_question_numbers=False`, no labels written (TC-PP-05) | TC-PP-05 |
| NY text_rich block with "Answer" line → `y_bottom` trimmed to `trim_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS` | TC-CR-01 |
| Block with no trim markers → `y_bottom` unchanged | TC-CR-02 |
| `new_y_bottom` never exceeds pre-trim `y_bottom` | TC-CR-03 |
| `new_y_bottom` ≥ `trim_y + CR_LINE_HEIGHT_PTS` (minimum 1-line pad) | TC-CR-04 |
| `image_heavy` blocks: `_trim_constructed_response_blocks()` changes no block boundary | TC-CR-05 |
| `comparator.py` with identical PDFs → all pages PASS, no REVIEW trigger | TC-CMP-01 |
| `comparator.py` with one modified page → page flagged, result = REVIEW | TC-CMP-02 |
| `comparator.py` page count mismatch → extra pages flagged, result = REVIEW | TC-CMP-03 |
| `comparator.py` with `--compare` absent → comparator stage skipped, no verdict emitted | TC-CMP-04 |
| Comparator report section present in compaction report when `--compare` is used | TC-CMP-05 |

---

## 14. Visual Comparison (US-11)

### 14.1 Purpose

The comparator provides a structured signal for operators reviewing output quality against a known-good golden sample. It does **not** replace human judgment — the final call always belongs to the operator.

### 14.2 Invocation

Comparator runs **only** when `--compare --golden <path/to/golden.pdf>` is supplied. If omitted, the stage is fully skipped and no verdict appears in the report.

```
python scripts/compact_runner.py --inputs <input.pdf> --compare --golden <golden.pdf>
```

### 14.3 Algorithm

1. Render every page of the output PDF at `COMPARATOR_RENDER_DPI` DPI.
2. Render the corresponding page of the golden PDF at the same DPI.
3. Compute SSIM (Structural Similarity Index) for each page pair.
4. A page is **PASS** if SSIM ≥ `COMPARATOR_SIMILARITY_THRESHOLD` (default 0.97).
5. A page is **REVIEW** if SSIM < `COMPARATOR_SIMILARITY_THRESHOLD`.

### 14.4 Page Count Mismatch

- If output has **more pages** than the golden: all extra output pages are flagged **REVIEW**.
- If output has **fewer pages** than the golden: all missing golden pages are listed as **ABSENT**.
- Overall verdict is **REVIEW** whenever any REVIEW or ABSENT page exists.

### 14.5 Verdict Logic

| Condition | Verdict |
|-----------|--------|
| All pages PASS, counts match | No verdict block in report (clean run) |
| Any page REVIEW or ABSENT | `VERDICT: REVIEW` block added to compaction report |

**REVIEW is never FAIL.** The pipeline does not abort on a REVIEW verdict. The operator reads the report and decides.

### 14.6 Report Output

When `--compare` is used the compaction report gains a **Visual Comparison** section:

```
## Visual Comparison
Golden: <path>
Pages compared: N

| Page | SSIM | Status |
|------|------|--------|
| 1    | 0.99 | PASS   |
| 3    | 0.82 | REVIEW |

VERDICT: REVIEW
Operator action required: inspect flagged pages before distributing.
```

If all pages pass the section is omitted from the report.

### 14.7 Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `COMPARATOR_SIMILARITY_THRESHOLD` | 0.97 | SSIM score below which a page is flagged REVIEW |
| `COMPARATOR_RENDER_DPI` | follows `PDF_RENDER_DPI` | DPI for page renders during comparison |

### 14.8 Version History

| Version | Date | Change |
|---------|------|--------|
| v2 | 2026-05-10 | §14 added — anchors comparator.py to US-11; closes RISK-03 |
| `comparator.py` with identical PDFs → all pages PASS, no REVIEW trigger | TC-CMP-01 |
| `comparator.py` with one modified page → page flagged, result = REVIEW | TC-CMP-02 |
| `comparator.py` page count mismatch → extra pages flagged, result = REVIEW | TC-CMP-03 |
| `comparator.py` with `--compare` absent → comparator stage skipped, no verdict emitted | TC-CMP-04 |
| Comparator report section present in compaction report when `--compare` is used | TC-CMP-05 |
