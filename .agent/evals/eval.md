# eval.md — MTS Project-Level Evaluation Framework

**Scope:** All features and workflows within the MTS AI-native system
**Version:** v1
**Status:** Active

---

## 1. Purpose

This document defines the global evaluation framework for the MTS AI-native system.

It establishes:
- Evaluation dimensions
- Scoring standards
- Acceptance criteria
- Cross-feature consistency rules

All feature-level evaluations MUST align with this framework.

---

## 2. Evaluation Dimensions

All outputs are evaluated across the following dimensions:

### 2.1 Functional Correctness
- Output is logically and mathematically correct
- No incorrect answers
- No invalid assumptions

### 2.2 Specification Compliance
- Output strictly follows the feature spec
- No missing required elements
- No unauthorized deviations

### 2.3 Source Fidelity *(when applicable)*
- Output is grounded in source
- No hallucinated concepts
- All content traceable to source

### 2.4 Structural Quality
- Proper organization
- Logical sequencing
- Clean hierarchy (sections, numbering)

### 2.5 Pedagogical Quality
- Appropriate for grade level
- Clear progression (easy → hard)
- Concept reinforcement
- Meaningful variety

### 2.6 Clarity & Usability
- Instructions are clear
- Questions are unambiguous
- Student-friendly format
- Teacher usability

### 2.7 Formatting Quality
- Clean layout
- Print-ready
- Consistent spacing and alignment

### 2.8 Productivity / Efficiency
- Output generated with minimal rework
- Low iteration cycles
- High first-pass quality

### 2.9 Time Performance
- Time taken per run is reasonable
- No excessive delays in pipeline stages

### 2.10 Traceability
- All outputs are reproducible
- Proper run artifacts exist
- Clear lineage from input → output

---

## 3. Scoring Model

Each dimension is scored:

| Score | Meaning |
|-------|---------|
| 5 | Excellent |
| 4 | Good |
| 3 | Acceptable |
| 2 | Weak |
| 1 | Fail |

---

## 4. Pass / Fail Criteria

A run is considered **PASS** only if:
- Functional Correctness = **5**
- Specification Compliance ≥ **4**
- Source Fidelity (if applicable) ≥ **4**
- No dimension < **3**

---

## 5. Critical Failure Conditions

**Immediate FAIL if:**
- Any incorrect answer
- Any hallucinated concept (source-based workflows)
- Missing required outputs
- Broken structure (unusable worksheet)

---

## 6. Evaluation Layers

### 6.1 Feature-Level Eval
Defined in:
```
.agent/evals/<feature>/<feature>-eval.md
```

### 6.2 Run-Level Eval
Each run MUST produce:
- `eval-summary.md`
- `trace.md`

---

## 7. Run Trace Summary Structure

Each run under `.agent/evals/runs/<feature>/<run-id>/` must include:

| File | Purpose |
|------|---------|
| `request.json` | Normalized input |
| `source-extract.md` | Cleaned source |
| `concept-map.md` | Concepts identified |
| `plan.md` | Generation plan |
| `worksheet-draft.md` | First draft output |
| `answer-key-draft.md` | Draft answer key |
| `qa-report.md` | Quality check results |
| `eval-summary.md` | Scored evaluation |
| `trace.md` | Step-by-step execution log |
| `worksheet-final.md` | Final approved output |

---

## 8. Continuous Improvement Loop

Each failed or weak run must:
1. Identify failure dimension(s)
2. Trace root cause (agent / spec / workflow)
3. Update: spec OR eval OR agent behavior

---

## 9. Guiding Principles

1. Correctness is non-negotiable
2. Spec adherence over creativity
3. Traceability over convenience
4. First-pass quality over iterative fixing
5. Measurable quality over subjective judgment
