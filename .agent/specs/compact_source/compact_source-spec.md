# compact_source-spec.md

**Feature:** `compact_source`
**Version:** v1
**Status:** Active
**Date:** 2026-04-26

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
2. Sample the first `IMAGE_HEAVY_SAMPLE_PAGES` (default: 10) pages that have at least 1 character
3. For each sampled page, count words using `page.extract_text()` split on whitespace
4. Compute `avg_words = sum(word_counts) / len(sampled_pages)`
5. If `avg_words < IMAGE_HEAVY_AVG_WORDS_THRESHOLD` (default: 10) → classify as `"image_heavy"`
6. Otherwise → classify as `"text_rich"`

**Testable claim:** Given a valid EOG 2014 grade 3 PDF, `_classify_format()` MUST return `"image_heavy"`. Given a valid STAAR 2022 grade 3 PDF, MUST return `"text_rich"`.

### 4.3 Constants

| Constant | Default | Meaning |
|----------|---------|---------|
| `IMAGE_HEAVY_SAMPLE_PAGES` | 10 | Number of non-blank pages to sample for classification |
| `IMAGE_HEAVY_AVG_WORDS_THRESHOLD` | 10 | avg words/page below which PDF is classified as image_heavy |
| `IMAGE_HEAVY_PAGE_MAX_WORDS` | 5 | Max words on a content page to be included as a question block |

### 4.4 Format Detection Failure Modes

| Situation | Behavior |
|-----------|----------|
| PDF has < 3 non-blank pages | Classify as `"image_heavy"` (conservative) |
| pdfplumber raises exception during sampling | Raise `DetectionError` with message identifying the page and exception |
| All sampled pages have 0 words | Classify as `"image_heavy"` |

---

## 5. Block Detection Contract

### 5.1 image_heavy Path

1. Find the answer key fence (§5.3)
2. Iterate pages 0 through `fence_page - 1`
3. For each page, extract word count from pdfplumber
4. Include page as a block if and only if: `0 < word_count <= IMAGE_HEAVY_PAGE_MAX_WORDS`
5. Each included page becomes exactly one block spanning that single page

**Testable claims:**
- Blank pages (0 words) MUST NOT be included
- Section-break notice pages (e.g., "The first section of the test ends here.", 8 words) MUST NOT be included
- Answer key pages MUST NOT be included
- Given EOG 2014 gr_3: block count MUST equal 40
- Given EOG 2014 gr_4: block count MUST equal 50
- Given EOG 2014 gr_5: block count MUST equal 50

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

### 7.6 Output Naming

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
| EC-06 | Source PDF has mixed formats (some pages image-heavy, some text-rich) | Classification uses average over sampled pages; one format is chosen for the whole document |
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
| `ValidationError` on encrypted PDF | TC-VAL-01 |
| `ValidationError` on empty folder | TC-VAL-02 |
| `ValidationError` on `scale_factor=0` | TC-VAL-03 |
| `ValidationError` on `columns=3` | TC-VAL-04 |
| Output named `{stem}_Compacted_{N}col_{run_id}.pdf` | TC-OUT-01 |
| Output ≤ 5 MB for 50-question exam at 96 DPI | TC-OUT-02 |
| File size row present in compaction report | TC-RPT-01 |
