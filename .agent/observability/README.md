# MTS Observability

**Organization:** Masters Tuition Services LLC
**Version:** v1
**Status:** Active

---

## 1. Purpose

Observability is how the MTS system **develops self-awareness** — the ability to
understand its own behavior, diagnose its failures, and improve its quality.

Traditional software observability tracks: logs, metrics, traces.

AI-native observability adds: prompts, context windows, reasoning traces,
eval scores, hallucination events, and repair history.

> "Observability without evals lacks judgment.
> Evals without observability lack diagnosis.
> Together they create Cognitive Quality Intelligence."
> — Holistic AI-Native Cognitive Architecture

---

## 2. What MTS Observability Tracks

### 2.1 Execution Observability

| Track | What It Captures |
|-------|-----------------|
| Run Log | What pipeline ran, with what inputs, at what time |
| Stage Trace | What each stage received, decided, and produced |
| Timing | How long each stage took; total run time |
| Errors | What failed, where, with what error message |
| Artifacts | What files were produced and where |

### 2.2 Content Observability

| Track | What It Captures |
|-------|-----------------|
| Block Count | How many blocks were detected vs expected |
| Page Reduction | Output page count vs source page count |
| Scale Factor Used | What scale factor was applied |
| Problem List | Which problems were included/excluded |

### 2.3 Quality Observability

| Track | What It Captures |
|-------|-----------------|
| Eval Scores | Scores per eval dimension, per run |
| QA Verdict | PASS / FAIL / REVIEW per run |
| Regression Status | Pass/fail on regression case suite |
| Benchmark Trend | Quality metrics over time |

### 2.4 AI Observability *(for LLM-involved stages)*

| Track | What It Captures |
|-------|-----------------|
| Prompt Used | Which prompt version was injected |
| Context Injected | What context documents were included |
| Model Used | Which model/API was called |
| Token Usage | Input and output token counts |
| Latency | API response time |
| Hallucination Flags | Any content flagged as beyond source |

---

## 3. Observability Artifacts

Every pipeline run MUST produce:

| Artifact | Content | Location |
|---------|---------|---------|
| `run_log.md` | Execution summary | `reports/` or `harness/traces/` |
| `eval_report.md` | Quality scores and findings | `harness/evals/` |
| `failure_log.md` | Failure detail (if failed) | `harness/failures/` |

---

## 4. Observability Signals by Pipeline Stage

### compact_source_math

| Stage | Observable Signals |
|-------|-------------------|
| Block Detection | Pages processed; blocks found per page; total block count; anomaly flag |
| Human Gate | Operator confirmed/bypassed; time at gate |
| Block Extraction | Blocks extracted; any extraction errors |
| PDF Packing | Output page count; scale factor applied; columns used |

### math_worksheet_generation *(planned)*

| Stage | Observable Signals |
|-------|-------------------|
| Source Ingestion | Pages read; content extracted; tokens used |
| Generation | Prompt version; model; latency; tokens; draft length |
| QA | Dimension scores; verdict; findings count |
| Formatting | Output format; page count |

---

## 5. Observability Standards

* All timestamps are in ISO 8601 format (UTC).
* All artifact paths are absolute or workspace-rooted relative paths.
* All eval scores include the threshold they are compared against.
* All anomaly warnings include: what was detected, what was expected, severity.

---

## 6. Observability Maturity Levels

| Level | Description | MTS Current State |
|-------|-------------|-------------------|
| L1 — Logging | Run logs produced | ✅ Active |
| L2 — Eval Coverage | Eval reports per run | ✅ Active |
| L3 — Trend Tracking | Quality metrics over time | 🔲 Planned |
| L4 — Anomaly Alerting | Automatic detection of quality regression | 🔲 Planned |
| L5 — Self-Diagnosis | System identifies root cause of failures | 🔲 Future |

---

## 7. Relationship to Harness

Observability and harness are tightly coupled:

```text
Pipeline Run
     ↓
Observability captures signals + artifacts
     ↓
Harness stores and organizes artifacts
     ↓
Evals score quality
     ↓
Failures feed failure archive
     ↓
Repair pipeline resolves failures
     ↓
Regression harness prevents re-introduction
     ↓
Quality intelligence compounds over time
```
