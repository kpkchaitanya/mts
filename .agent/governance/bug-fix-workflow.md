# bug-fix-workflow.md — MTS Bug Fix Workflow

**Version:** v1  
**Date:** 2026-05-08  
**Status:** Active  
**Authority:** Sits below `agent.md` in the authority chain. Applies to all coding agents.

---

## 1. Purpose

This document defines the required workflow for fixing bugs in the MTS codebase. It prevents the most common failure mode: jumping to code before understanding the problem.

**Every bug fix must begin with classification.** Classification determines which workflow applies. There are no exceptions.

---

## 2. Fix Classification

Before touching any file, state the classification explicitly.

| Class | Criteria | Examples |
|-------|----------|---------|
| **Simple** | Isolated change — 1 to 5 lines, no logic or data-flow change, impact is local and obvious | Wrong default value in config, off-by-one in a constant, missing `None` guard, typo in a string |
| **Moderate** | Logic change contained within a single component — cause is clear, no cross-module impact, fix is non-trivial but the correct approach is unambiguous | Wrong condition in a single function, incorrect scale calculation, missing early-return that causes bad output in one code path |
| **Deep** | Involves logic across multiple components, architecture, or data flow — failure mode is subtle or the correct fix is not immediately obvious | Infinite loop in layout engine, inverted boolean with cascading effect, multi-module data flow bug, classification error affecting multiple pipeline stages |

**When in doubt, go one class higher.**

---

## 3. Simple Fix Workflow

```
1. State classification: Simple
2. State the fix in one sentence
3. Apply the edit
4. VERIFY — run the post-generation QA loop (see Section 9)
```

No POC required. No strategy phase required.

---

## 4. Moderate Fix Workflow

```
1. State classification: Moderate
2. UNDERSTAND  — state the root cause in plain English (1–2 sentences)
3. STRATEGIZE  — state the intended fix and why it is correct
4. IMPLEMENT   — apply the edit
5. VERIFY      — run the post-generation QA loop (see Section 9)
```

POC is optional for Moderate fixes — use judgment. If the fix involves a condition or calculation that could be inverted or mis-scoped, run a POC.

---

## 5. Deep Fix Workflow

```
1. State classification: Deep
2. UNDERSTAND  — read the traceback and relevant code; state the root cause in plain English
3. STRATEGIZE  — state the intended fix and why it is correct before writing any code
4. POC         — write a minimal script (scripts/poc_<issue>.py) that either reproduces 
                 the bug or validates the fix against real input; run it and record output
5. IMPLEMENT   — apply the fix to source files
6. VERIFY      — run the post-generation QA loop (see Section 9)
```

**Never skip to IMPLEMENT without completing UNDERSTAND → STRATEGIZE → POC.**

The POC step exists specifically to catch inverted logic, off-by-one errors, and other cases where the fix looks correct in the abstract but fails in practice.

---

## 5. Common Failure Patterns to Guard Against

| Pattern | Description | Prevention |
|---------|-------------|------------|
| **Inverted fix** | Applying the logical complement of the intended condition (e.g. `not col_blocks` instead of `col_blocks`) | POC step catches this — the wrong condition produces wrong output in the POC run |
| **Symptom fix** | Fixing the error message or stack frame without fixing the root cause | UNDERSTAND phase requires stating root cause, not just identifying the crash site |
| **Scope creep** | Fixing a tangential issue while the root cause goes unaddressed | STRATEGIZE phase requires a single clear fix statement before any edit |
| **Untested path** | Fix works for the test input but fails on other inputs | VERIFY phase requires running the full batch (all 3 grades) not just the file that failed |

---

## 6. Classification Must Be Stated

At the start of every bug fix response, the agent must write:

> **Classification: Simple** — [one-sentence description]

or

> **Classification: Deep** — [one-sentence root cause statement]

If classification is omitted, the fix is non-compliant with this workflow.

---

## 7. POC Script Convention

- File: `scripts/poc_<short_issue_name>.py`
- Must be self-contained and runnable: `python scripts/poc_<name>.py`
- Must print a clear PASS or FAIL result
- Must be committed — POC scripts become regression references
- Record the POC output in the bug detail block in `bugs.md` before implementing the fix

---

## 8. Bug Entry Template Update

The `bugs.md` entry template includes a **Classification** field (see `bugs.md`). It must be filled in before any code is changed.

---

## 9. VERIFY — Post-Generation QA Loop (Required for All Fix Classes)

**VERIFY is not "re-run the script and eyeball the output."** VERIFY means executing the full post-generation QA loop defined in `agent.md §8`.

### What VERIFY requires

```
1. Run compact_runner.py (or orchestrator) on the affected input(s)
   → compact_runner.py runs the programmatic QA checks automatically after each batch
     and prints a QA summary table. Read it.
2. Review the printed QA table for any FAIL
3. For any FAIL:
   a. Assign priority using the scenario-to-priority table in agent.md §8.4
   b. All P1 and P2 failures must be fixed before the fix is considered verified
   c. Apply fix, re-run, re-read the QA table
   d. Maximum 3 iterations (agent.md §8.5)
4. When all P1 and P2 scenarios pass, VERIFY is complete
5. Report the QA table result in the bug entry Fix section
```

### Invocation

The standard VERIFY command is:

```powershell
python scripts/compact_runner.py `
  --inputs `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade3_2023_Released_Test_Questions.pdf" `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf" `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade5_2023_Released_Test_Questions.pdf" `
  --grade 5 --subject Math --columns 2
```

`compact_runner.py` will print the QA summary automatically at the end. The agent reads that output — no separate QA script invocation is needed.

For scenario checks that require manual visual inspection (QA-EXT-03, QA-PACK-05 heuristic positives), open the output PDF and confirm before filing a bug.

---

## 10. Authority

This workflow is enforced by `agent.md` §7.0, §8, and the IMP-019 backlog item. It supersedes any prior implicit "read traceback → edit → rerun" habit.
