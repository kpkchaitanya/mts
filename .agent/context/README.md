# MTS Context Engineering

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

Context engineering defines **what information an agent needs, in what form,
at what moment** to make the best possible decision.

Prompt engineering focuses on *instructions*.
Context engineering focuses on *the full information environment* — what the
model knows when it acts.

> Context quality often matters more than model size.
> — Holistic AI-Native Cognitive Architecture

---

## 2. Context Engineering Principles

1. **Precision over volume.** Include only what the agent needs right now.
2. **Structured injection.** Use clear section headers to separate context types.
3. **Ground before generate.** Always inject source material before asking for generation.
4. **Governance first.** Always inject relevant governance before task instructions.
5. **Compress when possible.** Summarize stable knowledge; include full detail only when required.

---

## 3. Standard Context Stack

For a typical MTS content generation task, context is injected in this order:

```text
[1] Role Anchor
    → Who is this agent? What is it responsible for?

[2] Governance Scope
    → Relevant constitution principles
    → Relevant persona guidance
    → Relevant safety constraints

[3] Domain Knowledge
    → Ontology concepts relevant to this task
    → Scope-and-sequence for declared grade/subject

[4] Feature Spec
    → The section(s) of the spec governing this task

[5] Source Material
    → The extracted source content to transform or ground against

[6] Task Instruction
    → What to do, in what format, with what constraints

[7] Output Contract
    → What the artifact must look like
    → What fields are required
    → What the QA gate will check
```

---

## 4. Context Templates

### 4.1 compact_source Context Template

```markdown
## Role
You are the [stage-name] agent in the MTS compact_source pipeline.
Your responsibility: [single-sentence responsibility].

## Governance
- Constitution: Correctness is non-negotiable.
- Safety: Block count anomalies trigger WARNING and human gate.
- Spec authority: Follow the spec exactly.

## Spec Reference
[Relevant excerpt from compact_source spec]

## Task
[Specific task instruction]

## Output Contract
Produce: [artifact name and format]
```

### 4.2 QA Agent Context Template

```markdown
## Role
You are the QA agent for Masters Tuition Services.
You evaluate content outputs against the feature spec and eval framework.
Your verdict is final for this run.

## Governance
- Constitution: QA has absolute veto power.
- Safety: CRITICAL failures halt the pipeline immediately.

## Eval Framework
[Relevant eval dimensions and thresholds]

## Spec Acceptance Criteria
[Pasted from feature spec]

## Artifact to Evaluate
[Draft output artifact]

## Output Contract
Produce: eval_report.md
Required fields: overall verdict, dimension scores, findings, recommendations.
```

---

## 5. Context Anti-Patterns

| Anti-Pattern | Problem |
|-------------|---------|
| No role anchor | Model drifts toward generic behavior |
| No spec reference | Model invents beyond spec |
| No grade declared | Content grade-level is inconsistent |
| Injecting full history | Noise degrades output quality |
| No output contract | Output format is unpredictable |
| Injecting raw HTML/PDF | Model cannot parse; use extracted text or images |

---

## 6. Context Compression Strategies

When context windows are constrained:

* **Summarize governance** — inject key principles, not full documents
* **Excerpt the spec** — inject only the section governing the current task
* **Compress source** — summarize source narrative; include verbatim only for quotes/math
* **Use knowledge documents selectively** — inject scope-and-sequence only when generating new content, not when reformatting

---

## 7. Context Inventory

| Context Document | When to Inject |
|-----------------|----------------|
| `governance/constitution.md` | All generation and QA tasks |
| `governance/persona.md` | All generation tasks |
| `governance/safety.md` | Any task with a safety-sensitive gate |
| `governance/glossary.md` | When terminology disambiguation is needed |
| `ontology/mts-ontology.md` | When entity definitions affect the task |
| `knowledge/math-scope-and-sequence.md` | Math content generation |
| `knowledge/ela-scope-and-sequence.md` | ELA content generation |
| `knowledge/pedagogical-guidelines.md` | Worksheet structure and sequencing |
| Feature spec | Always — for the relevant feature |
| `evals/eval.md` | QA tasks |
