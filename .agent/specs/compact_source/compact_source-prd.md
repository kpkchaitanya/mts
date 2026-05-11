# compact_source-prd.md — Product Requirements Document

**Feature:** `compact_source`
**Version:** v4
**Status:** Active
**Date:** 2026-05-10

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

### 3.0 User Story Analysis — Intent Review Table

Compact reference for human intent review, PM-layer planning, and IC-checklist triage.
Each row is a decision surface — not a spec. Elaboration lives in §3.1–3.11 and downstream artifacts.

| Story ID | Functional Area | Business Outcome | Primary Trigger | Core Behavior | EARS Type | Gherkin Status | Main Technical Concerns | Cross-Cutting Concerns | INVEST Risk | Recommended Split |
|----------|----------------|-----------------|----------------|--------------|-----------|---------------|------------------------|----------------------|-------------|------------------|
| US-01 | Output Generation | Print-ready 1-col PDF | Teacher runs CLI `--pdf <file>` | Detect blocks → extract → pack 1-col → report | Ubiquitous | ✅ QA-PACK-01/03, E2E-01 | `PdfPacker.pack()`, file naming, orchestrator | Pixel fidelity, run artifacts | No EARS written | Separate packing from orchestration |
| US-02 | Output Generation | Denser layout, more questions/page | `--columns 2` flag | Scale blocks to column width, 2-col pack | Optional (flag-driven) | ✅ QA-PACK-02/05 | `PdfPacker.pack(columns=2)`, block scaling | No clipping, pixel fidelity | Dependent on US-01 | Can stay merged |
| US-03 | Batch Processing | Process N exams in one invocation | `--pdf <folder>` | Walk folder, shared run ID, per-PDF report | State-Driven (while folder input) | ✅ QA-PACK-04, E2E-01 | Orchestrator folder walk, shared run ID | Error isolation per file, run artifacts | Moderate scope | Separate error-isolation per file |
| US-04 | Format Detection + Block Detection | Correct blocks from image-heavy exams | `image_heavy` PDF submitted | Classify format → detect by image boundary → exclude answer key fence | Event-Driven + Unwanted | ✅ QA-DET-01–05, EXT-01–04 | `_classify_format()`, `_find_answer_key_fence()`, y_bottom | Format detection accuracy, golden counts | Complex; deployed but partial QA | Separate format detect / AK fence / CR trim |
| US-05 | Format Detection + Block Detection | Correct block boundaries in text-based exams | `text_rich` PDF submitted | Classify as text_rich → detect via `QUESTION_LINE_PATTERN` → Claude fallback | Ubiquitous + Event-Driven + Unwanted + State-Driven + Optional | ❌ Pending STAAR PDFs (IMP-024) | `_detect_text_rich_blocks()`, Claude fallback, CR trim | Golden block counts (gr3=32/gr4=35/gr5=36), Claude API resilience | Not implemented; STAAR PDFs needed | Separate regex path / Claude fallback / CR trim |
| US-06 | Reporting | Transparency on compaction savings | Every successful run | Compute input→output size delta; write to terminal + report | Ubiquitous | ✅ QA-REP-01–03 | `Reporter.generate()`, file size format | Run artifacts, larger-than-source edge case | Low risk | None needed |
| US-07 | Input Validation | No mystery failures; operational reliability | Unreadable / corrupted / encrypted PDF submitted | Raise `ValidationError` before pipeline; non-zero exit | Unwanted | ✅ QA-VAL-01–04 | Orchestrator validation, exception taxonomy | Exit codes, observability | Not a true user story — system quality | Consider converting to platform resilience capability |
| US-08 | Block Detection | No wasted blank space in printed output | Block contains `CR_TRIM_MARKERS` | Trim `y_bottom` to first marker + `CR_BLANK_LINES_KEEP` lines | State-Driven (while CR markers present) | ❌ No Gherkin | `_trim_constructed_response_blocks()`, y_bottom | Pixel fidelity, ≥1 blank line preserved | Coupled to block detection; no Gherkin (IC-4 gap) | Separate NY format detection from trim logic |
| US-09 | Operator Safety Gate | Prevent defective output reaching teachers | Block detection complete in interactive mode | Display count+format → prompt Y/n → abort on n | State-Driven + Unwanted (LOW COUNT WARNING) | ✅ QA-HG-01–04 | Orchestrator gate, TTY detection, `--yes` flag | Observability, non-interactive stdin detection | Low risk; implemented | None needed |
| US-10 | Output Quality | Students can reference original question numbers | `image_heavy` format output | Overlay question number label on each block image | State-Driven (while image_heavy) + Optional (`--no-question-numbers`) | ❌ No Gherkin | `PdfPacker._render()`, PDF text overlay, white background rect | PDF text extractability | No Gherkin (IC-4 gap); implemented | Separate auto-enable logic from label rendering |
| US-11 | QA / Regression Detection | Catch visual regressions after code changes | `--compare --golden <path>` flag | SSIM per-page comparison; flag pages below threshold as REVIEW | Optional + Event-Driven (page count mismatch) | ✅ QA-CMP-01–04 | `comparator.py`, SSIM, `COMPARATOR_SIMILARITY_THRESHOLD` | Operator judgment (REVIEW not FAIL), golden sample management | Weak business ownership; more platform capability | Separate comparison engine from reporting |

**IC-3 gap:** EARS written only for US-05. US-01–04, US-06–11 have acceptance criteria only. See RISK-08 in `compact_source-traceability.md`.
**IC-4 gap:** Gherkin missing for US-05, US-08, US-10. See traceability RISK-01, CS-024.

---


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

**EARS Requirements**

*Ubiquitous — always-true system obligations:*

- REQ-05-U1: The system shall classify a PDF as `text_rich` when fewer than 50% of sampled content pages contain 5 words or fewer.
- REQ-05-U2: The system shall detect block boundaries for `text_rich` PDFs by scanning for question-number lines matching `QUESTION_LINE_PATTERN` (e.g., `^\d+\.?\s` or `^Q\d+`).
- REQ-05-U3: The system shall start a new block at each line that matches `QUESTION_LINE_PATTERN` and end the block at the line immediately before the next match, at the page boundary, or at the answer key fence — whichever comes first.
- REQ-05-U4: The system shall produce exactly 32 blocks for a valid STAAR 2022 Grade 3 PDF, 35 blocks for Grade 4, and 36 blocks for Grade 5.
- REQ-05-U5: The system shall guarantee that no block spans more than `DEFAULT_MAX_BLOCK_PAGES` (default: 2) pages.

*Event-Driven — triggered by classification result:*

- REQ-05-E1: When format detection returns `text_rich`, the system shall route block detection exclusively to `_detect_text_rich_blocks()` and shall not execute any `image_heavy` detection logic.
- REQ-05-E2: When `_detect_text_rich_blocks()` finds fewer than `MIN_QUESTIONS_FALLBACK` (default: 3) blocks by regex scan, the system shall invoke the Claude vision fallback and send page renders for boundary detection.
- REQ-05-E3: When the answer key fence is detected in a `text_rich` PDF, the system shall exclude all pages from the fence page onward from block detection.

*Unwanted — conditions the system must reject or contain:*

- REQ-05-W1: If a `QUESTION_LINE_PATTERN` match is found on a page within the answer key fence range, the system shall discard that match and not create a block from it.
- REQ-05-W2: If a block boundary scan would produce a block with zero extractable content (empty y-range), the system shall discard that block rather than passing an empty block downstream.
- REQ-05-W3: If the Claude vision fallback is invoked and returns a block count inconsistent with the regex result by more than `FALLBACK_DISAGREEMENT_THRESHOLD`, the system shall log a `WARNING` and use the Claude result.

*State-Driven — while in a specific pipeline state:*

- REQ-05-S1: While processing a `text_rich` PDF, the system shall not apply the `_find_image_heavy_y_bottom` footer-exclusion strategy; `y_bottom` is derived from text line bounding boxes only.
- REQ-05-S2: While processing a `text_rich` block, the system shall apply `_trim_constructed_response_blocks()` for any block whose text contains a line matching `CR_TRIM_MARKERS` (see spec §5.5).

*Optional — where a feature flag is active:*

- REQ-05-O1: Where `columns=2` is specified, the system shall pack all `text_rich` blocks into 2-column layout using the same `PdfPacker.pack()` path as `image_heavy`, with no `text_rich`-specific packing logic.
- REQ-05-O2: Where `question_list` is not `"ALL"`, the system shall filter the detected block list to only the specified question numbers before passing to extraction; question numbering is 1-based and derived from block detection order.

**Spec Reference:** spec.md §4 (format detection), §5.2 (text_rich path), §5.5 (CR trimming), §4.3 (constants)

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

### US-09 — Human gate: operator confirms block count before extraction
> As Ravi, when running the tool interactively, I want to see the detected block count and confirm before extraction begins, so I can catch detection errors before a useless output PDF is produced.

**Background:** Block detection can mis-classify hybrid-format PDFs or fail on non-standard question numbering. Without a confirmation gate, a near-empty block set would silently produce a defective output that reaches teachers and students.

**Acceptance Criteria:**
- In interactive mode (`auto_confirm=False`, stdin is a TTY), the pipeline MUST pause after detection and display: detected block count, source page count, detected format, and a `WARNING: LOW COUNT` message if count < 3 or < 0.5 blocks/page
- The operator is prompted `[Y/n]` to continue or abort
- Responding `n` or `no` aborts the pipeline cleanly with exit code 0 and a clear message
- The `WARNING: LOW COUNT` message MUST appear even when `auto_confirm=True` (batch mode) — it is a log signal, not just a prompt
- Running with `--yes` / `-y` sets `auto_confirm=True` and skips the prompt (for scripted/batch runs)
- Non-interactive stdin (piped input) skips the prompt silently

### US-10 — Question number labels on image-heavy output
> As Krishna, when I compact an EOG-style exam (where question numbers are embedded in the source footer that gets removed), I want each block in the output PDF to show its question number, so students can reference the original exam without confusion.

**Background:** EOG and similar image-heavy PDFs embed the question number as a page footer (e.g., "5 of 40"). The compaction pipeline removes the footer to eliminate wasted whitespace (BUG-002). Without labels, the output PDF has no question numbers — a student-facing quality defect.

**Acceptance Criteria:**
- For `image_heavy` format outputs, each block image in the output PDF MUST have a text label (e.g., `"1."`) at the top-left corner
- The label has a white-filled background rectangle so it is legible over any image content
- Labels are numbered from `question_start` (default: 1); `--question-start N` sets the offset
- `--no-question-numbers` suppresses all labels for cases where the teacher does not want them
- Label text is written as PDF text (not as an image) — extractable by a PDF text reader
- For `text_rich` format, labels are NOT added (question numbers are already embedded in the block images)
- The orchestrator auto-enables labeling for `image_heavy` unless explicitly suppressed by the caller

### US-11 — Visual comparison against a golden sample
> As Neelima, I want to compare a compacted output PDF against a known-good reference (golden sample) page-by-page, so I can verify that a code change or configuration change has not degraded the visual quality of the output.

**Background:** As the pipeline evolves, it is necessary to catch visual regressions — cases where output looks different from a previously approved reference. Manual visual inspection of every page is impractical at scale. An automated visual diff provides a fast, objective signal.

**Acceptance Criteria:**
- Running with `--compare --golden <path>` compares the output PDF against the golden PDF page by page
- For each page pair, the comparator renders both at the same DPI and computes a pixel-level similarity score
- Pages with similarity below a threshold are flagged in the terminal and in the compaction report
- A summary line states: total pages compared, pages passed, pages flagged
- If any page is flagged, the run result is `REVIEW` (not `FAIL` — the operator makes the final call)
- The comparator does not modify the output PDF or the golden PDF
- If page counts differ between output and golden, all extra pages are flagged automatically

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
| Q4 | Should the visual comparator (US-11) support a configurable similarity threshold? | Neelima | Open |
| Q5 | Should `--question-start` (US-10) be auto-inferred from the question list, or always manual? | Krishna | Open |

---

## 8. Version History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-04-26 | Initial PRD — US-01 through US-08 |
| v2 | 2026-05-10 | Added US-09 (human gate), US-10 (question number labels), US-11 (visual comparison). Removed visual comparison from Non-Goals. Added Q4, Q5. Traceability gap closure from compact_source-traceability.md audit. |
| v3 | 2026-05-10 | Added EARS requirements to US-05 (STAAR text-rich): 12 EARS sentences covering Ubiquitous (U1–U5), Event-Driven (E1–E3), Unwanted (W1–W3), State-Driven (S1–S2), Optional (O1–O2). Closes IC-3 for US-05. |
| v4 | 2026-05-10 | Added §3.0 User Story Analysis Table — compact intent review surface covering all 11 stories with EARS type, Gherkin status, technical concerns, INVEST risks, and recommended splits. IC gap callouts added. |
