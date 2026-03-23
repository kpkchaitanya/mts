# math-worksheet-generation-from-source-workflow.md

**Feature:** math_worksheet_generation_from_source
**Version:** v1
**Status:** Placeholder — to be generated

---

## Workflow Overview

```
Request → Intake → Source Extract → Concept Map → Plan → Generate → Answer Key → QA → Format → Publish
```

---

## Steps

| Step | Agent | Input | Output |
|------|-------|-------|--------|
| 1 | intake-agent | raw request | request.json |
| 2 | source-extractor-agent | request.json + source | source-extract.md |
| 3 | concept-mapper-agent | source-extract.md | concept-map.md |
| 4 | worksheet-planner-agent | concept-map.md + request | plan.md |
| 5 | question-generator-agent | plan.md | worksheet-draft.md |
| 6 | answer-key-agent | worksheet-draft.md | answer-key-draft.md |
| 7 | qa-agent | worksheet-draft.md + answer-key-draft.md | qa-report.md |
| 8 | formatter-agent | worksheet-draft.md (approved) | worksheet-final.md |

---

## Authority Chain

```
Spec → Request → Source Extract → Concept Map → Plan → Worksheet → Answer Key → QA → Final Output
```

- QA has veto power
- Formatter has zero authority over content

---

## Loopback Rules

- If QA fails correctness → send back to question-generator-agent
- If QA fails source fidelity → send back to concept-mapper-agent
- Maximum 2 revision loops before escalation

---

## Status

Full workflow definition pending. To be expanded during agent design phase.
