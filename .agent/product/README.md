# MTS Product Layer

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

The product layer defines **what** MTS is building and **why**.

It houses PRDs (Product Requirements Documents) and user stories that transform
teacher and organizational intent into executable product direction.

This layer lives above specs.
Specs define *how* a feature behaves.
PRDs define *why it exists* and *what success looks like*.

---

## 2. Structure

```text
product/
├── README.md                          ← this file
├── roadmap.md                         ← prioritized feature roadmap
├── prd-compact-source.md              ← PRD: compact_source feature
└── prd-math-worksheet-generation.md   ← PRD: math worksheet generation
```

---

## 3. PRD Template

Each PRD must contain:

```markdown
# PRD: [Feature Name]

## 1. Problem Statement
What teacher or student problem does this solve?

## 2. User Personas
Who uses this? (Teacher / Student / Administrator)

## 3. Goals
What does success look like? (measurable where possible)

## 4. Non-Goals
What is explicitly out of scope?

## 5. User Stories
As a [persona], I want to [action], so that [outcome].

## 6. Success Criteria
How do we know this is working?

## 7. Open Questions
What needs to be resolved before or during implementation?
```

---

## 4. Active PRDs

| Feature | PRD | Status |
|---------|-----|--------|
| compact_source | [prd-compact-source.md](prd-compact-source.md) | Draft |
| math_worksheet_generation_from_source | [prd-math-worksheet-generation.md](prd-math-worksheet-generation.md) | Draft |
