# MTS — Master Tuition Services - Making Academic Teaching more enjoyable, effective, and thoughtful!


**Project:** Masters Tuition Services
**Tagline:** "Making Academic Tuition More Enjoyable, Effective, & Very Affordable"
**Purpose:** Build an AI-native system that supports MTS teachers in delivering high-quality, curriculum-aligned education to students in Grades 2–10. The system automates content generation (worksheets, answer keys, lesson plans) so that teachers can focus on judgment, connection, and care — while every output upholds the MTS standard: correct, clear, and student-first.

---

## Structure

```
mts/
├── README.md                          ← this file
└── .agent/                            ← agent-agnostic agentic infrastructure
    ├── governance/                    ← system-wide governing principles
    │   ├── soul.md
    │   ├── constitution.md
    │   └── program.md
    ├── memory/                        ← decisions and learnings log
    │   ├── decisions.md
    │   └── learnings.md
    ├── reference/                     ← reference documents
    ├── specs/                         ← feature specifications (contracts of truth)
    │   └── math_worksheet_generation_from_source/
    ├── evals/                         ← evaluation frameworks + run artifacts
    │   ├── eval.md                    ← PROJECT-LEVEL eval
    │   ├── math_worksheet_generation_from_source/
    │   └── runs/                      ← run artifacts and trace logs
    │       └── math_worksheet_generation_from_source/
    ├── agents/                        ← agent definitions
    │   └── math_worksheet_generation_from_source/
    ├── workflows/                     ← workflow definitions
    │   └── math_worksheet_generation_from_source/
    └── templates/                     ← reusable templates
        └── math_worksheet_generation_from_source/
```

---

## Active Features

| Feature | Status | Spec | Eval | Workflow |
|---------|--------|------|------|----------|
| math_worksheet_generation_from_source | In Design | ✅ v3 | Pending | Placeholder |

---

## Usage

### Source PDFs

Place source worksheet PDFs in `docs/exams/` before running any pipeline command.

### compact_source

Compacts a source worksheet PDF into a print-efficient output PDF. All question blocks are extracted as images — math symbols, graphs, and diagrams are preserved exactly as they appear in the source.

**Basic usage** (run from the project root):

```bash
python -m src.orchestrator compact_source --pdf docs/exams/<filename>.pdf --grade <n> --subject Math
```

**All options:**

| Flag | Required | Description |
|------|----------|-------------|
| `--pdf` | ✅ | Path to a source worksheet PDF, or a **folder** to compact all PDFs inside it |
| `--grade` | | Grade level (e.g. `3`, `8`) — label in reports only (default: `0`) |
| `--subject` | | Subject area (default: `Math`) — label in reports only |
| `--scale-factor` | | Block size as % of content width (e.g. `85` → 85%) |
| `--max-pages` | | Target maximum number of output pages |
| `--columns` | | Output columns: `1` (default) or `2` |
| `--problem-list` | | Problems to include: `ALL` (default), `1-10`, or `1,3,5` |
| `--compare` | | Run visual comparison against a golden sample |
| `--golden` | | Path to the golden sample PDF (required with `--compare`) |

**Examples:**

```bash
# Compact a single file
python -m src.orchestrator compact_source --pdf docs/exams/2022-staar-5-math-test.pdf

# Compact all PDFs in a folder
python -m src.orchestrator compact_source --pdf docs/exams/2026-mid-term

# Compact problems 1–10 at 85% scale in 2 columns
python -m src.orchestrator compact_source --pdf docs/exams/2022-staar-5-math-test.pdf --problem-list 1-10 --scale-factor 85 --columns 2

# Compact and compare against a golden sample
python -m src.orchestrator compact_source --pdf docs/exams/2022-staar-5-math-test.pdf --compare --golden docs/exams/golden-staar-5.pdf
```

**Outputs** are written to `.agent/evals/runs/math_worksheet_generation_from_source/<run_id>/`:

| File | Description |
|------|-------------|
| `compacted-source.pdf` | The output PDF |
| `compaction-report.md` | Pass/fail summary and page reduction stats |
| `source-boundary-map.md` | Detected question block boundaries |
| `pack_layouts.csv` | Per-block layout trace (for debugging) |

### Slash Command

In VS Code Copilot Chat, type `/compact_source` to be guided interactively through building and running the command.

---

## Guiding Principles

1. Spec first — always define the contract before building
2. Eval second — always define quality before generating
3. Agents follow spec, not assumptions
4. Every run produces a trace and eval summary
5. Correctness over creativity
6. Source fidelity over hallucination

---

## Command Prompts

- `prompts/compact_source.prompt.md` — run the compact source pipeline
- `prompts/switch_git_identity.prompt.md` — switch global Git username/email using command parameters
