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

1. **Honor the authority chain.** Soul → Constitution → agent.md → Spec → Workflow → Agent → Output. Higher layers override lower layers.
2. **Never bypass QA.** No output proceeds past a QA failure.
3. **Every run produces artifacts.** Nothing is a black box. If it ran, it left a trace.
4. **Student-first standard.** Any output that would confuse, mislead, or discourage a student fails — regardless of technical correctness.
5. **Ask before assuming.** When the spec is unclear or the input is ambiguous, flag it and request clarification rather than guessing.

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

  Locates the first and last question boundaries in a state exam PDF.
  This is Step 1 of the compact_source pipeline.

  Inputs:  Raw PDF file path
  Outputs: (first_question_location, last_question_location) as named tuples
  """
  ```

---

## 5. Quality Bar

Before any output — code or artifact — is considered complete, the agent must be able to answer YES to all of these:

- [ ] Is this correct?
- [ ] Is this clear to a reader who didn't write it?
- [ ] Is this traceable back to its source or spec?
- [ ] Would this be acceptable to put in front of an MTS student or teacher?
- [ ] Have I followed the commenting and naming standards in this protocol?

If any answer is NO, the output is not complete.

---

## 6. Bug and Improvement Logging (Coding Agent)

### 6.1 When to Log a Bug

Log a bug in `.agent/bugs/bugs.md` when:
- Code produces incorrect output (wrong calculation, broken crop, malformed artifact)
- A run fails or halts due to an unhandled error
- An eval scores any dimension below 3
- A teacher or student reports a quality problem

Do not wait for a second occurrence. Log on first observation.

### 6.2 When to Log an Improvement

Log an improvement in `.agent/improvements/backlog.md` when:
- A repeated pattern of weak-but-passing output suggests a spec gap
- A new requirement emerges from teacher or student feedback
- A pipeline step is identified as inefficient or fragile

### 6.3 What Makes a Good Bug Entry

A bug entry must include enough information to reproduce and diagnose the issue without re-running the system from scratch:

- **Run ID** — the exact run folder where the bug occurred
- **Input** — what was provided to the system
- **Expected output** — what should have happened
- **Actual output** — what actually happened (quote or reference the artifact)
- **Root cause layer** — spec · agent logic · code · external library

### 6.4 Linking Bugs to Specs

Every P1 and P2 bug must result in one of:
- A spec update (if the spec was ambiguous or missing a constraint)
- A code fix (if the logic was wrong)
- An eval update (if the eval failed to catch this class of error)

The bug entry must reference what was updated and where.

### 6.5 Bug Lifecycle — Who Can Close a Bug

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
