# platform — Cross-Cutting Infrastructure Specs

This folder contains specifications and design documents for platform-level concerns that apply to **all MTS features**, not just one feature.

Each sub-folder is a theme. A theme groups related specs and design documents that belong together.

---

## Themes

| Theme | Folder | Phase | Status | Backlog Items |
|-------|--------|-------|--------|---------------|
| Observability | `observability/` | Phase 2 | Active | IMP-003, IMP-004 |
| Resilience | `resilience/` | Phase 3 | Planned | IMP-005, IMP-006, IMP-007 |
| Quality | `quality/` | Phase 4 | Planned | IMP-002, IMP-008, IMP-009 |
| Self-Improvement | `self-improvement/` | Phase 5 | Planned | IMP-010, IMP-011, IMP-012 |
| CI/CD | `ci-cd/` | Phase 6 | Planned | IMP-013, IMP-014, IMP-015, IMP-016 |

---

## Naming Convention

Each theme folder contains up to two documents:

| File | Purpose |
|------|---------|
| `platform-{theme}-spec.md` | **Contract** — what the platform guarantees; required artifacts; testability checklist |
| `platform-{theme}-design.md` | **Implementation** — how it works; class design; architecture diagrams |

Feature-specific delivery docs (e.g. `compact_source-phase2-design.md`) reference the platform spec but only contain what is specific to that feature's implementation work.
