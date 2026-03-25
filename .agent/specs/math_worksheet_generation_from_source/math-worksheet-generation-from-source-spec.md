# math-worksheet-generation-from-source-spec.md

**Feature Name:** math_worksheet_generation_from_source
**Version:** v6
**Status:** Active

---

## 1. Purpose

The `math_worksheet_generation_from_source` feature generates Mathematics worksheets strictly derived from a provided source document, ensuring:

- 100% mathematical correctness
- Full alignment with source content
- Pedagogically structured progression
- Print-ready usability

This system performs **controlled transformation**, not free-form generation.

---

## 2. Core Principle

```
Source → Concepts → Questions → Answers → Validation
```

The system MUST NOT skip the concept extraction step.

---

## 3. Transformation Modes

This feature supports two transformation modes. Each mode has its own input, pipeline, and output contract.

| Mode | Input | Output | Use Case |
|------|-------|--------|----------|
| `compact_source` | Source worksheet PDF | Compacted print-ready output | Minimize pages for printing |
| `generate_worksheet` | Source document + request parameters | MTS worksheet + answer key | Classroom worksheet creation |

Sections 3A–3B define each mode. Sections 4–18 apply to `generate_worksheet` unless otherwise noted.

---

## 3A. Mode: `compact_source`

### Purpose

Take a source worksheet PDF and produce a print-ready PDF that minimizes pages while **preserving the original rendering exactly** — all math symbols, graphs, diagrams, and formatting appear identically to the source.

### Design Rationale

> **Why visual block extraction, not text parsing:**
>
> Parsing question content into Markdown and re-rendering it as a PDF introduces **rendering inconsistency** — math symbols (fractions, exponents, radicals), graphs, coordinate planes, and geometric figures cannot be reliably reconstructed from raw text. Any re-rendering pipeline risks broken symbols, wrong layouts, and degraded readability.
>
> The correct approach is **visual cut-and-paste**: treat each question block as a rectangular region of the original rendered PDF, crop it exactly as-is, and pack the cropped blocks tightly into new pages. No content is re-interpreted or re-rendered. The output is pixel-faithful to the source.

### Input Contract

```json
{
  "mode": "compact_source",
  "source_pdf": "file path or binary",
  "grade": "integer",
  "subject": "string",
  "scale_factor": "float (%, default 100)",
  "max_pages": "integer (optional — target total output pages)",
  "columns": "integer (1 or 2, default 1)",
  "question_list": "string (ALL | ranges like '1-10' | comma list '1,3,5')"
}
```

### Packing Parameters

| Parameter | Type | Default | Meaning |
|-----------|------|---------|---------|
| `scale_factor` | float (%) | 100 | Base scale applied to each block relative to its natural fit width for the column. 100 = block fills the column width. Values < 100 shrink blocks. |
| `max_pages` | int | None | Target total output page count. When specified, the system auto-computes a base scale so all blocks fit within this many pages. If both `scale_factor` and `max_pages` are given, the more restrictive (smaller) scale is used. |
| `columns` | 1 or 2 | 1 | Number of layout columns per page. When `columns=2`, each column occupies half the content width minus a small inter-column gap; block scale is recalibrated relative to the column width (not the full page width). |
| `question_list` | string | ALL | Which questions to include. Supports `ALL`, ranges (`1-10`), and comma lists (`1,3,5`). Filtering occurs before packing. |

### Processing Pipeline (Strict)

#### Step 1 — Page Rendering
- Render each source PDF page to a high-resolution image (≥150 DPI) using PyMuPDF.
- Retain page geometry metadata (page width, height, DPI scale factor).

#### Step 2 — Question Block Detection
- Identify question block boundaries using a **hybrid approach**:
  - Extract text with positional coordinates (pdfplumber) to locate question number markers (e.g., "1.", "2.") and answer choice lines (A./B./C./D. or F./G./H./J.).
  - **Top boundary** of each block: the y-coordinate of the question number marker, minus a small upward padding (to capture the number itself). This is the definitive top — the crop starts at the question number, never at the top of the source page.
  - **Bottom boundary** of each block: the y_bottom of the **last answer choice line** (e.g., the "D." or "J." line) detected within the block's span, plus a small downward padding. This is the definitive bottom — NOT the y-coordinate of the next question marker, and never the bottom of the source page.
  - For the last question: bottom boundary = the y_bottom of its last answer choice, plus small padding.
  - **Source page headers and footers are NEVER included in any block crop.** The crop is always from the question number top to the last answer choice bottom, regardless of whether the block spans one or multiple source pages.
   - For the last question: bottom boundary = the y_bottom of its last answer choice, plus small padding.
   - **Source page headers and footers are NEVER included in any block crop.** The crop is always from the question number top to the last answer choice bottom, regardless of whether the block spans one or multiple source pages.
   - If a block spans a page boundary and the tail of one slice contains only empty page-space or a footer, the extractor must trim that trailing area so the combined block image contains no large blank regions or page footers. Crops should be tightened to remove continuous blank rows at slice bottoms while preserving all visual content of the question.
- **Non-question marker filtering:** Number markers (e.g., "1." in a formula chart or numbered instruction list) that have no detectable answer choices (A/B/C/D) AND span more than MAX_QUESTION_SPAN_PAGES pages are discarded as non-question content before building blocks. This prevents intro/reference material from being treated as the first question.
- Deduplication of question numbers occurs AFTER filtering, so a false-positive early marker does not prevent the real first question from being detected.
- A **question block** includes: question stem, embedded diagram/graph/table, and all answer choices (A/B/C/D).
- A block must **never** be split — stem and choices are one indivisible unit.

#### Step 3 — Block Extraction
- For each question block, crop the corresponding rectangular region from the rendered page image.
- The crop uses the tight boundaries from Step 2: small padding above the question number, bottom anchored to the last answer choice's y_bottom plus BLOCK_BOTTOM_PADDING.
- No whitespace between the last answer choice and the next question is included in the crop.
- No whitespace padding is added between blocks in the output.
 - No whitespace between the last answer choice and the next question is included in the crop.
 - No whitespace padding is added between blocks in the output. When a slice originally included extra empty space (e.g., because the question continues on the next page), that empty area must be trimmed so the extracted block image is as compact as possible.

#### Step 4 — Block Packing (Visual Reflow)

**Column layout:**
- If `columns=1` (default): each block is placed across the full content width.
- If `columns=2`: the content area is divided into two equal columns separated by a small inter-column gap. Blocks fill the left column top-to-bottom, then the right column, then advance to the next page. Block scale is recalibrated relative to the column width.

**Base scale computation:**
- If `max_pages` is given, compute `base_scale = (max_pages × content_height × columns) / total_block_height_sum`.
- If `scale_factor` is also given, use the more restrictive (smaller) of the two.
- All blocks are initially placed at this `base_scale`.

**Placement:**
- Blocks are placed immediately after the previous block — zero gap between them within a column.
- When a block would overflow the remaining space in the current column, advance to the next column (or new page if on the last column).
- A block whose scaled height exceeds one full column height is scaled down further until it fits on a single page — it is **never split**.

**Adaptive per-page scale adjustment (gap elimination):**
- After all blocks for a column are placed (i.e., the next block does not fit), measure the gap remaining at the bottom of the column.
- **Gap threshold:** if gap > ~35–40 pts (approximately 5 text lines), trigger a gap-fill attempt.
- Gap-fill: scale down all blocks in that column uniformly until the next block fits, OR until the scale would drop more than 20–30% below the base scale — whichever limit is hit first.
  - If the next block fits within the tolerance: pull it in, re-close the column.
  - If not: accept the gap (over-shrinking beyond tolerance is not allowed).
- Blocks on different pages/columns may have slightly different effective scales (within the 20–30% tolerance). All blocks on the same column share one scale.
**Adaptive per-page scale adjustment (gap elimination):**
- After all blocks for a column are placed (i.e., the next block does not fit), measure the gap remaining at the bottom of the column.
- **Gap threshold:** if gap > ~35–40 pts (approximately 5 text lines), trigger a gap-fill attempt.
- Gap-fill now supports pulling multiple subsequent blocks (lookahead) into the current column when doing so allows a uniform downscale within the permitted tolerance. The packer will attempt a bounded lookahead (configurable) to find a small set of next blocks that, when included, permit a uniform scale that fits exactly into the column without leaving a large leftover gap.
- Additionally, before advancing the column, the packer will attempt a uniform column shrink: reduce all blocks currently in the column (within the MAX_SCALE_REDUCTION tolerance) so the existing blocks exactly fill the column height — this eliminates large blank areas without pulling additional blocks when pulling is not feasible.
- Gap-fill: scale down all blocks in that column uniformly until the next block(s) fit, OR until the scale would drop more than 20–30% below the base scale — whichever limit is hit first.
  - If the next block(s) fit within the tolerance: pull them in, re-close the column.
  - Otherwise, if a uniform shrink of only the current column is acceptable within tolerance, apply it and accept the column as full.
  - If neither is possible without over-shrinking, accept the gap. The primary goal is to avoid leaving large blank/black areas in the output — so the algorithm prefers multi-block pull-in, then uniform shrink, then accepting small gaps.
- Blocks on different pages/columns may have slightly different effective scales (within the 20–30% tolerance). All blocks on the same column share one scale.

#### Step 5 — Output PDF Generation
- Assemble packed blocks into a final PDF.
- Output resolution matches source rendering DPI.
- No headers, footers, page numbers, or decorative elements added.

### Readability Preservation (Non-Negotiable)

- A question block (stem + choices) is **never split across pages**.
- All symbols, graphs, and diagrams are rendered identically to source — no re-interpretation.
- Blocks are scaled uniformly (aspect ratio preserved) — never distorted.
- Scale adjustments during gap-fill are capped at 20–30% below base scale to prevent unreadable output.
- A very tall block that exceeds the full column height is scaled down to fit on one page — it is placed alone in its column slot, never split.

### Rendering Modes (Future)

- **Image mode** (current default): Each block is a pixel-faithful crop of the original rendered PDF page. No text is re-rendered. Math symbols, graphs, and diagrams appear identically to the source.
- **Text mode** (future): Blocks are re-rendered from extracted text. Not implemented — tracked for future phases.

### Output Contract

```json
{
  "output_format": "pdf",
  "questions_retained": "integer (must equal total questions in source)",
  "pages_original": "integer",
  "pages_compacted": "integer",
  "reduction_percent": "float"
}
```

### Failure Conditions (`compact_source`)

**FAIL if:**
- Any question block from the original is missing in the output
- Question numbering is altered or obscured
- A question stem is separated from its answer choices across a page break
- A diagram is detached from its question
- Any block is scaled below readable size
- Output is less readable than source
- Source page headers or footers appear in any block crop
- Block crop does not start at the question number or does not end at the last answer choice

### Artifacts Produced

#### `source-boundary-map.md`

```
# Source Boundary Map
Run ID | Source File | Grade | Subject | Date

## Boundary Detection
| Boundary       | Description            | Page | Y-Coord (pts) |
| First Question | {text preview}         | n    | n             |
| Last Question  | {text preview}         | n    | n             |

## Question Block Inventory
| Q# | Source Page | Y-top (pts) | Y-bottom (pts) | Has Diagram | Notes |
| 1  | n           | n           | n              | Yes / No    |       |
Total Question Blocks Identified: n

## Stripped Regions
| Region                  | Pages | Reason               |
| Pre-question content    | n     | Non-question content |
| Post-question content   | n     | Non-question content |

## Flags
- [ ] Q{n}: {reason — e.g. spans 2 pages, large diagram, table}
```

#### `compacted-source.pdf`

The primary output. A PDF where:
- Each page contains tightly packed question blocks cropped from the source.
- No gaps between consecutive blocks.
- All content (symbols, graphs, diagrams) is pixel-faithful to the original.

#### `comparison_report.json` (optional QA)

When a golden sample is available for the source (approved baseline output), the system MUST support a visual comparison step that:

- Renders the golden PDF and the generated `compacted-source.pdf` at a configured DPI.
- Computes per-page pixel diffs and flags pages exceeding a configurable diff ratio.
- Detects large blank/empty bands introduced in the output (indicates packing regressions).
- Writes `comparison_report.json` with a list of defects and per-page diff images for human review.

This artifact is consumed by the QA workflow: defects are reviewed and either (a) fixed manually, or (b) queued for an automated agent-driven repair step after human approval.

#### `compaction-report.md`

```
# Compaction Report
Run ID | Source File | Grade | Subject | Date

## Page Reduction Summary
| Original Pages | Compacted Pages | Pages Saved | Reduction % |

## Question Integrity Check
| Questions in source          | n         |
| Questions in output          | n         |
| All questions retained       | Pass/FAIL |
| No block split across pages  | Pass/FAIL |
| No content re-rendered       | Pass/FAIL |

## Readability Check
| All diagrams adjacent to question  | Pass/FAIL |
| No block scaled below minimum size | Pass/FAIL |
| Visual fidelity to source          | Pass/FAIL |

## Verdict
PASS / FAIL — {reason if fail}

## Notes
{flagged questions, edge cases, oversized blocks placed alone on page}
```

---

## 3B. Mode: `generate_worksheet` — Input Contract (Strict)

```json
{
  "mode": "generate_worksheet",
  "subject": "Math",
  "grade": "integer",
  "topic": "string",
  "source_document": "text",
  "difficulty": "Easy | Medium | Hard | Mixed",
  "question_count": "integer",
  "transformation_mode": "extract | transform | enhance",
  "question_distribution": {
    "direct": "integer",
    "variation": "integer",
    "application": "integer",
    "challenge": "integer"
  },
  "include_answer_key": true,
  "include_explanations": false
}
```

**Rules:**
- `question_count` MUST equal sum of distribution
- `source_document` MUST NOT be empty
- `grade` MUST be respected in all outputs

---

## 4. Mandatory Intermediate Artifacts

The system MUST generate these BEFORE worksheet creation:

### 4.1 Source Extract
**File:** `source-extract.md`
- Cleaned version of source
- Key examples identified
- Noise removed

### 4.2 Concept Map
**File:** `concept-map.md`

Structure:
```markdown
## Concepts Identified

| Concept | Description | Source Reference |
|---------|-------------|------------------|
| Fractions as parts | Understanding numerator/denominator | Example 1 |
```

**Rules:**
- ALL concepts must originate from source
- No inferred external concepts

---

## 5. Question Taxonomy (MTS Standard)

Every worksheet MUST include a mix of:

### 5.1 Direct (Level 1)
- Direct application from source
- Example → similar question

### 5.2 Variation (Level 2)
- Same structure, different numbers
- Slight twist in representation

### 5.3 Application (Level 3)
- Word problems
- Real-life context

### 5.4 Challenge (Level 4)
- Multi-step
- Slight abstraction

---

## 6. Transformation Rules (Strict)

### Allowed Transformations

| Type | Allowed | Example |
|------|---------|---------|
| Rephrase | Yes | Simplify wording |
| Number change | Yes | 1/2 → 3/4 |
| Format change | Yes | Example → question |
| Context change | Limited | Add real-world context |

### Disallowed Transformations
- Introducing new formulas
- Changing problem type
- Increasing conceptual difficulty beyond source
- Mixing unrelated topics

---

## 7. Question Generation Contract

Each question MUST:
- Map to ONE concept from concept map
- Be solvable with given information
- Match grade-level language
- Avoid ambiguity

**Mandatory Mapping:**

Each question must internally track:
```json
{
  "question_id": 1,
  "concept": "Equivalent Fractions",
  "source_reference": "Example 3",
  "type": "variation"
}
```

---

## 8. Worksheet Structure (Strict)

### Header
- Title
- Grade
- Topic
- Instructions

### Sections
- **Section A** — Direct Practice
- **Section B** — Variations
- **Section C** — Applications
- **Section D** — Challenge (optional)

### Formatting Rules
- Numbered questions
- Adequate spacing for answers
- Clean section separation
- No clutter

---

## 9. Answer Key Contract

- One answer per question
- Exact mapping (1 → 1)
- Units included where applicable
- Independently derived (not copied)

---

## 10. Mathematical Integrity Rules

- No unsolvable questions
- No missing data
- No contradictions
- No rounding errors unless specified

---

## 11. Source Fidelity Rules (Critical)

Each question MUST satisfy:
- Derived from source example, OR
- Valid transformation of source concept

**Traceability Check:**
For each question — "Can we trace it back to source?" → **YES required**

---

## 12. Coverage Requirements

- All major concepts from source MUST be covered
- No over-focus on a single concept
- Balanced distribution

---

## 13. Difficulty Control

| Level | Characteristics |
|-------|----------------|
| Easy | Direct recognition, single-step |
| Medium | Variation + reasoning |
| Hard | Multi-step, slight abstraction |

---

## 14. Failure Conditions

**FAIL if:**
- Any question not traceable to source
- Any incorrect answer
- Concept outside source
- Distribution mismatch
- Poor formatting

---

## 15. Traceability Artifacts

Each run MUST produce:

```
request.json
source-extract.md
concept-map.md
plan.md
worksheet-draft.md
answer-key-draft.md
qa-report.md
worksheet-final.md
```

---

## 16. Anti-Hallucination Guardrails

The system MUST:
- Reject generation if source is unclear
- Avoid guessing missing concepts
- Prefer omission over incorrect generation

---

## 17. Guiding Principles

1. Source fidelity over creativity
2. Correctness over volume
3. Structure over randomness
4. Clarity over complexity
5. Traceability over convenience

---

## 18. Authority

This spec has highest authority.

**Agents MUST NOT:**
- Override constraints
- Skip intermediate artifacts
- Bypass concept mapping

**Violation → QA failure → regeneration required**
