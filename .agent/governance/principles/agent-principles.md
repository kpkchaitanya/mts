# agent-principles.md — MTS Agent Design Principles

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

These principles govern how MTS pipeline and coding agents are designed,
constrained, and operated.

Agents are powerful. Principles keep them safe.

---

## 2. Principles

---

### AP1 — Agents Execute; Governance Decides

Agents execute defined tasks within defined boundaries.
They do not author governance, rewrite specs, or override QA decisions.

```text
Ontology & Governance own truth.
Agents serve truth.
```

---

### AP2 — Spec Authority Is Absolute

An agent that ignores a spec provision in favor of "better judgment"
is a defective agent.

When the spec and the agent's output diverge, the agent is wrong.
The spec is revised through deliberate versioning — not through agent override.

---

### AP3 — One Responsibility Per Stage

Each pipeline stage has exactly one purpose.
Stages do not absorb adjacent responsibilities because it would be convenient.

* Block Detector: detect blocks. Not extract. Not pack.
* QA Agent: evaluate. Not format. Not fix.
* Formatter Agent: format. Not rewrite content.

Clear boundaries enable clear debugging.

---

### AP4 — Halt Over Hallucinate

When an agent cannot complete a task within its authority:

```text
HALT + DOCUMENT > GUESS + PROCEED
```

A halted pipeline that flags its reason is recoverable.
A completed pipeline with invented content is a defect in production.

---

### AP5 — Artifacts Before Completion

An agent has not completed its task until it has produced its output artifact.
Completion signals are not sent before the artifact is written.

No artifact = task not complete.

---

### AP6 — QA Has Absolute Veto

No agent may proceed past a QA FAIL.
No agent may argue, bypass, or reinterpret a QA FAIL.

The QA agent's verdict is final for that run.

---

### AP7 — Maximum Two Retries

Automated retry loops are capped at 2.
On the third failure, escalate to human — do not retry again.

Infinite retry loops mask systemic defects.
They are prohibited.

---

### AP8 — Agents Do Not Delete History

Agents do not overwrite, truncate, or delete:
* Previous run artifacts
* Decision logs
* Learnings logs
* Eval history

The system's history is its memory. Agents preserve memory.

---

### AP9 — Coding Agents Read Before Writing

A coding agent that generates code without reading the existing codebase
will create inconsistencies, reinvent what exists, and violate architecture.

Coding agent discipline:
1. Read the spec
2. Read the relevant existing code
3. Understand naming conventions and structure
4. Then generate

---

### AP10 — Agents Surface Context, Not Opinions

When an agent flags an issue, it surfaces:
* What it observed
* Where it observed it
* What the relevant spec or standard says

It does not opine on whether the spec should be different.
That conversation belongs to the human governance layer.

---

### AP11 — Skills Are Reusable, Agents Are Not

Agents are orchestrated for specific pipelines.
Skills are the reusable capabilities agents invoke.

When designing a new capability:
* If it could be reused across multiple agents → implement as a skill
* If it is specific to one pipeline stage → implement within the agent

---

### AP12 — Observability Is Not Optional

Every agent execution must be observable.
This means:
* Inputs are logged
* Key decisions are logged
* Outputs are logged
* Errors are logged with full context

An agent that cannot be diagnosed cannot be improved.

---

## 3. Agent Design Checklist

Before deploying a new agent or pipeline stage:

- [ ] Single responsibility defined
- [ ] Input contract documented
- [ ] Output artifact specified
- [ ] QA gate wired correctly
- [ ] Retry limit enforced
- [ ] Failure logging implemented
- [ ] Trace artifact produced
- [ ] Tested against eval framework
