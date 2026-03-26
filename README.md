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
