# compact_source — Spec Folder README

**Feature:** `compact_source`
**Folder:** `.agent/specs/compact_source/`
**Last Updated:** 2026-05-10

---

## Purpose

This folder contains all product management, specification, design, and quality artifacts for the `compact_source` feature — the pipeline that takes a source math exam PDF and produces a print-ready, densely packed output PDF while preserving all content pixel-for-pixel.

Every document here sits within the MTS governance authority chain:

```
Soul → Constitution → PM Framework → agent.md → Spec (this folder) → Eval → Workflow → Agents → Output
```

No implementation may begin until the relevant spec passes the Spec Readiness Checklist (IC-1 through IC-6 + structural 1–11) in `holistic-ai-native-cognitive-architecture.md §8.4`.

---

## Document Map

### Core SDLC Chain

```
compact_source-prd.md            ← PM layer: business intent · user stories · EARS requirements
    ↓ governs
compact_source-spec.md           ← behavioral contract: stages · inputs · outputs · constants · exceptions
    ↓ elaborated by
compact_source-hld.md            ← system design: pipeline · data model · module dependencies · decisions
    ↓ detailed by
compact_source-lld.md            ← detailed design: algorithms · telemetry schema · logging · delivery log
    ↓ verified by
compact_source-qa-scenarios.md   ← Gherkin-level QA acceptance scenarios
    ↓ tracked through
compact_source-traceability.md   ← US → design → code → test → eval → deployment
    ↓ work items in
compact_source-backlog.md        ← compact_source-specific improvement backlog (CS-001…CS-024)
```

---

### 1. `compact_source-prd.md` — Product Requirements Document
**Version:** v3 | **Status:** Active | **Authority:** PM layer — primary product intent

Defines the *why* and the *what* from the business perspective. All downstream documents derive from it.

| Section | Content |
|---------|---------|
| Problem Statement | Paper waste, print cost, teacher workflow pain |
| Personas | Krishna (teacher), Neelima (coordinator), Ravi (admin) |
| User Stories (US-01–US-11) | INVEST-validated; each with acceptance criteria and EARS requirements |
| EARS Requirements | Machine-consumable system obligations (US-05 fully written; US-01–04/06–11 IC-3 gap) |
| Non-Goals | Out of scope for v1 |
| Success Metrics | Block count accuracy, run time, file size, crash rate |
| Open Questions | Q1–Q5, unresolved design decisions |
| Version History | v1 (Apr 26) → v3 (May 10) |

---

### 2. `compact_source-spec.md` — Feature Specification
**Version:** v2 | **Status:** Active | **Authority:** Behavioral contract — agents read this before acting

The executable contract between intent (PRD) and code. All pipeline behavior must conform to it.

| Section | Governs |
|---------|---------|
| §1 Overview | What the feature does |
| §2 Pipeline Stages | 5-stage pipeline diagram |
| §3 Input Contract | All CLI parameters, types, defaults, validation rules |
| §4 Format Detection | `image_heavy` vs `text_rich` — fraction-based majority vote, constants, failure modes |
| §4.5 Human Gate | Interactive confirmation before extraction; LOW COUNT WARNING; `--yes` bypass |
| §5 Block Detection | `image_heavy` path (§5.1); `text_rich` path (§5.2); answer key fence (§5.3); y_bottom helper (§5.4) |
| §5.5 CR Trimming | Constructed-response blank space trim algorithm and constants |
| §6 Block Extraction | Rasterization, cross-page block assembly |
| §7 Page Packing | 1-col / 2-col layout, scale_factor, question label overlay |
| §8 Reporting | `compaction-report.md`, `source-boundary-map.md`, file size format |
| §9 Output Contract | File naming, run folder structure |
| §10 Exception Taxonomy | `ValidationError`, `DetectionError`, `ExtractionError`, `PackingError`, `ReportingError` |
| §11 Edge Cases | Empty folder, oversized blocks, encrypted PDF, 0 blocks |
| §12 Constants Table | All tunable constants with defaults |
| §13 Testability Checklist | TC-DET-01 through TC-CMP-05 |
| §14 Visual Comparison (US-11) | SSIM per-page, `COMPARATOR_SIMILARITY_THRESHOLD=0.97`, REVIEW verdict |

---

### 3. `compact_source-hld.md` — High-Level Design (System Design)
**Version:** v1 | **Status:** Active | **Authority:** Architecture reference

System-wide view with rich Mermaid visualizations. Read this to understand how the feature works as a whole and how it connects to the rest of the platform.

| Section | Content |
|---------|---------|
| §1 Architectural Philosophy | Why pixel-preservation; no text extraction; no re-rendering |
| §2 End-to-End Pipeline | Full 5-stage Mermaid flowchart including human gate and artifact outputs |
| §3 Data Model | Class diagram: PageSlice → QuestionBlock → BlockDetectionResult → ExtractedBlock → _PlacedBlock |
| §4 Module Dependency Map | All modules, utilities, external libraries, config — with dependency arrows |
| §5 Holistic Platform Impacts | Phases 2–5 (Observability, Resilience, Quality, Self-Improvement) with platform spec pointers |
| §6 Key Architectural Decisions | 7 numbered decisions with rationale (D-HLD-01 through D-HLD-07) |
| §7 Exam Format Support Matrix | Which formats are verified, which are RISK |
| §8 Artifact Layout | Run folder structure for single-file and batch runs |
| §9 Cross-Document Reference Map | How all documents in this folder connect |

---

### 4. `compact_source-lld.md` — Low-Level Design (Detailed Design)
**Version:** v1 | **Status:** Active | **Authority:** Implementation guide — read before touching any module

Per-module and per-algorithm detail with Mermaid flowcharts for every stage.

| Section | Content |
|---------|---------|
| §1 Stage 1 & 2 — Format Detection + Block Detection | Flowcharts for `_classify_format()`, `image_heavy` path, `text_rich` path; CR trimming; all constants |
| §2 Stage 3 — Block Extraction | `BlockExtractor.extract()` flowchart; blank-row pixel trimming; constants |
| §3 Stage 4 — Page Packing | Phase 1 (compute_layout) + Phase 2 (render) flowcharts; gap-fill algorithm; layout constants |
| §4 Stage 5 — Reporting | `compaction-report.md` and `source-boundary-map.md` content contracts |
| §5 Stage 6 — Visual Comparator | SSIM algorithm, verdict semantics, page count mismatch handling |
| §6 Telemetry Schema | `run-telemetry.json` full schema; defect entry format; defect codes table |
| §7 Logging Architecture | Logger hierarchy diagram; handler lifecycle; log levels |
| §8 Phase Delivery Log | Phase 6.6 (format fix + human gate), Phase 6.5 (question labels), Phase 6.4 (height efficiency), Phase 2 design |

---

### 5. `compact_source-qa-scenarios.md` — Functional QA Scenarios
**Version:** v2 | **Status:** Active | **Authority:** Must be run after every code change — no exceptions

Gherkin-layer acceptance gate. A single FAIL blocks any change from being closed.

| Stage | Scenario IDs | US | Status |
|-------|-------------|-----|--------|
| Stage 1 — Block Detection | QA-DET-01–05 | US-04 | ✅ |
| Stage 2 — Block Extraction | QA-EXT-01–04 | US-04 | ✅ |
| Stage 3 — Page Packing | QA-PACK-01–05 | US-01–03 | ✅ |
| Stage 4 — Reporting | QA-REP-01–03 | US-06 | ✅ |
| Stage 5 — End-to-End | QA-E2E-01 | US-01, US-03 | ✅ |
| Stage 6 — Input Validation | QA-VAL-01–04 | US-07 | ✅ |
| Stage 7 — Human Gate | QA-HG-01–04 | US-09 | ✅ |
| Stage 8 — Visual Comparison | QA-CMP-01–04 | US-11 | ✅ |
| **STAAR text-rich** | **QA-STAAR-01–04** | **US-05** | ❌ Pending PDFs (CS-024) |

**Reference inputs:** NY Math Grade 3/4/5 2023 Released Tests — 22 / 27 / 20 blocks respectively.

---

### 6. `compact_source-traceability.md` — Traceability Matrix
**Version:** v3 | **Status:** In Progress

Forward (left→right) and backward (right→left) traceability across all 11 user stories.

**Open risks:**

| Risk | Severity | Description |
|------|----------|-------------|
| RISK-01 | 🔴 P1 | US-05 (STAAR): zero QA, no deployment. EARS ✅; Gherkin + PDFs needed. |
| RISK-02 | 🔴 P1 | US-07: no QA scenarios for `ValidationError` paths |
| RISK-04 | 🔴 P1 | Unit tests critically thin — only 5 tests, all `y_bottom` math |
| RISK-05 | 🔴 P1 | 9 of 11 User Stories have zero unit tests |
| RISK-06 | ⚠️ P2 | Spec version history incomplete |

---

### 7. `compact_source-backlog.md` — compact_source Feature Backlog
**Version:** v1 | **Status:** Active

All `compact_source`-specific improvement items in phase order. Original global IMP-NNN IDs cross-referenced. Global items remain in `.agent/improvements/backlog.md`.

| Phase | Theme | Key Items | Status |
|-------|-------|-----------|--------|
| Phase 1 — Foundation | Spec + PRD | CS-001 | ✅ Complete |
| Phase 2 — Observability | Telemetry + Logging | CS-003, CS-004 | 🔲 Planned |
| Phase 3 — Resilience | Robustness + Safety | CS-005–007 | 🔲 Planned |
| Phase 4 — Quality | Eval + Gate | CS-002, CS-008–009 | 🔲 Planned |
| Phase 5 — Self-Improvement | Learn + Heal | CS-010–012 | 🔲 Planned |

---

## Read Order

```
1. compact_source-prd.md          ← Problem, personas, user stories, EARS
2. compact_source-spec.md         ← Behavioral contract — what must be true
3. compact_source-hld.md          ← System structure and holistic impact (start here for code)
4. compact_source-lld.md          ← Algorithm detail (read before modifying a module)
5. compact_source-traceability.md ← Gaps and risks
6. compact_source-qa-scenarios.md ← How to verify after any change
7. compact_source-backlog.md       ← What work is planned and in what order
```

---

## SDLC Status Summary

| US | Story | EARS | Gherkin | Code | Deployed | Overall |
|----|-------|------|---------|------|----------|---------|
| US-01 | 1-col output | ❌ | ✅ | ✅ | ❌ | In Progress |
| US-02 | 2-col output | ❌ | ✅ | ✅ | ❌ | In Progress |
| US-03 | Folder batch | ❌ | ✅ | ✅ | ❌ | In Progress |
| US-04 | EOG image-heavy | ❌ | ✅ | ✅ | ✅ 2026-05-08 | In Progress |
| US-05 | STAAR text-rich | ✅ | ❌ | ❌ | ❌ | IC-4 gate — PDFs needed |
| US-06 | File size reported | ❌ | ✅ | ✅ | ❌ | In Progress |
| US-07 | No silent failures | ❌ | ✅ | ❌ | ❌ | Not started |
| US-08 | CR trimming | ❌ | ❌ | ❌ | ❌ | Not started |
| US-09 | Human gate | ❌ | ✅ | ✅ | ❌ | In Progress |
| US-10 | Question labels | ❌ | ❌ | ✅ | ❌ | IC-4 gap |
| US-11 | Visual comparison | ❌ | ✅ | ❌ | ❌ | Not started |

---

## Immediate Open Work (Priority Order)

| Priority | Action | Artifact | Closes |
|----------|--------|----------|--------|
| P1 | Obtain STAAR Grade 3/4/5 PDFs; write QA-STAAR-01–04 | `compact_source-qa-scenarios.md` | CS-024, RISK-01 |
| P1 | Write Gherkin scenarios for US-08 (CR trimming) | `compact_source-qa-scenarios.md` | IC-4 for US-08 |
| P1 | Write Gherkin scenarios for US-10 (question labels) | `compact_source-qa-scenarios.md` | IC-4 for US-10 |
| P1 | Implement `_detect_text_rich_blocks()` against spec §5.2 | Code | US-05 |
| P1 | Implement US-11 comparator against spec §14 | Code | US-11 |
| P2 | Unit tests for `_classify_format()`, `_find_answer_key_fence()` | `tests/` | RISK-04 |
| P2 | Unit tests for `PdfPacker.pack()`, `Reporter.generate()` | `tests/` | RISK-05 |
| P2 | Backfill spec version history (§4.2, §5.5, §7.6) | `compact_source-spec.md` | RISK-06 |
| P3 | Full QA sign-off run for US-01–04, US-06, US-09 | Manual run | Deployment Verified column |
