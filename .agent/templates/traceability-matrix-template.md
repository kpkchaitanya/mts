# Traceability Matrix — [Feature Name]

**Feature:** `[feature_name]`
**Spec Version:** v[N]
**Status:** IN PROGRESS | VERIFIED
**Last Updated:** YYYY-MM-DD

---

## Purpose

This matrix provides complete forward and backward traceability
from User Story through design, code, tests, evals, and verified production deployment.

A row is **VERIFIED** only when all columns are populated
and Deployment Verified has a real production entry.

---

## How to Read This Matrix

| Direction | Question |
|-----------|----------|
| Forward (left → right) | Did we build everything we intended? |
| Backward (right → left) | Is everything we built justified by a User Story? |

A gap in any column for a row is an open risk.
An empty Deployment Verified is an unconfirmed delivery.

---

## Matrix

| US-ID | User Story | High-Level Design | Low-Level Design | Module / Function | Unit Test ID | QA Scenario ID | Eval Dimension | Deployment Verified | Status |
|-------|-----------|------------------|-----------------|------------------|-------------|---------------|---------------|-------------------|--------|
| US-01 | [title] | [design-doc.md §N] | [system-design.md §N] | `src/[module]/[file].py::[fn]` | `TC-[ID]` | `QA-[ID]` | [Eval dimension] | — | NOT STARTED |
| US-02 | [title] | | | | | | | — | NOT STARTED |
| US-03 | [title] | | | | | | | — | NOT STARTED |

---

## Deployment Verified Log

Records each time a User Story was confirmed working in production.

| US-ID | Date | Exam PDF Used | Reviewer | Notes |
|-------|------|--------------|---------|-------|
| US-01 | — | — | — | — |

---

## Backward Traceability Check

List any code modules / functions that exist **without** a corresponding US-ID row above.
These represent unauthorized behavior and must be either linked to a User Story
or removed.

| Module / Function | Issue | Resolution |
|------------------|-------|-----------|
| — | — | — |

---

## Status Legend

| Status | Meaning |
|--------|---------|
| NOT STARTED | Row created; no artifacts yet linked |
| IN PROGRESS | Some columns populated; not fully verified |
| VERIFIED | All columns populated; Deployment Verified has a production entry |
| DEPRECATED | User Story removed or superseded; row retained for history |

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| v1 | YYYY-MM-DD | Initial matrix created |
