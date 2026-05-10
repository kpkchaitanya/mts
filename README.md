# MTS — Master Tuition Services - Making Academic Teaching more enjoyable, effective, and thoughtful!


**Project:** Masters Tuition Services
**Tagline:** "Making Academic Tuition More Enjoyable, Effective, & Very Affordable"
**Purpose:** Build an AI-native system that supports MTS teachers in delivering high-quality, curriculum-aligned education to students in Grades 2–10. The system automates content generation (worksheets, answer keys, lesson plans) so that teachers can focus on judgment, connection, and care — while every output upholds the MTS standard: correct, clear, and student-first.

---

## Structure

```
mts/
├── README.md                          ← this file
├── src/                               ← production Python source code
├── tests/                             ← unit and integration tests
├── docs/                              ← source materials (exams, strategy)
├── scripts/                           ← diagnostic and utility scripts
├── config/                            ← configuration files
└── .agent/                            ← AI-native cognitive infrastructure
    │
    ├── governance/                    ← system DNA: philosophy, principles, boundaries
    │   ├── soul.md                    ← why MTS exists; core identity
    │   ├── constitution.md            ← non-negotiable governing principles
    │   ├── program.md                 ← MTS operational program knowledge
    │   ├── agent.md                   ← agent operating protocol
    │   ├── persona.md                 ← agent behavioral expression
    │   ├── role.md                    ← agent functional responsibilities
    │   ├── standards.md               ← engineering and content standards
    │   ├── safety.md                  ← risk categories and policy boundaries
    │   ├── glossary.md                ← shared terminology
    │   ├── architecture/              ← strategic architecture documents
    │   └── principles/                ← engineering, prompting, agent principles
    │       ├── engineering-principles.md
    │       ├── prompting-principles.md
    │       └── agent-principles.md
    │
    ├── ontology/                      ← domain intelligence: what exists, what it means
    │   └── mts-ontology.md            ← MTS domain concepts and relationships
    │
    ├── knowledge/                     ← LLM wiki: retrievable institutional knowledge
    │   ├── README.md
    │   ├── math-scope-and-sequence.md
    │   ├── ela-scope-and-sequence.md
    │   └── pedagogical-guidelines.md
    │
    ├── product/                       ← PRDs and user stories
    │   ├── README.md
    │   └── prd-compact-source.md
    │
    ├── specs/                         ← feature specifications (contracts of truth)
    │   ├── compact_source/
    │   ├── math_worksheet_generation_from_source/
    │   └── platform/
    │
    ├── evals/                         ← evaluation frameworks
    │   ├── eval.md                    ← PROJECT-LEVEL eval framework
    │   └── math_worksheet_generation_from_source/
    │
    ├── harness/                       ← quality intelligence infrastructure
    │   ├── README.md
    │   ├── traces/                    ← execution traces for diagnosis
    │   ├── regression/                ← regression test cases and results
    │   └── benchmarks/                ← performance and quality benchmarks
    │
    ├── agents/                        ← agent definitions
    │   └── math_worksheet_generation_from_source/
    │
    ├── workflows/                     ← workflow orchestration definitions
    │   └── math_worksheet_generation_from_source/
    │
    ├── skills/                        ← reusable cognitive capability registry
    │   └── README.md
    │
    ├── context/                       ← context engineering templates and strategy
    │   └── README.md
    │
    ├── observability/                 ← observability tracking and instrumentation
    │   └── README.md
    │
    ├── memory/                        ← decisions and learnings log
    │   ├── decisions.md
    │   └── learnings.md
    │
    ├── bugs/                          ← bug reports (feed harness/failures)
    ├── improvements/                  ← improvement proposals (feed harness/repair)
    ├── reference/                     ← reference documents
    └── templates/                     ← reusable pipeline templates
```

---

## AI-Native Cognitive Architecture

This repository is organized as an **AI-native cognitive system** — not just a codebase.

The `.agent/` directory is the cognitive infrastructure: governance, ontology, knowledge,
skills, context engineering, harness, and observability all work together to ensure
that AI agents produce reliable, traceable, student-safe outputs.

**Authority chain:**
```
soul.md → constitution.md → agent.md → role.md / persona.md → Spec → Workflow → Execution
```

**Quality chain:**
```
Evals → Harness → Traces → Regression → Benchmarks → Observability → Learning
```

Full architecture reference: `.agent/governance/architecture/holistic-ai-native-cognitive-architecture.md`

---

## Active Features

| Feature | Status | PRD | Spec | Eval | Workflow |
|---------|--------|-----|------|------|----------|
| compact_source | ✅ Active | [PRD](.agent/product/prd-compact-source.md) | ✅ | Active | Active |
| math_worksheet_generation_from_source | In Design | Planned | ✅ v3 | Pending | Placeholder |

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
