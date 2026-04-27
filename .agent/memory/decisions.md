# decisions.md — MTS System Decisions Log

**Purpose:** Record key architectural, structural, and design decisions made during the MTS agentic system build.

---

## Decision Log

| # | Date | Decision | Rationale | Status |
|---|------|----------|-----------|--------|
| 14 | 2026-04-26 | Adopt AI-First SDLC loop: PRD → Spec → Build → Run → Eval → Observe → Learn → Heal | Ensures every phase is AI-native, traceable, and self-improving | Active |
| 13 | 2026-04-26 | Sequence harness work into 6 SDLC phases logged in backlog.md | Incremental delivery; each phase gates the next; avoids big-bang rewrites | Active |
| 12 | 2026-04-26 | DPI default changed from 150 to 96; override in .env takes precedence | 96 DPI produces print-ready output at ~35% smaller file size; 150 DPI was left as .env override | Active |
| 11 | 2026-04-26 | Add PDF deflate compression (`deflate=True, garbage=4`) to packer save | Reduces output PDF file size significantly at no quality cost | Active |
| 10 | 2026-04-26 | Column count included in output filename (`_1col_` / `_2col_`) | Makes 1-column and 2-column outputs distinguishable without opening files | Active |
| 9 | 2026-04-26 | Folder mode uses a single shared ArtifactWriter for all PDFs in the batch | All outputs from one folder run land in one run folder; cleaner organization | Active |
| 8 | 2026-04-26 | Auto-detect PDF format (image_heavy vs text_rich) by sampling word counts | EOG-style PDFs (one visual question per page) need a different detection strategy than STAAR | Active |
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
