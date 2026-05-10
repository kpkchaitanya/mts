# MTS Knowledge Base — LLM Wiki

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

This is the MTS **LLM Wiki** — a structured, markdown-first knowledge repository
optimized for AI agent consumption.

It stores institutional knowledge that:
* Does not change frequently
* Should be retrievable in context when agents need grounding
* Is too stable to live in specs (which are feature-specific)
* Is too operational to live in governance (which is principle-level)

---

## 2. Contents

| Document | Description |
|----------|-------------|
| [curriculum-standards.md](curriculum-standards.md) | NC Common Core & AIG standards by grade |
| [pedagogical-guidelines.md](pedagogical-guidelines.md) | Teaching principles and content design guidelines |
| [math-scope-and-sequence.md](math-scope-and-sequence.md) | Math topics by grade level |
| [ela-scope-and-sequence.md](ela-scope-and-sequence.md) | ELA topics by grade level |
| [program-knowledge.md](program-knowledge.md) | MTS-specific operational knowledge |

---

## 3. LLM Wiki Usage Guidance

When an agent needs domain grounding, it should request relevant knowledge
documents to inject into context.

**For content generation tasks:**
→ Inject the relevant scope-and-sequence for the declared grade and subject

**For QA tasks:**
→ Inject the curriculum standards for the declared grade

**For formatting tasks:**
→ Inject pedagogical-guidelines.md

**For all tasks:**
→ The ontology (`ontology/mts-ontology.md`) provides concept definitions
→ The glossary (`governance/glossary.md`) provides terminology disambiguation

---

## 4. Maintenance

* Documents are updated when curriculum standards change or MTS program evolves.
* Changes are version-noted at the top of each document.
* Additions are proposed in `decisions.md` before being added here.
