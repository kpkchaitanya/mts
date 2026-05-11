# agent.md — MTS Agent Operating Protocol

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active
**Authority:** Sits between `constitution.md` and `spec` in the authority chain.

---

## 1. Purpose

This document is the **operating protocol** for all agents that work within the MTS system.

It applies to two categories of agents:

| Agent Type | Examples |
|------------|---------|
| **Pipeline agents** | intake-agent, concept-mapper-agent, qa-agent, formatter-agent |
| **Coding agents** | Claude Code, any AI coding assistant generating Python or other code for MTS |

Both categories must honor this protocol. No exceptions.

---

## 2. Universal Rules (All Agents)

These rules apply regardless of agent type:

1. **Honor the authority chain.** Soul → Constitution → PM Framework → agent.md → Spec → Workflow → Agent → Output. Higher layers override lower layers.
2. **Product intent is governed by the PM Framework.** When evaluating whether a spec is well-formed, whether a user story is correctly decomposed, or whether requirements are clear, consult `.agent/governance/architecture/product-management/holistic-ai-product-management-framework.md`. This is the single source of truth for product management questions. A spec that violates the PM Framework must be flagged before implementation begins.
2. **Never bypass QA.** No output proceeds past a QA failure.
3. **Every run produces artifacts.** Nothing is a black box. If it ran, it left a trace.
4. **Student-first standard.** Any output that would confuse, mislead, or discourage a student fails — regardless of technical correctness.
5. **Ask before assuming.** When the spec is unclear or the input is ambiguous, flag it and request clarification rather than guessing.
6. **Human gate after block detection.** Every `compact_source_math` run MUST pause after Stage 2 (block detection) to allow a human operator to validate the detected question count before extraction begins. A count that is suspiciously low (< 3 blocks, or < 0.5 blocks per source page) MUST trigger a visible `WARNING` message regardless of whether the gate is bypassed. The gate MAY be bypassed only when `--yes` is explicitly passed (batch/scripted runs) or when stdin is non-interactive. No pipeline may silently extract and pack a near-empty block set.

---

## 3. Pipeline Agent Protocol

### 3.1 Before Starting Any Task

- Read the feature spec in full before acting.
- Read the workflow to understand your position in the pipeline and your handoff contract.
- Confirm your input artifact exists and is complete before beginning.

### 3.2 Artifact Handoff Rules

- **Never skip** an intermediate artifact. Each artifact is a checkpoint.
- **Never modify** an artifact produced by a prior agent. You receive it as read-only input.
- **Always write** your output artifact before signaling completion.
- Artifact filenames and structures are defined in the spec. Do not deviate.

### 3.3 Loopback Behavior

- If QA fails, the qa-agent returns the artifact to the responsible upstream agent with a specific failure reason.
- **Maximum 2 retry loops** per run. On the third failure, escalate to a human reviewer — do not loop again.
- On loopback, the upstream agent receives the qa-report.md and addresses only the flagged issues. It does not regenerate everything.

### 3.4 QA Veto

- qa-agent has absolute veto power. Its FAIL verdict stops the pipeline.
- No other agent may override a QA failure.
- The formatter-agent formats only QA-approved content. It has zero content authority.

### 3.5 Anti-Hallucination Rules

- Never introduce concepts, facts, or information not present in the source document.
- When in doubt, omit rather than invent.
- Every concept in a concept map must have a source reference. If a reference cannot be provided, the concept must be removed.
- If source material is ambiguous or insufficient, flag it in the artifact and halt — do not proceed with assumptions.

---

## 4. Coding Agent Protocol

### 4.1 Code Commenting Standards

These standards are non-negotiable. Every piece of code produced for MTS must follow them.

#### Classes
Every class must have a docstring block immediately after the class declaration:
```python
class BoundaryDetector:
    """
    Detects the first and last question boundaries in a state exam PDF.

    Responsibilities:
    - Locate Q1 using text markers (e.g., "1.", "Question 1")
    - Locate the last question using reverse scan
    - Handle edge cases: ambiguous markers, multi-page questions

    Does NOT strip content — that is the responsibility of Stripper.
    """
```

#### Methods and Functions
Every method and function must have a docstring:
```python
def detect_first_question(self, page_texts: list[str]) -> tuple[int, int]:
    """
    Scans page text to find the position of the first question.

    Args:
        page_texts: List of text content per page (index = page number).

    Returns:
        Tuple of (page_number, line_number) for the first question.

    Raises:
        BoundaryNotFoundError: If no question marker is detected in the document.
    """
```

#### Loops
Every non-trivial loop must have a comment explaining what is being iterated and why:
```python
# Scan each page in reverse to find the last question marker
# Reverse scan is more efficient since last question is near end of document
for page_number in reversed(range(len(page_texts))):
    ...
```

#### Non-Obvious Blocks
Any block of logic that is not immediately self-evident must have an inline comment:
```python
# Skip pages before page 2 — state exams always have at least one cover page
# This avoids false positives from numbered items in instructions
if page_number < 2:
    continue
```

### 4.2 Readability Standards

- **Meaningful names.** Variable and function names must express intent. No single-letter variables outside of loop counters (`i`, `j`). No abbreviations that obscure meaning (`pg` → `page_number`, `q` → `question`).
- **Single responsibility.** Each function does one thing. If you can describe a function's purpose and need to use the word "and", split it.
- **Function length.** Target under 30 lines per function. If a function grows beyond this, extract the sub-logic into a named helper.
- **No magic numbers.** Replace all numeric literals with named constants in `config.py`:
  ```python
  # Bad
  if page_number < 2:

  # Good
  if page_number < MIN_CONTENT_PAGE:
  ```

### 4.3 Maintainability Standards

- **No duplicate logic.** If the same logic appears in two places, extract it to `utils/`. The second time you write something similar, extract it.
- **No hardcoded paths or API keys.** All configuration goes through environment variables loaded via `python-dotenv`. The `.env.example` file documents every required variable.
- **No hardcoded model names in business logic.** Model identifiers belong in `config.py`.
- **Fail loudly with context.** When raising exceptions, include enough information to diagnose the failure without running the code again:
  ```python
  raise BoundaryNotFoundError(
      f"No question marker found in '{pdf_path}'. "
      f"Scanned {len(page_texts)} pages. Check if this is a valid exam PDF."
  )
  ```
- **No silent failures.** Never catch an exception and pass. Either handle it or re-raise it.

### 4.4 File and Module Standards

- One primary class or responsibility per file.
- Imports ordered: standard library → third-party → internal (separated by blank lines).
- Every module has a module-level docstring explaining its role in the pipeline:
  ```python
  """
  boundary_detector.py

  Locates the first and last question boundaries in a source exam PDF.
  This is Step 1 of the block detection pipeline.

  Inputs:  Raw PDF file path
  Outputs: (first_question_location, last_question_location) as named tuples
  """
  ```

---

## 5. Hierarchical Change Protocol (Coding Agent)

Every non-trivial code change — bug fix, enhancement, or refactor — MUST follow this
four-stage sequence. **No stage may be skipped. A human gate separates each stage.**

```
INTENT → DESIGN → IMPLEMENTATION → OBSERVATION & VALIDATION
   ↑         ↑            ↑                    ↑
 human     human        human               human
  gate      gate         gate                gate
```

### Mapping to the AI-First SDLC Loop

This protocol is how a single change moves through the MTS SDLC. See `program.md §AI-First SDLC`
for the full loop definition. The stage mapping is:

```
SDLC:    Observe/Heal  →  Spec     →   Build    →   Run → Eval → Learn
         (trigger)        (design)     (code)        (validate)
Protocol: Stage 1      →  Stage 2  →   Stage 3  →   Stage 4
```

A change is triggered by the **Observe** or **Heal** phase (a defect found in a run, or
an eval score below threshold). It feeds back into **Spec** before any **Build** work
begins. The cycle closes when **Learn** records the outcome in `learnings.md`.

### Extended Authority Chain (from program.md)

```
Soul → Constitution → PRD → Spec → Eval → Build → Run → Observe → Learn → Heal
```

- A spec cannot contradict the PRD. A build cannot contradict the spec.
- An eval failure blocks a run from being marked PASS.
- P1/P2 bugs block new feature work until resolved.
- Only humans close bugs — agents may only set status to `fix-applied`.

---

### Stage 1 — Intent  *(maps to: Observe / Heal → trigger)*

The agent states:
- **What** is wrong or missing (symptom with evidence — screenshot, log, artifact path,
  eval dimension that failed).
- **Why** it matters (user or student impact).
- **Scope** — what is in and explicitly out of scope.

**Artifact actions:**
- Bug fix → open (or reference an existing) entry in `.agent/bugs/bugs.md` with status `open`.
- Enhancement / tech debt → open (or reference) an entry in `.agent/improvements/backlog.md`.
- Every change must trace to one of these two files before design starts.

> **Human gate:** human confirms intent is correctly understood.

---

### Stage 2 — Design  *(maps to: Spec)*

Before writing any code, the agent produces:
- **Root cause** — the exact file(s), class(es), method(s), and logic responsible.
- **Proposed change** — what changes, where, and why.
- **Decision tree / logic** — all branching behavior documented explicitly.
- **Interfaces touched** — classes, methods, constants, and files that change.
- **Interface stability** — what does NOT change (callers, data classes, public contracts).
- **Harness impact** — which harness layers (see `program.md §Harness Engineering`) are
  affected: tests that must be added/updated, eval dimensions that this fix addresses,
  logging or telemetry changes needed.
- **Test plan** — specific unit and integration cases with inputs and expected outputs,
  mapped to the harness test suite (`pytest`).

**Spec artifact actions — update in this authority order:**

| File | Role | When to update |
|---|---|---|
| `<feature>-prd.md` | Product requirements and user stories | Only if a product requirement or user story changes |
| `<feature>-spec.md` | Behavioral contract (inputs, outputs, stage behavior, error handling) | If the contract governing the affected behavior changes |
| `<feature>-design.md` | Living implementation record | Always — the design section for the affected stage must reflect the approved new logic |

The agent drafts the proposed diffs to these files as part of the design presentation.
No file is updated until the human approves the design.

> **Human gate:** human approves the design, spec diffs, and test plan before any code is written.
> Clarifying questions → revise design and re-present. Do NOT write code.

---

### Stage 3 — Implementation  *(maps to: Build)*

- Implement exactly what was approved in Stage 2. No scope creep.
- Follow all coding standards in Section 4.
- Add or update tests per the approved test plan — harness coverage must not regress.

**Doc-sync is non-negotiable and part of implementation — not a follow-up step:**
The spec and design documents are the authoritative record of how the system works.
Code that is not reflected in the docs is incomplete, regardless of whether it runs correctly.
The agent MUST update these files in the same step as the code change, in authority order:

| File | Rule |
|---|---|
| `<feature>-design.md` | **Always update.** Every code change to pipeline logic MUST be reflected in the affected stage's section and flowchart. If the design doc does not match the code, the implementation is not done. |
| `<feature>-spec.md` | Update if the behavioral contract changed (inputs, outputs, stage behavior, error handling, testable claims). |
| `<feature>-prd.md` | Update only if a product requirement or user story changed. |

The agent does not wait to be asked. Updating the docs is as much a deliverable as the code itself.

- Update `.agent/bugs/bugs.md` or `.agent/improvements/backlog.md`: advance status to `fix-applied`.
- If a significant architectural or approach decision was made, record it in
  `.agent/memory/decisions.md`.
- Leave a verification instruction in the bug/improvement entry:
  - Exact command to run.
  - Which eval quality dimensions (from `program.md §Eval Quality Dimensions`) to check.
  - Expected output artifacts in `.agent/evals/runs/<feature>/<run-id>/`.

> **Human gate:** human reviews all changes (code + updated `.md` files) before running anything.

---

### Stage 4 — Observation & Validation  *(maps to: Run → Eval → Learn)*

- Human runs the pipeline against a real input; output artifacts land in
  `.agent/evals/runs/<feature>/<run-id>/` (exact files defined in the feature spec).
- Validation is evaluated against the **Eval Quality Dimensions** in `program.md` — not
  just visual inspection. The agent must call out which dimensions are addressed by this fix.
- The coding agent may NOT declare the bug resolved.
- Only after the human confirms the output is correct:
  - Human advances status `fix-applied` → `resolved` in `bugs.md` (human action only).
  - Agent adds an entry to `.agent/memory/learnings.md`: what was learned, what was
    updated, linked to run ID and bug/improvement ID, which eval dimension improved.
  - If the eval in `.agent/evals/<feature>/` needs updating to catch this class of defect
    in future, agent drafts that update for human review.

> **Human gate:** human confirms resolution. Agent records in `learnings.md`.

---

## 8. Post-Generation QA Loop (Coding Agent — compact_source_math)

After every generation run — single file or batch — the coding agent **must** execute the QA scenarios defined in `.agent/specs/compact_source/qa-scenarios.md` before reporting the run complete. This is not optional.

### 8.1 When the Loop Runs

The post-generation QA loop is triggered after:
- Any `compact_runner.py` batch invocation — **`compact_runner.py` runs the programmatic QA checks automatically and prints the QA table; the agent reads this output**
- Any single-file `orchestrator` run
- Any code change to `block_detector.py`, `block_extractor.py`, `pdf_packer.py`, or `reporter.py`

The VERIFY step in `bug-fix-workflow.md` (all fix classes) requires completing this loop. See `bug-fix-workflow.md §9` for the standard invocation command.

### 8.2 Loop Steps

```
1. Run generation
2. Execute all QA scenarios from qa-scenarios.md
3. Collect PASS / FAIL for each scenario
4. If all PASS → generation is complete. Report results and stop.
5. If any FAIL:
   a. Triage all failures (see §8.3)
   b. Fix highest-priority defect first (apply fix classification from §7.0)
   c. Re-run generation on the affected input(s)
   d. Re-run all QA scenarios
   e. Repeat from step 3 — maximum 3 fix iterations
6. If failures persist after 3 iterations → escalate to human. Do not loop again.
```

### 8.3 Defect Triage — Priority Assignment

Assign priority before fixing. Do not start coding until priority is assigned.

| Priority | Condition | Action |
|----------|-----------|--------|
| **P1 — Blocker** | Output is blank, truncated, or missing questions; text visibly cut off; infinite loop; run crashes | Fix immediately before anything else. Do not deliver the output. |
| **P2 — Major** | Wrong question count (outside DET tolerance); image resolution below threshold; page reduction implausible; split block detected | Fix before delivery. Output may be inspected but is not deliverable. |
| **P3 — Minor** | Run folder has unexpected files; log section missing; runtime slightly over threshold but run completes | Fix in the same session if fast. Deliver output with a logged note. |
| **P4 — Observation** | Heuristic check flagged a possible issue but visual inspection confirms it is acceptable | Log in `bugs.md` as `open` with low priority. Do not block delivery. |

**P1 and P2 failures block delivery.** The agent must not hand off or present output to the user until all P1 and P2 scenarios pass.

### 8.4 Scenario-to-Priority Mapping

| Scenario | Default Priority |
|----------|------------------|
| QA-DET-01 / 02 / 03 (block count) | P1 if count = 0; P2 if outside tolerance |
| QA-DET-04 (no vision fallback) | P3 |
| QA-EXT-01 (extracted = detected) | P2 |
| QA-EXT-02 (image resolution) | P2 |
| QA-EXT-03 (no text cut off) | P1 if visually confirmed; P4 if heuristic only |
| QA-PACK-01 (no infinite loop) | P1 |
| QA-PACK-02 (2-col < 1-col pages) | P2 |
| QA-PACK-03 (no blank output) | P1 |
| QA-PACK-04 (clean run folder) | P3 |
| QA-PACK-05 (no split blocks) | P2 if confirmed; P4 if heuristic only |
| QA-REP-01 (Result: PASS all files) | P1 |
| QA-REP-02 (page reduction plausible) | P2 |
| QA-REP-03 (run.log complete) | P3 |
| QA-E2E-01 (full batch) | P1 if any sub-check is P1; otherwise P2 |

### 8.5 Fix Iteration Budget

- **3 iterations maximum.** If the same scenario fails on the third re-run, stop, log the bug as `in-progress`, and escalate to the human with a clear description of what was tried and why it did not resolve.
- Each iteration must fix at least one failing scenario. If no progress is made after an iteration, escalate immediately — do not spend iterations on approaches that are not converging.
- Re-running all QA scenarios after each fix (not just the one that failed) is required. A fix must not introduce new failures.

### 8.6 Reporting After the Loop

When the loop completes (all PASS or escalation), report to the human:

1. **QA table** — all scenario IDs with PASS / FAIL
2. **Run folder** path
3. **Fixes applied** (if any) — scenario ID → root cause → fix summary
4. **Open issues** (P3 / P4) — logged but not blocking
5. **Delivery verdict** — `DELIVERABLE` (all P1/P2 pass) or `ESCALATE` (P1/P2 open after 3 iterations)

---

### Authority chain for this protocol

```
soul.md → constitution.md → program.md → agent.md (this doc) → spec → workflow → agent → output
```

Within Stage 2, the spec artifact authority chain is:
```
<feature>-prd.md → <feature>-spec.md → <feature>-design.md
```
Lower files must never contradict higher files. If they conflict, the higher file wins
and the agent must resolve the contradiction before proceeding.

### Violations

If a coding agent writes code before receiving design approval, edits a spec without
human approval, or advances a stage without a human gate — that is a **protocol
violation**. The human may reject the change and require a restart from Stage 1.

---

## 6. Quality Bar  

Before any output — code or artifact — is considered complete, the agent must be able to answer YES to all of these:

- [ ] Is this correct?
- [ ] Is this clear to a reader who didn't write it?
- [ ] Is this traceable back to its source or spec?
- [ ] Would this be acceptable to put in front of an MTS student or teacher?
- [ ] Have I followed the commenting and naming standards in this protocol?

If any answer is NO, the output is not complete.

---

## 7. Bug and Improvement Logging (Coding Agent)

### 7.0 Fix Classification (Required First Step)

Before fixing any bug, the coding agent must classify it and state the classification explicitly. See **`.agent/governance/bug-fix-workflow.md`** for the full workflow.

| Class | When | Required steps |
|-------|------|---------------|
| **Simple** | Isolated, 1–5 lines, no logic change | State → Edit → Verify |
| **Moderate** | Logic change in one component, cause is clear | Understand → Strategize → Implement → Verify (POC optional) |
| **Deep** | Logic, control flow, architecture, or subtle failure mode | Understand → Strategize → POC → Implement → Verify |

**When in doubt, go one class higher.** Never skip to code on a Moderate or Deep fix.

### 7.1 When to Log a Bug

Log a bug in `.agent/bugs/bugs.md` when:
- Code produces incorrect output (wrong calculation, broken crop, malformed artifact)
- A run fails or halts due to an unhandled error
- An eval scores any dimension below 3
- A teacher or student reports a quality problem

Do not wait for a second occurrence. Log on first observation.

### 7.2 When to Log an Improvement

Log an improvement in `.agent/improvements/backlog.md` when:
- A repeated pattern of weak-but-passing output suggests a spec gap
- A new requirement emerges from teacher or student feedback
- A pipeline step is identified as inefficient or fragile

### 7.3 What Makes a Good Bug Entry

A bug entry must include enough information to reproduce and diagnose the issue without re-running the system from scratch:

- **Run ID** — the exact run folder where the bug occurred
- **Input** — what was provided to the system
- **Expected output** — what should have happened
- **Actual output** — what actually happened (quote or reference the artifact)
- **Root cause layer** — spec · agent logic · code · external library

### 7.4 Linking Bugs to Specs

Every P1 and P2 bug must result in one of:
- A spec update (if the spec was ambiguous or missing a constraint)
- A code fix (if the logic was wrong)
- An eval update (if the eval failed to catch this class of error)

The bug entry must reference what was updated and where.

### 7.5 Bug Lifecycle — Who Can Close a Bug

**A coding agent may NEVER mark a bug as `resolved`.**

The lifecycle is:

| Transition | Who can do it |
|------------|---------------|
| `open` → `in-progress` | Coding agent (when starting the fix) |
| `in-progress` → `fix-applied` | Coding agent (when the fix is committed) |
| `fix-applied` → `resolved` | **Human only** — after manually running the pipeline and confirming the output is correct |
| Any status → `wont-fix` | **Human only** |

**Rationale:** A coding agent cannot observe the actual rendered output. Only the human who reported the bug can confirm that the visual result — the PDF, the worksheet, the artifact — matches what was expected. Code changes alone do not constitute verification.

When a bug is marked `fix-applied`, the coding agent must leave a clear verification instruction in the bug's Fix section so the human knows exactly what to run and what to look for.
