# standards.md — MTS Engineering & Content Standards

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active
**Authority:** Below constitution.md; applies to all agents and code.

---

## 1. Purpose

This document defines the quality and engineering standards
for all content, code, artifacts, and processes produced within the MTS system.

When specifications are silent on a topic, these standards fill the gap.

---

## 2. Content Standards

### 2.1 Grade Alignment

| Grade Band | Language Standard | Cognitive Load |
|-----------|------------------|---------------|
| Grades 2–4 | Simple sentences, concrete terms | Single-step, foundational |
| Grades 5–7 | Clear, structured, slightly abstract | Multi-step, pattern recognition |
| Grades 8–10 | Academic, precise, SAT-ready | Complex, multi-concept |

* All vocabulary must be appropriate for the declared grade level.
* Instructions use active voice.
* Quantities and units are consistent within a worksheet.

### 2.2 Mathematical Content

* All mathematical notation must be unambiguous.
* Answer keys must show solution steps, not just final answers.
* Fractions are formatted consistently (never mixed between styles in one document).
* Word problems use real-world context appropriate for the grade.

### 2.3 ELA Content

* Passages are grade-level appropriate (Lexile-aware when possible).
* Questions target a range: literal recall → inferential → evaluative.
* Grammar and usage questions align to grade-level standards (NC Common Core).

### 2.4 Visual Layout

* Questions are numbered sequentially (1, 2, 3...) with no gaps.
* White space is consistent and intentional — not padded.
* Diagrams and graphs are included only when sourced; never invented.
* Headers, labels, and instructions are visually distinct from content.

---

## 3. Code Standards

### 3.1 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `block_detector.py` |
| Classes | PascalCase | `BlockDetector` |
| Functions | snake_case | `extract_blocks()` |
| Constants | UPPER_SNAKE | `MAX_PAGES` |
| Variables | snake_case | `page_count` |

### 3.2 Commenting Standards

Every MTS class must have a docstring:

```python
class BlockDetector:
    """
    Detects question blocks in a source PDF page.

    Uses PyMuPDF bounding box analysis to identify
    discrete question regions for downstream extraction.
    """
```

Every non-trivial function must have a docstring:

```python
def extract_blocks(page, scale_factor: float) -> list[Block]:
    """
    Extract question blocks from a single PDF page.

    Args:
        page: PyMuPDF page object.
        scale_factor: Target block width as fraction of content width.

    Returns:
        List of Block objects with bounding boxes and metadata.

    Raises:
        ValueError: If scale_factor is outside (0, 1].
    """
```

### 3.3 Error Handling

* Never silently swallow exceptions.
* Every caught exception must either re-raise or log with context.
* User-visible errors must include a remediation hint.
* Pipeline failures must produce a run artifact before halting.

### 3.4 Testing Standards

* Every non-trivial function has a corresponding unit test.
* Tests live in `tests/` mirroring the `src/` structure.
* Test names follow: `test_<function>_<scenario>`.
* Tests must be deterministic — no random seeds without fixture.
* PDF-dependent tests use fixture files checked into the repo.

### 3.5 Dependency Management

* All dependencies declared in `requirements.txt`.
* No unpinned dependencies in production.
* New dependencies require documented justification in the PR or decision log.

---

## 4. Artifact Standards

Every pipeline run MUST produce:

| Artifact | Purpose |
|---------|---------|
| `run_log.md` | What ran, when, inputs, outputs, status |
| `eval_report.md` | Scores and findings against eval dimensions |
| `output/` | Final deliverable files |

Artifact filenames use descriptive kebab-case:
`worksheet-grade-5-math-fractions-v1.pdf`

---

## 5. Spec Standards

Feature specs must include:

* Purpose and scope
* Input contract (what goes in)
* Output contract (what comes out)
* Acceptance criteria
* Edge cases and failure modes
* Version history

Specs are authoritative. Code and agents defer to specs.
Specs are updated via deliberate versioning — not silently.

---

## 6. Eval Standards

Every feature must have:

* A feature-level eval aligned to `evals/eval.md`
* Acceptance thresholds for each dimension
* At least one regression eval run before feature release

Eval scores are not suggestions — they are gates.

---

## 7. Communication Standards

All internal documents (specs, evals, decisions) use:

* Markdown with clear heading hierarchy (H1 → H2 → H3)
* Tables for comparative information
* Code blocks for commands and code snippets
* Status badges: `Active`, `Draft`, `Deprecated`, `Archived`

---

## 8. Document Size and Structure Standards

Prefer small, single-purpose, high-signal markdown files.

| Document Type | Target Length |
|--------------|--------------|
| Operational / canonical (agent.md, standards.md, etc.) | 1-3 pages |
| Deeper references (spec, HLD, LLD, PRD) | 3-8 pages |
| Structured reference / index material (traceability, backlog) | as needed |

### 8.1 When a document grows beyond its target range

* **Split by responsibility** - each file owns exactly one concern.
* **Preserve canonical ownership** - the source-of-truth for each topic lives in one file only; other files reference, they do not repeat.
* **Maintain navigational index docs** - every spec folder must have a `README.md` that maps all files and their read order.
* **Avoid duplication across files** - if the same content appears in two files, one of them is wrong.

### 8.2 Split signals

A document should be split when any of these are true:

* It contains two or more distinct responsibilities (e.g., algorithm detail mixed with delivery history).
* A reader of one section never needs the other section.
* A section is updated on a different cadence than the rest of the file.
* The file exceeds the target range and the excess is not index/reference material.
