# Traceability Matrix — compact_source

**Feature:** `compact_source`
**Spec Version:** v4
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
| US-01 | Single PDF, 1-column compacted output | hld.md §2 pipeline | lld.md §3 Stage 4 | `pdf_packer.py::PdfPacker.pack()` `orchestrator.py::run_compact_source()` | — | QA-PACK-01, QA-PACK-03, QA-REP-01, QA-REP-02, QA-E2E-01 | Functional Correctness, Structural Quality | — | IN PROGRESS |
| US-02 | Single PDF, 2-column layout | hld.md §2 Stage 4 | spec.md §7.4, lld.md §3 | `pdf_packer.py::PdfPacker.pack()` (columns=2) | — | QA-PACK-02, QA-PACK-05 | Functional Correctness, Structural Quality | — | IN PROGRESS |
| US-03 | Folder batch run (all PDFs in folder, single run ID) | hld.md §2 orchestrator | spec.md §3 (folder input) | `orchestrator.py::run_compact_source()` | — | QA-PACK-04, QA-E2E-01 | Functional Correctness | — | IN PROGRESS |
| US-04 | EOG image-heavy exam: correct block count, no answer key | hld.md §2 Stage 1–2 | spec.md §4, §5.1, §5.3; lld.md §1 | `block_detector.py::BlockDetector.detect()` `block_detector.py::_classify_format()` `block_detector.py::_find_answer_key_fence()` | `test_content_aware_y_bottom_is_below_page_height` `test_bug_002_regression_height_fraction_check_catches_hardcoded` `test_y_bottom_uses_max_of_all_content_types` `test_no_content_falls_back_to_page_height` `test_y_bottom_never_exceeds_page_height` | QA-DET-01, QA-DET-02, QA-DET-03, QA-DET-04, QA-DET-05, QA-EXT-01, QA-EXT-02, QA-EXT-03, QA-EXT-04 | Functional Correctness, Source Fidelity | 2026-05-08 NY Grade 3/4/5 (Krishna) | IN PROGRESS |
| US-05 | STAAR text-rich exam: correct block boundaries | hld.md §2 Stage 2 | spec.md §5.2; lld.md §1 (text_rich path) | `block_detector.py::_detect_text_rich_blocks()` | — | — | Functional Correctness, Source Fidelity | — | NOT STARTED — EARS written (PRD v3 §US-05); Gherkin pending (IMP-024) |
| US-06 | File size delta reported in terminal and report | hld.md §2 Stage 5 | spec.md §8, §8.3; lld.md §4 | `reporter.py::Reporter.generate()` | — | QA-REP-01, QA-REP-02, QA-REP-03 | Functional Correctness | — | IN PROGRESS |
| US-07 | No silent failures — ValidationError before pipeline | hld.md §2 (validate) | spec.md §10, §11 | `orchestrator.py::run_compact_source()` | — | QA-VAL-01, QA-VAL-02, QA-VAL-03, QA-VAL-04 | Functional Correctness | — | NOT STARTED |
| US-08 | Constructed-response blank space trimmed | hld.md §2 Stage 2 | spec.md §5.5; lld.md §1 (CR trimming) | `block_detector.py::_trim_constructed_response_blocks()` | — | — | Functional Correctness, Structural Quality | — | NOT STARTED |
| US-09 | Human gate: operator confirms block count before extraction | hld.md §2 (human gate subgraph) | spec.md §4.5 | `orchestrator.py` (human gate block) | — | QA-HG-01, QA-HG-02, QA-HG-03, QA-HG-04 | Functional Correctness | — | NOT STARTED |
| US-10 | Question number labels on image-heavy output | hld.md §2 Stage 4 | spec.md §7.6; lld.md §3 | `pdf_packer.py::PdfPacker._render()` | — | — | Functional Correctness, Structural Quality | — | NOT STARTED |
| US-11 | Visual comparison against a golden sample | hld.md §2 (comparator) | spec.md §14; lld.md §5 | `comparator.py` | — | QA-CMP-01, QA-CMP-02, QA-CMP-03, QA-CMP-04 | Source Fidelity | — | NOT STARTED |

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

### RISK-08 — EARS missing for 10 of 11 User Stories 🔴
Only US-05 has EARS requirements. US-01–04, US-06–11 have acceptance criteria only — no machine-consumable system obligations. IC-3 gate is open for all but US-05.

**Impact:** AI agents implementing these stories have no formal obligation surface; drift is undetectable.

### RISK-09 — Traceability matrix referenced deleted design.md ✅ *(Resolved — 2026-05-10)*
All HLD/LLD references updated to `compact_source-hld.md` and `compact_source-lld.md` with section numbers. `design.md` was a zombie file and has been deleted.

### RISK-10 — "Answer Key" naming collision between ontology and spec 🔴
`mts-ontology.md §3.10` defines Answer Key as a *teacher-facing document* (companion to Worksheet).
`compact_source-spec.md §5.3` uses "answer key fence" to mean a *structural boundary region* in the source PDF that separates questions from answers.
These are two fundamentally different concepts sharing the same name.

**Impact:** Agents and code using "answer key" will interpret it differently depending on which layer they read first.

**Fix:** Add `AnswerKeyFence` as a distinct concept in `mts-ontology.md` for the structural PDF boundary.

### RISK-11 — `ExamFormat` and `ExamType` not in ontology ⚠️
`image_heavy` / `text_rich` (ExamFormat) and STAAR / EOG / NY Regents (ExamType) are used throughout the spec and code but are not defined in `mts-ontology.md`. Definition lives scattered across spec §4.1 and PRD §1 only.

**Fix:** Add `ExamFormat` and `ExamType` enums to ontology §3. IMP-026 tracks the broader exam-formats knowledge gap.

### RISK-12 — `Block` term used with 5 different phrasings across documents ⚠️
Docs use `question block`, `block span`, `block image`, `content block`, and `Block` interchangeably. The canonical ontology term (§3.8) is `Block`.

**Impact:** Spec and code that refer to "block" and agents that read the docs may fail to recognize they are talking about the same entity.

### RISK-13 — Feature name split: `compact_source` (docs) vs `compact_source_math` (module) ⚠️
All documentation uses the feature name `compact_source`. The Python module is `src/compact_source_math/`. This creates a navigation gap — searching for `compact_source_math` in docs or `compact_source` in code yields no match.

**Impact:** Onboarding confusion; agents that read docs may generate code referencing the wrong module path.

---

## 5. Recommended Actions (Priority Order)

| Priority | Action | Closes |
|---------|--------|--------|
| ✅ Done | Added US-09 (human gate), US-10 (question labels), US-11 (comparator) to PRD v2 | RISK-07 |
| ✅ Done | Added US-09, US-10, US-11 to PRD v2; comparator spec clause §14 added | RISK-03, RISK-07 |
| ✅ Done | QA scenarios added: QA-VAL-01–04, QA-HG-01–04, QA-CMP-01–04 | RISK-02, RISK-03 |
| ✅ Done | Traceability refs updated from design.md → hld.md + lld.md | RISK-09 |
| P1 | Write EARS for US-01–04, US-06–11 (IC-3 gate) | RISK-08 |
| P1 | Obtain STAAR Grade 3/4/5 PDFs; write QA-STAAR-01–04 | RISK-01 |
| P1 | Add `AnswerKeyFence` to ontology; disambiguate from Answer Key doc concept | RISK-10 |
| P2 | Add `ExamFormat` (`image_heavy`/`text_rich`) and `ExamType` (STAAR/EOG/NY) to ontology §3 | RISK-11 |
| P2 | Standardize all uses of "Block" across docs — eliminate `question block`, `block span`, `block image`, `content block` variants | RISK-12 |
| P2 | Decide canonical feature name (`compact_source` vs `compact_source_math`); align docs or module | RISK-13 |
| P2 | Add unit tests for `_classify_format()`, answer key fence, `PdfPacker.pack()`, `Reporter.generate()` | RISK-04, RISK-05 |
| P2 | Add spec version history — backfill known additions | RISK-06 |
| P3 | Run full QA sign-off for US-01–04, US-06, US-09, US-10, US-11 | All unverified rows |

---

## 6. Version History

| Version | Date | Change |
|---------|------|--------|
| v1 | 2026-05-10 | Initial matrix — 8 User Stories mapped. 7 risks identified. |
| v2 | 2026-05-10 | Added US-09, US-10, US-11 rows. RISK-07 resolved. RISK-03 downgraded to ⚠️ (PRD anchored; spec clause still needed). Updated recommended actions. |
| v3 | 2026-05-10 | US-05 status updated — EARS requirements written (PRD v3). IC-3 satisfied for US-05. Gherkin (IC-4) still pending via IMP-024. |
| v4 | 2026-05-10 | RISK-08–13 added from ontology/terminology spec health review. design.md refs replaced with hld.md+lld.md (RISK-09 resolved). US-07, US-09, US-11 QA scenario IDs backfilled. Recommended Actions updated. |
