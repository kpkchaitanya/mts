# Traceability Matrix — compact_source

**Feature:** `compact_source`
**Spec Version:** v1
**Status:** IN PROGRESS
**Last Updated:** 2026-05-10

---

## Purpose

Forward and backward traceability from each User Story through design, code,
unit tests, functional QA scenarios, eval dimensions, and verified production deployment.

A row is **VERIFIED** only when all columns are populated
and Deployment Verified has a real production entry.

---

## How to Read This Matrix

| Direction | Question |
|-----------|----------|
| Forward (left → right) | Did we build everything we intended? |
| Backward (right → left) | Is everything we built justified by a User Story? |

A gap (`—`) in any column is an open risk. See Section 4 for the risk log.

---

## 1. Traceability Matrix

| US-ID | User Story | High-Level Design | Low-Level Design | Module / Function | Unit Test ID | QA Scenario ID | Eval Dimension | Deployment Verified | Status |
|-------|-----------|------------------|-----------------|------------------|-------------|---------------|---------------|-------------------|--------|
| US-01 | Single PDF, 1-column compacted output | design.md §1 pipeline | design.md §1 Stage 4 | `pdf_packer.py::PdfPacker.pack()` `orchestrator.py::run_compact_source()` | — | QA-PACK-01, QA-PACK-03, QA-REP-01, QA-REP-02, QA-E2E-01 | Functional Correctness, Structural Quality | — | IN PROGRESS |
| US-02 | Single PDF, 2-column layout | design.md §1 Stage 4 | spec.md §7.4 | `pdf_packer.py::PdfPacker.pack()` (columns=2) | — | QA-PACK-02, QA-PACK-05 | Functional Correctness, Structural Quality | — | IN PROGRESS |
| US-03 | Folder batch run (all PDFs in folder, single run ID) | design.md §1 orchestrator | spec.md §3 (folder input) | `orchestrator.py::run_compact_source()` | — | QA-PACK-04, QA-E2E-01 | Functional Correctness | — | IN PROGRESS |
| US-04 | EOG image-heavy exam: correct block count, no answer key | design.md §1 Stage 1–2 | spec.md §4 (format detection), §5.1 (image_heavy path), §5.3 (answer key fence) | `block_detector.py::BlockDetector.detect()` `block_detector.py::_classify_format()` `block_detector.py::_find_answer_key_fence()` | `test_content_aware_y_bottom_is_below_page_height` `test_bug_002_regression_height_fraction_check_catches_hardcoded` `test_y_bottom_uses_max_of_all_content_types` `test_no_content_falls_back_to_page_height` `test_y_bottom_never_exceeds_page_height` | QA-DET-01, QA-DET-02, QA-DET-03, QA-DET-04, QA-DET-05, QA-EXT-01, QA-EXT-02, QA-EXT-03, QA-EXT-04 | Functional Correctness, Source Fidelity | 2026-05-08 NY Grade 3/4/5 (Krishna) | IN PROGRESS |
| US-05 | STAAR text-rich exam: correct block boundaries | design.md §1 Stage 2 | spec.md §5.2 (text_rich path) | `block_detector.py::_detect_text_rich_blocks()` | — | — | Functional Correctness, Source Fidelity | — | NOT STARTED — EARS written (PRD v3 §US-05); Gherkin pending (IMP-024) |
| US-06 | File size delta reported in terminal and report | design.md §1 Stage 5 | spec.md §8 (reporting), §8.3 (file size format) | `reporter.py::Reporter.generate()` | — | QA-REP-01, QA-REP-02, QA-REP-03 | Functional Correctness | — | IN PROGRESS |
| US-07 | No silent failures — ValidationError before pipeline | design.md §1 (validate) | spec.md §10 (exception taxonomy), §11 (edge cases) | `orchestrator.py::run_compact_source()` | — | — | Functional Correctness | — | NOT STARTED |
| US-08 | Constructed-response blank space trimmed | — | spec.md §5.5 (CR trimming) | `block_detector.py::_trim_constructed_response_blocks()` | — | — | Functional Correctness, Structural Quality | — | NOT STARTED |

| US-09 | Human gate: operator confirms block count before extraction | design.md §1 (human gate subgraph) | spec.md §4.5 | `orchestrator.py` (human gate block) | — | — | Functional Correctness | — | NOT STARTED |
| US-10 | Question number labels on image-heavy output | design.md §1 Stage 4 | spec.md §7.6 | `pdf_packer.py::PdfPacker._render()` | — | — | Functional Correctness, Structural Quality | — | NOT STARTED |
| US-11 | Visual comparison against a golden sample | — | Not yet in spec.md ⚠️ | `comparator.py` | — | — | — | — | NOT STARTED |

---

## 2. Backward Traceability Check

Previously unanchored behaviors — now resolved by PRD v2 (US-09, US-10, US-11).

| Behavior | Code Location | Resolution |
|---------|--------------|-----------|
| Human gate (block count confirmation) | `orchestrator.py` | ✅ Anchored to US-09 (PRD v2) |
| Question number overlay | `pdf_packer.py::_render()` | ✅ Anchored to US-10 (PRD v2) |
| Visual comparison (`--compare`) | `comparator.py` | ✅ Anchored to US-11 (PRD v2) — spec clause still needed |

---

## 3. Deployment Verified Log

Records each time a User Story was confirmed working in real production.

| US-ID | Date | Exam PDF Used | Reviewer | Notes |
|-------|------|--------------|---------|-------|
| US-04 | 2026-05-08 | NY Math Grade 3, 4, 5 (2023 Released) | Krishna | 22/27/20 blocks detected. 2-col output reviewed. Partial — answer key and CR trimming not separately verified per-story. |

All other User Stories: no deployment verification recorded.

---

## 4. Open Risks from This Matrix

### RISK-01 — US-05 (STAAR text-rich) has zero test coverage 🔴
No unit tests, no QA scenarios, no deployment verification for STAAR-style PDFs.
The spec defines the path in §5.2 and makes testable claims (gr_3=32, gr_4=35, gr_5=36 blocks)
but none of these are tested or manually verified.

**Impact:** If text-rich block detection regresses, there is no signal.

### RISK-02 — US-07 (no silent failures) has no QA scenario 🔴
Exception taxonomy exists in spec §10 and edge cases in §11 but there is no QA scenario
that actually triggers a ValidationError and confirms the correct error message and exit code.

**Impact:** A regression in error handling would ship silently.

### RISK-03 — US-11 (visual comparison) has no spec clause ⚠️ *(Partially resolved)*
`comparator.py` is now anchored to US-11 in PRD v2. However, there is still no spec
clause governing its behavior, no QA scenario, and no eval dimension.

**Remaining action:** Add §X to spec.md governing comparator behavior (similarity threshold,
output format, REVIEW vs FAIL verdict). Then add QA scenarios.

### RISK-04 — Unit test coverage is critically thin 🔴
Only 5 unit tests exist, all in `test_block_detector.py`, all about `y_bottom` boundary math.
No tests for: `_classify_format()`, answer key fence, text-rich detection, PDF packer layout,
reporter output, validation, batch orchestration, CR trimming, question number overlay.

**Impact:** All functional correctness is carried entirely by manual QA scenarios.
A code change that breaks packing or reporting has no automated safety net.

### RISK-05 — No unit tests for US-01, US-02, US-03, US-06, US-07, US-08, US-09, US-10, US-11 🔴
Unit Test column is empty for 9 of 11 User Stories.

### RISK-06 — Spec version history missing ⚠️
Question number overlay (§7.6), CR trimming (§5.5), and fraction-based format detection (§4.2)
were clearly added after v1 but there is no version history in the spec.
Impossible to know what the spec looked like at any prior point.

### RISK-07 — Human gate, question number overlay, and comparator had no User Stories ✅ *(Resolved)*
All three are now anchored to US-09, US-10, US-11 in PRD v2 (2026-05-10).

---

## 5. Recommended Actions (Priority Order)

| Priority | Action | Closes |
|---------|--------|--------|
| ✅ Done | Added US-09 (human gate), US-10 (question labels), US-11 (comparator) to PRD v2 | RISK-07 |
| P1 | Add spec clause for comparator (US-11) to spec.md | RISK-03 |
| P1 | Write QA scenarios for US-05 (STAAR) and US-07 (error handling) | RISK-01, RISK-02 |
| P1 | Write QA scenarios for US-09 (human gate) and US-11 (comparator) | RISK-03 |
| P2 | Add unit tests for `_classify_format()` and answer key fence | RISK-04 |
| P2 | Add unit tests for `PdfPacker.pack()` layout logic | RISK-04, RISK-05 |
| P2 | Add unit tests for `Reporter.generate()` file size row | RISK-04, RISK-05 |
| P2 | Add spec version history — backfill known additions | RISK-06 |
| P3 | Run US-05 against STAAR PDFs and populate Deployment Verified | RISK-01 |
| P3 | Run full QA sign-off for US-01, US-02, US-03, US-06, US-07, US-09, US-10, US-11 | All unverified rows |

---

## 6. Version History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-05-10 | Initial matrix — 8 User Stories mapped. 7 risks identified. |
| v2 | 2026-05-10 | Added US-09, US-10, US-11 rows. RISK-07 resolved. RISK-03 downgraded to ⚠️ (PRD anchored; spec clause still needed). Updated recommended actions. |
| v3 | 2026-05-10 | US-05 status updated — EARS requirements written (PRD v3). IC-3 satisfied for US-05. Gherkin (IC-4) still pending via IMP-024. |
