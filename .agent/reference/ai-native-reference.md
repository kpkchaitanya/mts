# AI Native Development Reference

## Purpose

This document serves as the **single source of truth** for the AI-native, spec-driven development framework.

It defines:

* Folder structure
* All `.md` artifacts
* Their roles, usage, and relationships
* End-to-end execution flow

---

# 1. Folder Structure

```
mts/
│
├── README.md                                               ← Project overview, active features, guiding principles
│
└── .agent/                                                 ← All agentic infrastructure (agent-agnostic)
    │
    ├── governance/                                         ← Identity, philosophy, and governing rules of MTS
    │   ├── soul.md                                         ← The why: MTS values, teaching philosophy, Feynman principle
    │   ├── constitution.md                                 ← The how: governing rules for all agents and outputs
    │   ├── agent.md                                        ← Operating protocol for all agents (pipeline + coding)
    │   └── program.md                                      ← The what: batches, grades, subjects, fees, teachers
    │
    ├── specs/                                              ← Feature contracts — defines what each feature must do
    │   └── math_worksheet_generation_from_source/
    │       └── math-worksheet-generation-from-source-spec.md   ← Input/output contract, transformation rules, quality requirements
    │
    ├── evals/                                              ← Evaluation frameworks and run artifacts
    │   ├── eval.md                                         ← Project-level eval: 10 dimensions, scoring model, pass/fail gates
    │   ├── math_worksheet_generation_from_source/
    │   │   └── math-worksheet-generation-from-source-eval.md   ← Feature-level eval (placeholder — pending generation)
    │   └── runs/                                           ← All run artifacts live here, organized by feature
    │       └── math_worksheet_generation_from_source/
    │           ├── eval-summary-template.md                ← Template: scored eval across all 10 dimensions per run
    │           └── trace-template.md                       ← Template: step-by-step execution log per run
    │
    ├── agents/                                             ← Agent definitions — one file per agent role
    │   └── math_worksheet_generation_from_source/
    │       ├── intake-agent.md                             ← Normalizes raw request into structured request.json
    │       ├── source-extractor-agent.md                   ← Cleans and extracts key content from source document
    │       ├── concept-mapper-agent.md                     ← Maps concepts from source into structured concept-map.md
    │       ├── worksheet-planner-agent.md                  ← Creates question distribution plan before generation
    │       ├── question-generator-agent.md                 ← Generates worksheet draft from plan
    │       ├── answer-key-agent.md                         ← Independently derives answers for every question
    │       ├── qa-agent.md                                 ← Validates correctness, source fidelity, structure — has veto power
    │       └── formatter-agent.md                          ← Renders approved content into final print-ready output
    │
    ├── workflows/                                          ← Workflow definitions — sequence, handoffs, loopback rules
    │   └── math_worksheet_generation_from_source/
    │       └── math-worksheet-generation-from-source-workflow.md   ← Full pipeline: intake → extract → map → plan → generate → QA → format
    │
    ├── templates/                                          ← Reusable starter templates for runs and outputs
    │   └── math_worksheet_generation_from_source/
    │       ├── worksheet-request-template.json             ← Structured input template for a worksheet run
    │       ├── worksheet-plan-template.md                  ← Concept coverage and question distribution plan
    │       ├── worksheet-template.md                       ← Blank worksheet with sections A–D
    │       ├── answer-key-template.md                      ← Answer key table template
    │       └── qa-report-template.md                       ← QA checklist with pass/fail verdict
    │
    ├── memory/                                             ← Institutional knowledge — decisions and learnings across sessions
    │   ├── decisions.md                                    ← Log of architectural and structural decisions with rationale
    │   └── learnings.md                                    ← Lessons from runs, failures, and design iterations
    │
    └── reference/                                          ← Reference documents for the system
        └── ai-native-reference.md                         ← This file — canonical structure reference
```

---

# 2. Holistic Table of All `.md` Files

| Layer | File / Artifact | Definition | Usage | Compare / Contrast |
|-------|----------------|------------|-------|-------------------|
| **Governance** | constitution.md | Non-negotiable system rules and constraints | Enforces consistency and prevents bad practices | vs soul.md → rules vs philosophy |
| **Governance** | soul.md | System identity, philosophy, and thinking model (Clarity, Leverage, Alignment, Wisdom) | Guides behavior of agents and humans | vs program.md → mindset vs execution |
| **Governance** | agent.md | Operating protocol for all agents — pipeline agents and coding agents | Defines how agents behave, hand off artifacts, and write code | vs constitution.md → protocol vs principles |
| **Governance** | program.md | Strategic roadmap and execution direction | Defines what to build and sequencing | vs constitution.md → direction vs constraints |
| **Governance** | README.md | Repository entry point and navigation guide | Helps users and agents understand structure quickly | vs reference → quick guide vs deep knowledge |
| **Reference** | ai-native-reference.md | Master architecture and framework document | Resolves doubts and provides holistic understanding | vs README.md → deep reference vs quick navigation |
| **Template** | spec-template.md | Standard structure for requirements | Ensures consistency across specs | vs workflow-template → what vs how |
| **Template** | workflow-template.md | Standard execution sequence format | Guides orchestration of tasks | vs agent-template → flow vs role |
| **Template** | agent-template.md | Standard definition of agent responsibilities | Ensures consistent agent behavior | vs skill-template → executor vs capability |
| **Template** | eval-template.md | Standard evaluation structure | Ensures consistent quality measurement | vs trace-template → quality vs execution |
| **Template** | trace-template.md | Standard execution logging format | Ensures observability and debugging | vs eval.md → what happened vs how good |
| **Execution** | specs/*.md | Feature-level requirements | Starting point of all development work | vs workflows → definition vs execution |
| **Execution** | workflows/*.md | Step-by-step execution logic | Orchestrates agents and processes | vs agents → flow vs actor |
| **Execution** | agents/*.md | Role-based execution units | Perform defined tasks | vs skills → who executes vs how it's done |
| **Execution** | evals/*.md | Evaluation definitions and results | Measure correctness and quality | vs trace → performance vs execution history |
| **Runtime** | evals/runs/ | Collection of execution instances | Tracks system evolution over time | vs trace → grouped runs vs individual logs |
| **Runtime** | eval-summary.md | High-level summary of execution | Provides quick insights | vs trace.md → summary vs detailed log |
| **Runtime** | trace.md | Execution logs | Debug, audit, and analyze runs | vs eval → what happened vs how well |
| **Memory** | decisions.md | Log of architectural and structural decisions | Records rationale for choices made | vs learnings → deliberate choices vs observed outcomes |
| **Memory** | learnings.md | Lessons from runs, failures, and design iterations | Drives continuous improvement | vs decisions → outcomes observed vs choices made |

---

# 3. Core Principles (Soul Alignment)

## Clarity

* All work must be structured and explicit
* Specs, evals, and traces are mandatory

## Leverage

* Reuse templates, skills, and shared components
* Avoid duplication

## Alignment

* All artifacts must align with constitution and program
* No isolated or ad-hoc work

## Wisdom

* Use evals and trace logs to improve continuously
* Maintain human-in-the-loop for critical decisions

---

# 4. Execution Flow

```
Spec → Workflow → Agent → Execution → Eval → Trace → Improve
```

---

# 5. Operating Model

## Roles

| Role | Responsibility |
|------|---------------|
| Human Architect | Defines specs, validates outputs, ensures alignment |
| Agents | Execute workflows and tasks |
| System | Maintains structure, standards, and feedback loops |

---

# 6. Non-Negotiable Rules

* Every feature starts with a **spec**
* Every execution produces **eval + trace**
* No duplication of logic or constants
* Templates must be used
* Outputs must be structured and readable

---

# 7. Anti-Patterns (Avoid)

* Code-first development without specs
* Skipping eval or trace
* Hardcoding instead of reuse
* Unstructured outputs
* Over-engineering early

---

# 8. Maturity Model

| Level | Description |
|-------|-------------|
| Level 1 | Ad-hoc development |
| Level 2 | Spec-driven development |
| Level 3 | Agent-assisted execution |
| Level 4 | Eval + trace feedback loops |
| Level 5 | Fully AI-native self-improving system |

---

# 9. Authority Chain

```
soul.md → constitution.md → agent.md → spec → eval → workflow → agents → output
```

Higher layers override lower layers. No exceptions.

---

# 10. Feature Naming Convention

| Layer | Convention | Example |
|-------|-----------|---------|
| Folder | `snake_case` | `math_worksheet_generation_from_source` |
| Files | `kebab-case` | `math-worksheet-generation-from-source-spec.md` |
| Agents | `role-agent.md` | `concept-mapper-agent.md` |

---

# 11. Run Artifacts Per Feature

Every run under `.agent/evals/runs/<feature>/<run-id>/` produces:

| File | Produced By | Purpose |
|------|------------|---------|
| `request.json` | intake-agent | Normalized input |
| `source-extract.md` | source-extractor-agent | Cleaned source content |
| `concept-map.md` | concept-mapper-agent | Concepts mapped to source |
| `plan.md` | worksheet-planner-agent | Question distribution plan |
| `worksheet-draft.md` | question-generator-agent | First draft worksheet |
| `answer-key-draft.md` | answer-key-agent | Independently derived answers |
| `qa-report.md` | qa-agent | Validation results + pass/fail |
| `eval-summary.md` | eval process | Scored across 10 dimensions |
| `trace.md` | workflow | Step-by-step execution log |
| `worksheet-final.md` | formatter-agent | Final print-ready worksheet |

---

# 12. Active Features

| Feature | Spec | Eval | Workflow | Agents |
|---------|------|------|----------|--------|
| `math_worksheet_generation_from_source` | ✅ v3 | Pending | Placeholder | 8 defined (placeholder) |

---

# 13. Final Principle

> We are not building isolated features.
> We are building a system that builds correctly, consistently, and improves over time.
