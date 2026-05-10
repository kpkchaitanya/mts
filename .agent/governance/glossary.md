# glossary.md — MTS Shared Terminology

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

This glossary defines the shared language used across all MTS governance
documents, specs, agents, and workflows.

Consistent terminology prevents semantic drift — where different parts of the
system use the same word to mean different things.

When in doubt, defer to this glossary.

---

## 2. Domain Terms

### A

**Answer Key**
A companion document to a worksheet containing correct answers and, for math,
step-by-step solution paths. Answer keys are teacher-facing, never student-facing.

**Artifact**
Any file produced by a pipeline run. Includes output PDFs, run logs, eval reports,
intermediate block images, and failure logs.

### B

**Block**
A discrete question region extracted from a source PDF page, represented as a
bounding box and rasterized image. The atomic unit processed by `compact_source`.

**Block Detector**
The pipeline stage that identifies question blocks on source PDF pages using
bounding box analysis.

**Batch**
A group of students attending MTS sessions at the same grade level and time slot.

### C

**compact_source**
The first MTS feature: transforms a source worksheet PDF into a print-efficient
compact PDF by extracting question blocks as images and repacking them.

**Constitution**
`constitution.md` — the governing document that all agents, specs, and workflows
must comply with. It is the highest authority below the soul.

**Content Width**
The usable horizontal width of a PDF page after subtracting margins. Used as the
reference dimension for block scaling.

### D

**Decision Log**
`.agent/memory/decisions.md` — the running record of significant architectural
and design decisions, with rationale and consequences.

### E

**ELA**
English Language Arts. One of MTS's two core instructional subjects.

**Eval**
An evaluation run that scores an output against defined dimensions (correctness,
spec compliance, pedagogical quality, etc.).

**Eval Dimension**
A specific quality axis on which an output is scored (e.g., Functional Correctness,
Source Fidelity, Pedagogical Quality).

### F

**Feature**
A self-contained capability of the MTS system, governed by a spec and implemented
as a pipeline. Examples: `compact_source`, `math_worksheet_generation_from_source`.

**Formatter Agent**
The pipeline stage that applies layout, formatting, and visual polish to
QA-approved content. Has zero content authority.

### G

**Gate**
A required checkpoint in a pipeline where human or automated validation must
occur before the pipeline continues. Gates cannot be silently skipped.

**Golden Sample**
A reference output PDF used as the visual baseline for visual comparison in
`compact_source` runs.

**Grade Alignment**
The requirement that all content — vocabulary, cognitive load, format —
matches the declared grade level of the intended student audience.

### H

**Harness**
The collection of evals, traces, regression tests, and benchmarks that validate
MTS system quality over time. Lives in `.agent/harness/`.

**Human Gate**
A specific gate requiring a human to explicitly confirm before the pipeline
continues. In `compact_source_math`, the human gate fires after block detection.

### I

**Intake Agent**
The first pipeline stage. Validates inputs, confirms spec contract, and prepares
the run context before handing off to downstream stages.

### L

**Learnings Log**
`.agent/memory/learnings.md` — accumulated lessons from eval runs, failures,
and system behavior observations.

**Lexile**
A measure of text complexity. Used informally at MTS to ensure reading passages
and instructions match the cognitive and reading level of the grade.

### M

**MTS**
Masters Tuition Services LLC — the organization this system serves.

### O

**Ontology**
The structured definition of concepts, relationships, and constraints in the MTS
domain. The semantic backbone of the system. Lives in `.agent/ontology/`.

**Orchestrator**
`src/orchestrator.py` — the entry point that routes commands to the appropriate
feature pipeline.

### P

**Passage**
In ELA contexts, a reading excerpt presented to students as the basis for
comprehension questions.

**PDF Packer**
The pipeline stage that assembles extracted block images into a final output PDF.

**Pipeline**
The end-to-end sequence of stages that transforms an input into a final output
artifact for a given feature.

**PRD**
Product Requirements Document. Defines business goals, user needs, and success
criteria for a feature. Lives in `.agent/product/`.

### Q

**QA Agent**
The pipeline stage responsible for evaluating outputs against the feature spec
and eval framework. Has absolute veto power.

**QA Gate**
The mandatory QA evaluation checkpoint. No output proceeds past a QA FAIL.

### R

**Regression Eval**
An eval run that verifies the system still passes known-good scenarios after
a change. Regression evals live in `.agent/harness/regression/`.

**Run Artifact**
The collection of files produced by a single pipeline execution.
See *Artifact*.

**Run Log**
`run_log.md` — the artifact recording what ran, when, with what inputs, and
what outputs were produced.

### S

**Scale Factor**
In `compact_source`, the target block width expressed as a percentage of content
width. Controls how large blocks appear in the output PDF.

**Skill**
A reusable cognitive capability that agents can invoke. Examples: `summarize`,
`extract_math_blocks`, `generate_worksheet`. Lives in `.agent/skills/`.

**Spec**
A feature specification document. The authoritative contract describing a
feature's behavior, inputs, outputs, and acceptance criteria.

**Soul**
`soul.md` — the foundational philosophy and identity of MTS. The highest layer
of the authority chain.

**Source PDF**
The input worksheet PDF provided by the teacher. The pipeline transforms but
never modifies the source.

**Stage**
A discrete step in a pipeline, performed by a specific agent role.

### T

**Trace**
A detailed log of an agent's execution: inputs received, tools called, decisions
made, outputs produced. Enables diagnosis of failures.

**TDD**
Test-Driven Development. The practice of writing unit tests before implementing
the code they cover. Mandatory for non-trivial MTS code.

### W

**Workflow**
A document defining the ordered stages, handoff contracts, and decision logic
for a pipeline. Lives in `.agent/workflows/`.

**Worksheet**
A student-facing document containing practice problems. The primary output artifact
of most MTS generative features.

---

## 3. Status Values

Used across specs, evals, and documents:

| Status | Meaning |
|--------|---------|
| `Active` | Current and enforced |
| `Draft` | Under development; not yet authoritative |
| `Deprecated` | Superseded; do not reference in new work |
| `Archived` | Historical record only |

---

## 4. Eval Score Labels

| Label | Meaning |
|-------|---------|
| `PASS` | Meets acceptance threshold |
| `PASS_WITH_NOTES` | Passes but has notable observations |
| `REVIEW` | Borderline; requires human judgment |
| `FAIL` | Does not meet threshold; pipeline halts |
| `WARNING` | Anomaly detected; does not halt but is logged |
