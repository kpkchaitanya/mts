# safety.md — MTS Risk & Policy Boundaries

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active
**Authority:** Enforced by constitution.md; no agent or workflow may override.

---

## 1. Purpose

This document defines the safety boundaries, risk categories, and policy constraints
that all MTS agents and workflows MUST respect.

Safety in the MTS context has two dimensions:

1. **Content Safety** — protecting students from harmful, incorrect, or inappropriate content
2. **System Safety** — protecting the integrity, reliability, and auditability of the pipeline

---

## 2. Absolute Prohibitions

The following are **never permitted** under any circumstances:

### Content Prohibitions

* Generating content that is factually incorrect and could harm a student's academic foundation
* Inventing problem solutions not derivable from the source material
* Producing age-inappropriate content (language, themes, cultural references)
* Including personally identifiable information (PII) about real students or families
* Presenting guessed answers as verified answers
* Generating content that discriminates by race, gender, religion, or background
* Using biased examples or stereotyped representations in word problems

### System Prohibitions

* Bypassing the QA gate without explicit `--yes` flag and human awareness
* Silently continuing a pipeline after a detected failure
* Overwriting a prior agent's artifact
* Deleting run artifacts or eval reports
* Proceeding past a detected block count anomaly without surfacing a WARNING
* Running in production without producing a trace artifact

---

## 3. Risk Categories

| Risk Level | Description | Response |
|-----------|-------------|---------|
| **CRITICAL** | Wrong answers, incorrect math, factual errors | Immediate halt; do not deliver |
| **HIGH** | Missing QA gate; spec deviation; grade misalignment | Halt; escalate to human |
| **MEDIUM** | Formatting quality issues; unclear instructions | Flag in eval report; may proceed conditionally |
| **LOW** | Minor style inconsistencies; cosmetic issues | Note in log; do not halt |

---

## 4. Content Safety Rules

### 4.1 Student-Protective Standard

Any content that could:

* Confuse a student about a core concept
* Discourage a student from engaging with the material
* Introduce a misconception that compounds in later grades

...MUST be flagged as CRITICAL and halted, regardless of technical correctness
in other dimensions.

### 4.2 Grade Appropriateness

Content MUST be validated against the declared grade level for:

* Reading complexity (Lexile alignment)
* Vocabulary (no adult idioms or culturally obscure references)
* Cognitive load (single-step problems not assigned to Grade 9 difficulty expectations)
* Emotional tone (no content that might cause anxiety or embarrassment)

### 4.3 Correctness Gate

No answer key, solution set, or graded output may proceed past QA without
mathematical / linguistic correctness verification.

A QA agent that cannot verify correctness MUST escalate — not pass.

---

## 5. System Safety Rules

### 5.1 Auditability

Every run that produces output MUST leave an artifact trail.
Runs that fail before producing output MUST leave a failure log.

No output exists without a traceable origin.

### 5.2 Human Gate Protocol

The human review gate for block detection (Stage 2 of `compact_source_math`)
is a safety mechanism. It exists because:

* A near-empty block set produces a defective product
* Silent defective products reach teachers and students

The gate:
* MUST fire on every interactive run
* MUST display detected block count and source page count
* MUST display WARNING when count is suspiciously low (< 3 blocks, or < 0.5 per page)
* MAY be bypassed only via explicit `--yes` flag in batch/scripted contexts

### 5.3 Retry Limits

Maximum 2 automatic retry loops per pipeline run.
On the third failure, the pipeline MUST halt and escalate to a human.

Silent infinite retries are a safety violation.

### 5.4 Dependency Isolation

No pipeline stage may access external APIs or services
not declared in its feature spec.

Unauthorized external calls (e.g., undeclared web requests) are a safety violation.

---

## 6. Data Handling

### 6.1 Student Data

* No student names, IDs, or performance data is stored in pipeline artifacts.
* Worksheets contain student fields as blank write-in areas only.
* No analytics or tracking of individual student usage.

### 6.2 Source Materials

* Source PDFs are treated as confidential teaching materials.
* They are not transmitted to external services except where explicitly declared in spec.
* Processed outputs (compact PDFs, extracted images) are intermediate artifacts — not published.

---

## 7. Escalation Policy

When any CRITICAL or HIGH risk is detected:

1. **Halt the pipeline** immediately
2. **Write a failure artifact** with: what was detected, at what stage, with what inputs
3. **Display a human-readable error message** with cause and suggested remediation
4. **Do not auto-retry** without human acknowledgment for CRITICAL risks

---

## 8. Safety Review Trigger

The safety policy is reviewed when any of the following occur:

* A defective output reaches a teacher or student
* A new feature spec is introduced that involves external data or APIs
* A pipeline bypassed a safety gate (even legitimately)
* A security or sensitivity concern is raised by any MTS staff member
