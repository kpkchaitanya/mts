# PRD: compact_source

**Feature:** compact_source
**Version:** v1
**Status:** Active (In Production)
**Owner:** MTS Engineering

---

## 1. Problem Statement

MTS teachers receive source worksheet PDFs that are often poorly laid out for printing:
* Wide margins waste paper
* Single large questions leave pages half-empty
* Diagrams and graphs are embedded in non-extractable ways

Teachers spend time reformatting worksheets before they can be used in class.
This is manual, inconsistent work that doesn't scale across multiple grades and subjects.

---

## 2. User Personas

| Persona | Need |
|---------|------|
| MTS Teacher | Receives a ready-to-print compact worksheet without manual reformatting |
| MTS Admin | Can batch-process multiple PDFs before a teaching week begins |

---

## 3. Goals

1. Reduce per-worksheet prep time from ~15 minutes to < 2 minutes.
2. Preserve all visual content (math symbols, graphs, diagrams) exactly.
3. Produce a print-ready output in fewer pages than the source.
4. Give the teacher visibility and control over what was extracted.

---

## 4. Non-Goals

* Does NOT generate new content — only restructures existing content.
* Does NOT interpret or understand the math in the source.
* Does NOT OCR text — content is treated as raster images.
* Does NOT support scanned/hand-written PDFs (only digitally-created PDFs).

---

## 5. User Stories

**US1 — Core Extraction**
As a teacher, I want to compact a source worksheet PDF into a smaller output PDF,
so that I can print it efficiently without wasting paper.

**US2 — Visual Fidelity**
As a teacher, I want the compacted output to look exactly like the original questions,
so that students aren't confused by altered formatting.

**US3 — Question Selection**
As a teacher, I want to select which questions to include (e.g., problems 1–10),
so that I can assign targeted practice without editing the PDF manually.

**US4 — Block Confirmation Gate**
As a teacher running the tool interactively, I want to see how many blocks were
detected before extraction proceeds, so that I can catch detection errors early.

**US5 — Batch Processing**
As an admin, I want to compact all PDFs in a folder at once,
so that I can prepare an entire week's materials without running the tool repeatedly.

**US6 — Visual Comparison**
As a teacher, I want to compare my output against a golden sample,
so that I can verify quality before printing.

---

## 6. Success Criteria

| Criterion | Target |
|-----------|--------|
| Page reduction vs source | ≥ 20% fewer pages in output |
| Visual fidelity | All question content preserved without distortion |
| Block detection accuracy | ≥ 95% of questions detected on standard source PDFs |
| Prep time | Teacher ready to print in < 2 minutes |
| Batch reliability | 0 silent failures in batch mode |

---

## 7. Open Questions

* What is the upper bound on source PDF page count for acceptable performance?
* Should the tool support two-column layout as a default or as an option?
* Is visual comparison (golden diff) a regularly-used workflow or exceptional?
