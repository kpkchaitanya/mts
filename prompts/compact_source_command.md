# compact_source_command.md

How to run the `compact_source` pipeline, what the runner does, and how to
interpret QA results.

---

## Overview

- Processes one or more source PDFs into compact worksheet PDFs.
- By default produces **both 1-column and 2-column** layouts in a single run.
- All outputs (PDFs + `run.log`) land in one shared run folder under
  `.agent/evals/runs/math_worksheet_generation_from_source/<timestamp>/`.
- After every batch the runner automatically executes the full QA suite and
  prints a verdict table.

---

## Standard command

Run from the project root with the `.venv` activated:

```bash
python scripts/compact_runner.py \
  --inputs docs/exams/2026-EOGs/math/05_09_2026/NY_Math_Grade4_2023.pdf \
           docs/exams/2026-EOGs/math/05_09_2026/NY_Math_Grade5_2023.pdf \
  --grade 4 \
  --subject Math
```

Multiple files (separate invocations per grade if needed):

```bash
python scripts/compact_runner.py \
  --inputs "docs/exams/2026-EOGs/math/05_09_2026/NY_Math_Grade6_2023_Released_Test_Questions.pdf" \
           "docs/exams/2026-EOGs/math/05_09_2026/NY_Regents_AlgebraI_Aug2023.pdf" \
  --grade 6 \
  --subject Math
```

---

## Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--inputs` | paths (1+) | required | Source PDF file(s) to compact |
| `--grade` | int | required | Grade level (e.g. 3, 4, 5, 6) |
| `--subject` | str | `Math` | Subject string written into output filenames |
| `--columns` | int(s) | `1 2` | Layout(s) to produce. Accepts multiple values. Defaults to both 1-col and 2-col. |
| `--max-pages` | int | `None` | Cap output at N pages per layout |
| `--scale-factor` | float | `None` | Override image scale factor |

To produce only one layout pass `--columns 1` or `--columns 2` explicitly.

---

## How the runner works

`scripts/compact_runner.py` is an **in-process orchestrator** — it calls
`run_compact_source_math()` directly (no subprocess) and shares one run folder
across all inputs and column counts.

Execution flow:

```
for each col_count in args.columns:          # default: [1, 2]
    for each input PDF:
        call run_compact_source_math(...)
        append PASS / FAIL to results table

run_post_generation_qa(run_path)             # programmatic QA on all outputs
_print_qa_table(qa_results)                  # verdict table to stdout
exit 1 if any hard-blocker FAIL
```

---

## Output structure

```
.agent/evals/runs/math_worksheet_generation_from_source/<run_id>/
  NY_Math_Grade4_2023_1col.pdf
  NY_Math_Grade4_2023_2col.pdf
  NY_Math_Grade5_2023_1col.pdf
  NY_Math_Grade5_2023_2col.pdf
  run.log
```

---

## QA scenarios (run automatically after every batch)

| ID | Check | Blocker? |
|----|-------|----------|
| QA-PACK-03 | Every output PDF has at least one image on page 0 (non-blank) | Hard |
| QA-PACK-04 | Run folder contains only `.pdf` and `.log` files | Hard |
| QA-PACK-05 | Output page count <= source page count | Soft / WARN |
| QA-EXT-02 | Extracted images are >= 1200 px wide (confirms DPI) | Hard |
| QA-EXT-03 | No image is >3x taller than wide (no page-height slivers) | Soft / WARN |
| QA-REP-01 | `run.log` exists and is non-empty | Hard |
| QA-REP-02 | `run.log` contains "blocks detected" line | Hard |
| QA-REP-03 | `run.log` references expected grade strings (G3/G4/G5 only) | Hard |
| QA-DET-05 | No block has Q#=0 (cover/session-heading pages in output) | Hard |

**Known persistent failures:**
- **QA-REP-03**: False positive for Grade 6 / Algebra I — check is hard-coded to
  look for "Grade3/Grade4/Grade5". Fix pending.
- **QA-DET-05**: Cover/session-heading raster pages still appear as Q#=0 blocks
  (BUG-011 open — previous filter was reverted because it excluded real Q pages).

---

## Key implementation notes

### NY sidebar x-position filter

Real NY sidebar question markers sit at x0 approx 42-56 pts. False positives
from fraction numerals and inline numbers appear at x0 >= 79 pts. The detector
gates sidebar detection on `NY_SIDEBAR_MAX_X_PTS = 72.0` in `block_detector.py`.
This fixed Q9 (Grade 5) and Q44 (Grade 4) being cut off in 05/09/2026 files.

### Dual-column default

```python
parser.add_argument("--columns", type=int, choices=[1, 2], nargs="+", default=[1, 2])
```

---

## Useful stdout filter

```powershell
python scripts/compact_runner.py --inputs ... --grade 5 --subject Math 2>&1 |
  Select-String -Pattern "blocks detected|col\) ->|pages ->|Run ID:|  PASS|  FAIL|! QA|[*] QA|Verdict|DELIVERABLE|BLOCKED"
```

---

## Baseline block counts

| File | Grade | Blocks |
|------|-------|--------|
| NY Math G3 2023 (05/08) | 3 | 22 |
| NY Math G4 2023 (05/08) | 4 | 27 |
| NY Math G5 2023 (05/08) | 5 | 20 |
| NY Math G4 2023 (05/09) | 4 | ~26 |
| NY Math G5 2023 (05/09) | 5 | ~26 |
| NY Math G6 2023 (05/09) | 6 | 30 |
| NY Regents Algebra I Aug 2023 | -- | 36 |
