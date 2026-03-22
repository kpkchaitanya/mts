# MTS — AI-Native Agentic System

**Project:** Mecklenburg Tutorial Services
**Purpose:** Automate curriculum, worksheet generation, assessment, and program management using an agentic AI system.

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
