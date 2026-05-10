# MTS Skills Registry

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

Skills are **reusable cognitive capabilities** that agents invoke.

Unlike agents (which are pipeline-specific), skills are portable:
* A summarization skill works in an eval agent AND a lesson plan agent.
* A block extraction skill is the core of `compact_source_math` AND `compact_source_reading`.

This registry catalogs all MTS-defined skills. Before building a capability
into an agent, check here — it may already exist as a reusable skill.

---

## 2. Skills vs Agents

| Concept | Scope | Reusability |
|---------|-------|-------------|
| Skill | One capability | High — used across multiple agents |
| Agent | One pipeline stage | Low — specific to its pipeline |
| Workflow | Full pipeline | Not reusable — orchestrates skills/agents |

---

## 3. Skills Registry

### 3.1 Content Skills

| Skill | Description | Used By |
|-------|-------------|---------|
| `extract_math_blocks` | Identify and extract question blocks from a math PDF page | compact_source_math |
| `extract_reading_blocks` | Identify and extract passage/question blocks from a reading PDF | compact_source_reading |
| `pack_blocks_to_pdf` | Assemble extracted block images into a formatted output PDF | compact_source_math, compact_source_reading |
| `evaluate_worksheet` | Score a worksheet against eval dimensions | QA Agent |
| `validate_answer_key` | Verify correctness of a math answer key | QA Agent |

### 3.2 Transformation Skills

| Skill | Description | Used By |
|-------|-------------|---------|
| `rasterize_pdf_page` | Convert a PDF page to a high-resolution raster image | compact_source pipelines |
| `crop_bbox` | Crop a raster image to a bounding box | block extraction pipeline |
| `scale_image` | Resize an image to a target width fraction of content width | pdf_packer |
| `compare_pdfs_visually` | Visual diff two PDFs page by page | compact_source --compare flag |

### 3.3 Generation Skills *(planned)*

| Skill | Description | Status |
|-------|-------------|--------|
| `generate_math_problems` | Generate math problems for a grade and topic | Planned |
| `generate_answer_key` | Generate answer key with worked solutions | Planned |
| `generate_passage_questions` | Generate comprehension questions for a passage | Planned |
| `summarize_source` | Summarize source content for context injection | Planned |

### 3.4 Evaluation Skills

| Skill | Description | Used By |
|-------|-------------|---------|
| `score_functional_correctness` | Evaluate if output answers are correct | QA Agent |
| `score_grade_alignment` | Assess if content matches declared grade level | QA Agent |
| `score_spec_compliance` | Check output against spec acceptance criteria | QA Agent |
| `score_source_fidelity` | Verify no hallucinated content beyond source | QA Agent |

### 3.5 Utility Skills

| Skill | Description | Used By |
|-------|-------------|---------|
| `write_run_log` | Write a structured run log artifact | All pipeline stages |
| `write_eval_report` | Write a structured eval report artifact | QA Agent |
| `write_failure_log` | Write a failure diagnostic artifact | Any failing stage |
| `detect_block_count_anomaly` | Warn if extracted block count is suspicious | Block Detector |

---

## 4. Adding a New Skill

Before implementing, document here:

```markdown
### [skill_name]
**Description:** [what it does]
**Inputs:** [what it receives]
**Outputs:** [what it produces]
**Agents that use it:** [which agents invoke it]
**Location:** [module path in src/]
**Status:** Planned | Active | Deprecated
```

Skills live in `src/utils/` (shared utilities) or in dedicated skill modules
when they grow beyond utility scope.
