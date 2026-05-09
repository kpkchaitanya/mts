# compact_source-prd.md — Product Requirements Document

**Feature:** `compact_source`
**Version:** v1
**Status:** Active
**Date:** 2026-04-26

---

## 1. Problem Statement

Teachers preparing printed math worksheets for students must print multi-page PDFs from official state exam sources (STAAR, EOG, SOL, etc.). These source PDFs are formatted for digital display — wide margins, large whitespace, single questions per page — which wastes paper, inflates printing costs, and makes classroom logistics harder.

Teachers cannot reformat these PDFs manually: math symbols, graphs, geometric figures, and coordinate planes cannot be reliably copy-pasted or re-typed without introducing errors. The only safe approach is to preserve the original rendered content pixel-for-pixel and repack it more densely.

---

## 2. Personas

### Krishna — Classroom Math Teacher
- Teaches grades 3–8 math, assigned 3–5 classes per day
- Prepares printed worksheets for every class session, often pulling questions from state exam banks
- Prints 25–35 copies per worksheet; printing budget is constrained
- Has no technical background; uses the tool via command line with simple arguments
- **Goal:** produce a print-ready PDF that fits in 1–2 pages, preserves all question content, and looks professional enough to hand to students

### Neelima — Curriculum Coordinator
- Reviews worksheets before they go to students; responsible for accuracy and formatting quality
- Needs to verify that no question content was dropped, altered, or garbled in compaction
- Occasionally runs batches (several PDFs at once) before a unit begins
- **Goal:** trust that the output is a lossless visual subset of the source; see a report confirming what was included

### Ravi — Technical Administrator
- Sets up and maintains the tool; handles `.env` config changes
- Needs clean error messages, predictable output locations, and no silent failures
- **Goal:** the tool never crashes silently; every failure produces a clear message and a log

---

## 3. User Stories

### US-01 — Single PDF, one column
> As Krishna, I run `python -m src.orchestrator compact_source --pdf <path>` on a single STAAR exam PDF and receive a compacted 1-column PDF in the output folder, containing all question blocks from the original.

**Acceptance Criteria:**
- Output is a single PDF file named `{stem}_Compacted_1col_{run_id}.pdf`
- Every question detected in the source appears in the output, in source order
- All math symbols, graphs, and figures render identically to the source
- Output file size is ≤ 5 MB for a standard 30–50 question exam

### US-02 — Single PDF, two columns
> As Krishna, I run `--columns 2` and receive a 2-column layout that fits more questions per page.

**Acceptance Criteria:**
- Each question block is scaled to fit column width
- No block is clipped or overflows its column
- 2-column output contains the same questions as the 1-column output

### US-03 — Folder batch run
> As Neelima, I run `--pdf docs/exams/2026-EOGs` and all PDFs in that folder are processed in a single shared run folder.

**Acceptance Criteria:**
- All PDFs in the folder are processed in a single invocation
- All outputs land in one run folder (same run ID for all)
- A per-PDF compaction report is produced for each source file
- The shared run ID is printed to the terminal before processing begins

### US-04 — EOG-style image-heavy exams
> As Krishna, I run the tool on an EOG-style PDF (one question per page, question is a raster image) and receive the correct number of question blocks — no answer key rows included.

**Acceptance Criteria:**
- All content pages before the answer key section are detected as blocks
- Answer key pages are excluded from output
- Blank pages and section-break notice pages are excluded
- Detected block count matches expected question count (e.g., 40 for gr_3 EOG)

### US-05 — STAAR-style text-rich exams
> As Krishna, I run the tool on a STAAR-style PDF (multi-question pages, text-based questions) and receive correct block boundaries.

**Acceptance Criteria:**
- Block boundaries align with actual question starts
- No partial questions (a block shall not end mid-question)
- No extra empty blocks prepended or appended

### US-06 — File size is reported
> As Ravi, after every run, I see input size → output size and savings in the terminal and in the compaction report.

**Acceptance Criteria:**
- Terminal output: `<original_size> -> <output_size> (<delta>, <pct>% reduction)`
- Compaction report contains a file size table row
- If output is larger than source, the report states "N KB larger" not "N KB saved"

### US-07 — No silent failures
> As Ravi, if the source PDF is unreadable, corrupted, or password-protected, the tool exits with a clear error message before starting the pipeline.

**Acceptance Criteria:**
- `ValidationError` raised before any processing begins
- Terminal output includes the specific reason (unreadable / corrupted / encrypted)
- Exit code is non-zero

### US-08 — Constructed-response blank space is trimmed
> As Krishna, when a question is a constructed-response (open-ended, not multiple-choice), I want the large blank work areas and answer lines trimmed down to 1–2 blank lines so the compacted output does not waste page space on empty fields.

**Background:** Released-test PDFs for NY and similar formats include constructed-response questions that reserve half a page or more for student work (blank lines, "Show your work" space, answer blanks labelled "Answer ___", "Explain how you know.", etc.). In a printed study worksheet this space is unnecessary because students will be doing the work on a separate sheet or on-screen.

**Acceptance Criteria:**
- A block is classified as `constructed_response` when its text contains one or more `CR_TRIM_MARKERS` below the last detectable content line (stem / diagram / answer choice)
- For NY format, the "This question is worth N credit(s)." line is a reliable indicator of a constructed-response block and MUST NOT itself be trimmed
- `y_bottom` is set to the y-coordinate of the first `CR_TRIM_MARKER` match + `CR_BLANK_LINES_KEEP` (default: 2) × `CR_LINE_HEIGHT_PTS` (default: 12)
- If no trim marker is found within the block span, no trimming is applied (safe fallback)
- Trimming is applied after `_expand_blocks_for_vector_choices` so vector-drawn diagrams are preserved
- At least 1 blank line of whitespace is visible below the last content element in every trimmed block

---

## 4. Non-Goals

| Non-Goal | Reason |
|----------|--------|
| Re-rendering question content from text | Introduces rendering errors; pixel-exact crop is the only safe strategy |
| Editing or modifying question content | Out of scope; the system is a visual repacker, not a question editor |
| OCR on image-heavy questions | Not needed for compaction; question content is preserved as-is from source raster |
| Generating answer keys | Separate feature (`generate_worksheet`) |
| Merging questions from multiple source PDFs | Out of scope for v1 |
| Support for non-PDF source formats | Out of scope for v1 |
| Web UI or API endpoint | CLI only for v1 |
| Accessibility (tagged PDF, screen reader) | Out of scope for v1; output is print-only |

---

## 5. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Detected block count accuracy | ± 0 vs expected | Compare `blocks_detected` in telemetry to golden count |
| Zero content loss | 100% of source questions in output | Visual comparison; comparator module |
| File size | ≤ 5 MB for ≤ 50 questions | `output_size_bytes` in telemetry |
| Pipeline crash rate | 0 silent failures | All failures produce a non-zero exit code and a log entry |
| Run time | ≤ 60 seconds for 50-question exam | `total_duration_s` in telemetry |
| Format detection accuracy | Correct classification for all known exam types | `format_detected` in telemetry vs golden |

---

## 6. Constraints

- Output must be visually indistinguishable from source (pixel-level rendering preservation)
- The tool runs locally on a teacher's or coordinator's machine; no cloud dependencies except Claude API
- Claude API is used only as a fallback for difficult block boundary detection; the primary path is PDF text analysis
- Python 3.10+ required; PyMuPDF, pdfplumber, Pillow are core dependencies

---

## 7. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| Q1 | Should `question_list` filtering (e.g., `--questions 1-10`) be exposed in the CLI or remain internal? | Krishna | Open |
| Q2 | Should the tool support multi-level subfolders when `--pdf` is a folder? | Ravi | Open |
| Q3 | What is the right behavior when a PDF has 0 detectable blocks? Warn and skip, or exit non-zero? | Ravi | Open |
