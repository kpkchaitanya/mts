# math-worksheet-generation-from-source-spec.md

**Feature Name:** math_worksheet_generation_from_source
**Version:** v5
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
  "subject": "string"
}
```

### Processing Pipeline (Strict)

#### Step 1 — Page Rendering
- Render each source PDF page to a high-resolution image (≥150 DPI) using PyMuPDF.
- Retain page geometry metadata (page width, height, DPI scale factor).

#### Step 2 — Question Block Detection
- Identify question block boundaries using a **hybrid approach**:
  - Extract text with positional coordinates (pdfplumber) to locate question number markers (e.g., "1.", "2.") and answer choice lines (A./B./C./D. or F./G./H./J.).
  - **Top boundary** of each block: the y-coordinate of the question number marker, minus a small upward padding (to capture the number itself).
  - **Bottom boundary** of each block: the y_bottom of the **last answer choice line** (e.g., the "D." or "J." line) detected within the block's span, plus a small downward padding. This is the definitive bottom — NOT the y-coordinate of the next question marker.
  - For the last question: bottom boundary = the y_bottom of its last answer choice, plus small padding.
- **Non-question marker filtering:** Number markers (e.g., "1." in a formula chart or numbered instruction list) that have no detectable answer choices (A/B/C/D) AND span more than MAX_QUESTION_SPAN_PAGES pages are discarded as non-question content before building blocks. This prevents intro/reference material from being treated as the first question.
- Deduplication of question numbers occurs AFTER filtering, so a false-positive early marker does not prevent the real first question from being detected.
- A **question block** includes: question stem, embedded diagram/graph/table, and all answer choices (A/B/C/D).
- A block must **never** be split — stem and choices are one indivisible unit.

#### Step 3 — Block Extraction
- For each question block, crop the corresponding rectangular region from the rendered page image.
- The crop uses the tight boundaries from Step 2: small padding above the question number, bottom anchored to the last answer choice's y_bottom plus BLOCK_BOTTOM_PADDING.
- No whitespace between the last answer choice and the next question is included in the crop.
- No whitespace padding is added between blocks in the output.

#### Step 4 — Block Packing (Visual Reflow)
- Place extracted question blocks sequentially onto new PDF pages, top to bottom.
- Blocks are placed **immediately after** the previous block — zero gap between them.
- When a block would overflow the current page, start a new page.
- A block that does not fit on a full page (very tall diagram question) is placed alone on its own page — **it is never cropped or split**.
- Page margins: minimal (e.g., 0.25 in) to maximize content density.

#### Step 5 — Output PDF Generation
- Assemble packed blocks into a final PDF.
- Output resolution matches source rendering DPI.
- No headers, footers, page numbers, or decorative elements added.

### Readability Preservation (Non-Negotiable)

- A question block (stem + choices) is **never split across pages**.
- All symbols, graphs, and diagrams are rendered identically to source — no re-interpretation.
- Minimum block height is not compressed — blocks are cropped, not scaled down.
- If scaling is needed to pack a very wide block: scale uniformly (maintain aspect ratio), minimum readable size.

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
