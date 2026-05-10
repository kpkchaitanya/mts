# prompting-principles.md — MTS Prompting Principles

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

These principles govern how MTS system prompts, agent prompts, and
context injections are constructed, tested, and maintained.

Context quality determines output quality.
These principles protect that chain.

---

## 2. Principles

---

### PP1 — Context Before Instruction

Always load the model with relevant context before issuing instructions.

Bad:
```
Generate a Grade 5 math worksheet on fractions.
```

Better:
```
[Governance: constitution.md]
[Spec: math_worksheet_generation_from_source v3]
[Source: <extracted content>]

Using the above source and spec, generate a Grade 5 math worksheet on fractions.
```

---

### PP2 — Role Before Task

Establish the agent's role before describing the task.
Role-anchored models produce more consistent outputs.

```
You are the QA agent for Masters Tuition Services.
Your responsibility is to evaluate the attached worksheet draft
against the acceptance criteria in the spec below.
```

---

### PP3 — Spec Authority Is Explicit

When a spec governs the task, say so explicitly in the prompt.

```
The attached spec is authoritative. Follow it exactly.
Do not add, omit, or deviate from its requirements.
If the spec is ambiguous, flag the ambiguity — do not resolve it unilaterally.
```

---

### PP4 — Grade Level Is Always Named

Never assume grade level from context.
Always name it explicitly.

```
Grade level: 5th Grade
All vocabulary, sentence complexity, and cognitive load
must be appropriate for a 5th-grade student.
```

---

### PP5 — Hallucination Fences

For source-grounded tasks, install an explicit anti-hallucination instruction:

```
Use only information explicitly present in the source material provided.
Do not introduce concepts, vocabulary, or facts not found in the source.
If the source does not contain sufficient material, say so.
```

---

### PP6 — Output Format is Prescribed

Never leave output format ambiguous.
Specify structure, headers, and format explicitly.

```
Output format:
- Section 1: [title]
  [content]
- Section 2: [title]
  [content]
Do not include explanatory prose outside these sections.
```

---

### PP7 — Prompts Are Versioned

Prompts that govern pipeline behavior are not ad hoc.
They live in structured files, are versioned, and are traceable.

Prompt changes are recorded in `decisions.md` with rationale.

---

### PP8 — Test Before Deploy

Every prompt used in a production pipeline must be evaluated
against the eval framework before it is deployed.

A prompt that has not been evaled is an untested assumption.

---

### PP9 — Compress Context Thoughtfully

More context is not always better.
Irrelevant context increases noise and can degrade output quality.

Include:
* Governance scope relevant to the task
* The source material
* The spec section that applies
* The output format

Exclude:
* Historical run artifacts unless directly relevant
* Lengthy preamble the model does not need

---

### PP10 — Eval the Prompt, Not Just the Output

When an output fails, the prompt is a suspect.

Ask:
* Was the role established clearly?
* Was the spec authority declared?
* Was grade level named explicitly?
* Were anti-hallucination fences installed?
* Was the output format prescribed?

Prompt failures produce output failures. Trace back.

---

## 3. Prompt Review Checklist

Before deploying a new or modified prompt:

- [ ] Role established before task
- [ ] Spec authority declared
- [ ] Grade level named explicitly (if applicable)
- [ ] Anti-hallucination fence installed (if source-grounded)
- [ ] Output format prescribed
- [ ] Prompt version recorded
- [ ] Eval run against at least one representative input
