# decisions.md — MTS System Decisions Log

**Purpose:** Record key architectural, structural, and design decisions made during the MTS agentic system build.

---

## Decision Log

| # | Date | Decision | Rationale | Status |
|---|------|----------|-----------|--------|
| 1 | 2026-03-22 | Start with `math_worksheet_generation_from_source` as first feature | High frequency, easy to validate correctness, foundational for other features | Active |
| 2 | 2026-03-22 | Math only, source-grounded (not free-form generation) | Prevents hallucination, ensures fidelity to curriculum materials | Active |
| 3 | 2026-03-22 | Renamed feature to `math_worksheet_generation_from_source` | Precise scoping — differentiates from future freeform generation | Active |
| 4 | 2026-03-22 | All agentic infrastructure moved into `.agent/` folder | Agent-agnostic, separates AI system files from actual project content | Active |
| 5 | 2026-03-22 | `constitution.md` moved into `.agent/governance/` | Governance is a distinct concern; allows future governance docs alongside it | Active |
| 6 | 2026-03-22 | `runs/` moved under `.agent/evals/` | Runs produce eval artifacts — keeping them co-located with evals is semantically correct | Active |
| 7 | 2026-03-22 | `memory/` folder created for `decisions.md` and `learnings.md` | Captures institutional knowledge that is not derivable from code or structure | Active |

---

## Decision Template

```
| # | YYYY-MM-DD | <decision> | <rationale> | Active / Superseded |
```
