# MTS Harness

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

The harness is the **quality intelligence infrastructure** of the MTS system.

It provides controlled environments for:
* Running evals
* Capturing execution traces
* Regression testing
* Benchmarking
* Diagnosing and replaying failures
* Validating repairs

> "Harnesses should evolve toward self-improving cognitive quality systems."
> — Holistic AI-Native Cognitive Architecture

---

## 2. Structure

```text
harness/
├── README.md                  ← this file
├── evals/                     ← eval run artifacts (linked from .agent/evals/)
├── traces/                    ← execution traces for diagnosis and replay
├── regression/                ← regression test cases and results
├── benchmarks/                ← performance and quality benchmarks
├── failures/                  ← failure case archive (linked from .agent/bugs/)
├── replay/                    ← scenarios designed for defect replay
└── repair/                    ← repair validation runs
```

---

## 3. Harness Layers

### 3.1 Evals

Feature-level and project-level evaluation runs.

* Project-level eval: `.agent/evals/eval.md`
* Feature evals: `.agent/evals/<feature>/`
* Run artifacts: `harness/traces/` (capture full execution context)

### 3.2 Traces

Execution traces capture:
* What input was given
* What tool calls were made
* What decisions the agent made (and why)
* What output was produced
* What eval score was assigned

Traces enable:
* Post-mortem diagnosis of failures
* Replay of defect scenarios
* Evidence for prompt optimization

### 3.3 Regression

Regression cases are known-good scenarios that must continue to pass after any change.

Structure per regression case:
```text
regression/
└── <case-id>/
    ├── input/           ← input artifacts
    ├── expected/        ← expected output or eval thresholds
    └── result/          ← most recent run result
```

**Regression gate:** No feature release without a clean regression run.

### 3.4 Benchmarks

Benchmarks track system performance across runs:
* Block detection accuracy (%)
* QA pass rate (%)
* Average eval scores per dimension
* Processing time per page
* Output page reduction ratio

Benchmark baselines are established at feature release and tracked over time.

### 3.5 Failures

The failure archive preserves:
* The input that caused the failure
* The error or incorrect output observed
* The eval report from that run
* The root cause classification

Failure archive maps to the repair pipeline in `repair/`.

**Failure Classes (from architecture):**
| Class | Example |
|-------|---------|
| Hallucination | Content invented beyond source |
| Detection Failure | Block count near-zero unexpectedly |
| Spec Deviation | Output missing required element |
| Grade Misalignment | Content level wrong for declared grade |
| QA Bypass | Pipeline proceeded past FAIL |
| Tool Failure | PDF library error; image corruption |
| Prompt Drift | Agent behavior deviated from expected |

### 3.6 Replay

Replay cases are constructed from failures to enable:
* Deterministic reproduction of the defect
* Verification that a repair resolves it
* Regression protection against re-introduction

### 3.7 Repair

Repair validation runs verify that:
* A proposed fix resolves the failure in the replay case
* The fix does not introduce regressions in existing cases
* The repaired behavior matches the spec

**Every repair MUST:**
1. Reference the failure case it addresses
2. Describe the root cause and the fix
3. Include a replay run showing the defect
4. Include a repair validation run showing the fix

---

## 4. Relationship to Existing Infrastructure

| Existing Directory | Harness Mapping |
|-------------------|----------------|
| `.agent/evals/` | `harness/evals/` (same — evals feed the harness) |
| `.agent/bugs/` | `harness/failures/` (bugs are failure cases) |
| `.agent/improvements/` | `harness/repair/` (improvements are repair candidates) |
| `.agent/evals/runs/` | `harness/traces/` (run artifacts become traces) |

---

## 5. Harness Evolution Goals

Phase 1 (current): Manual eval runs + structured failure archive
Phase 2: Automated regression runs triggered on code changes
Phase 3: Automated defect classification + repair proposal generation
Phase 4: Harness evolves toward autonomous quality improvement
