# engineering-principles.md — MTS Engineering Principles

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

These principles guide all engineering decisions in the MTS codebase.
They resolve ambiguity and prevent drift when specs are silent.

---

## 2. Principles

---

### P1 — Spec First

Before writing any code, read the relevant spec.
Code that is not grounded in a spec is technical debt by default.

---

### P2 — Correctness Over Cleverness

Simple, readable, correct code is always preferred over
clever, compact, or impressive-looking code.

MTS teachers and future contributors should be able to read and understand
any function within 30 seconds.

---

### P3 — Traceability is Non-Negotiable

Every pipeline output must be traceable to its inputs.
Every failure must leave a diagnostic artifact.

If it ran, it left a trace. No exceptions.

---

### P4 — Tests Are First-Class Citizens

Tests are not afterthoughts. Every non-trivial function has a test.
A function without a test is an untested promise.

Write the test, then the implementation.
At minimum, write the test alongside the implementation.

---

### P5 — Human Gates Protect Quality

Human review gates exist because automation cannot yet exercise
the full judgment required for student-facing content.

Never design around a human gate. Design to make human gates efficient.

---

### P6 — Fail Loudly, Safely

When something is wrong, say so clearly.
Do not silently continue. Do not silently retry.
A quiet failure is the most dangerous failure.

Error messages include:
* What happened
* Where it happened
* What the operator should do next

---

### P7 — Dependency Discipline

Every new dependency is a risk:
* Upgrade burden
* Security exposure
* API changes

Before adding a dependency, ask:
1. Can this be done with the standard library?
2. Is this already in `requirements.txt`?
3. Is this dependency actively maintained?

---

### P8 — Source Fidelity in Generation

When transforming source material, the system compresses, restructures, and
reformats — but never invents.

Generated content is always downstream of source content.
There is no "creative license" in a content transformation pipeline.

---

### P9 — Progressive Enhancement

Build the simplest working version first.
Extend incrementally.
Do not build for hypothetical future requirements.

The best next step is the smallest step that produces real value.

---

### P10 — Shared Knowledge Over Tribal Knowledge

If a decision was made, write it down in `decisions.md`.
If something was learned, write it in `learnings.md`.
If it's a concept, it goes in the glossary.

The system's intelligence must compound — not evaporate when context is lost.

---

## 3. Principle Conflicts

When two principles conflict, resolve by asking:

> Which resolution better serves a student receiving the output?

Student welfare breaks ties.
