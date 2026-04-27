---
mode: ask
description: Run the compact_source pipeline to compact a source worksheet PDF into a print-efficient layout.
---

You are helping an MTS teacher run the `compact_source` pipeline.

Collect the following details from the user if not already provided:

- **PDF path** — path to a single source worksheet PDF, or a folder to compact all PDFs inside it (files are stored in `docs/exams/`)
- **Grade** *(optional)* — grade level integer (e.g. 3, 4, 5); used only as a label in reports
- **Subject** *(optional)* — subject area (default: `Math`); used only as a label in reports
- **Scale factor** *(optional)* — block size as a % of content width (e.g. `85` to shrink to 85%)
- **Max pages** *(optional)* — target maximum number of output pages
- **Columns** *(optional)* — `1` (default) or `2`
- **Problem list** *(optional)* — `ALL` (default), a range like `1-10`, or a comma list like `1,3,5`
- **Compare against golden?** *(optional)* — if yes, ask for the golden PDF path

Once you have the PDF path, output the exact command to run from the project root:

```bash
python -m src.orchestrator compact_source \
  --pdf <pdf_path> \
  [--grade <grade>] \
  [--subject <subject>] \
  [--scale-factor <value>] \
  [--max-pages <value>] \
  [--columns <1|2>] \
  [--problem-list <list>] \
  [--compare --golden <golden_path>]
```

**Rules:**
- Always run from the project root (`c:\Users\neeli\kpkDevelopment\mts`)
- `--pdf` is the only required flag — omit all others if not provided by the user
- If the user provides only a filename (e.g. `2022-staar-3-math-test.pdf`), prepend `docs/exams/`
- After the command, remind the user that run artifacts and reports will be written to `.agent/evals/runs/math_worksheet_generation_from_source/<run_id>/`
