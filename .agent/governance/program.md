# program.md — Masters Tuition Services: Program Details

**Organization:** Masters Tuition Services LLC (MTS)
**Tagline:** "Making Academic Tuition More Enjoyable, Effective, & Affordable"
**Phone:** +1 704-650-8681

---

## Venues

| Venue | Address |
|-------|---------|
| Venue 1 (Primary) | 10575 Skipping Rock Ln NW, Concord, NC |
| Venue 2 | 1433 Briarfield Dr NW, Concord, NC |

---

## Batches (2025–2026)

### Middle & High School Batch
| Field | Detail |
|-------|--------|
| Grades | 8th–10th Grade (7th Grade on demand) |
| Subjects | Math & ELA (Instructional — naturally prepares for SAT-like tests) |
| | IT & Sciences (Guidance) |
| Grade 8 Schedule | Monday, 5:30 PM – 7:00 PM (Venue 1) |
| Grade 9 Schedule | Monday, 6:30 PM – 8:00 PM (Venue 1) |
| Duration | 90 minutes per grade |
| Main Teacher | Krishna Chaitanya |
| Support Teacher | Ravi Gannamraju |
| Capacity | Only a couple of slots per grade |

### Elementary School Batch
| Field | Detail |
|-------|--------|
| Grades | 2nd–4th Grade (5th Grade on demand) |
| Subjects | Math & ELA |
| Grade 4 Schedule | Monday, 3:30 PM – 4:30 PM (Venue 1) |
| Grade 3 Schedule | Monday, 4:30 PM – 5:30 PM (Venue 1) |
| Grade 2 Schedule | Tuesday, 4:00 PM – 5:00 PM (Venue 2) |
| Duration | 60 minutes per grade |
| Main Teacher | Krishna Chaitanya (Grade 2: Ravi Gannamraju) |
| Support Teacher | Neelima & Ravi Gannamraju |
| Capacity | Only a couple of slots per grade |

*Timings may shift slightly — block 30 minutes before and after each window.

---

## Subjects

| Subject | Grades Served | Mode |
|---------|--------------|------|
| Math | 2nd – 10th Grade | Instructional |
| ELA (English Language Arts) | 2nd – 10th Grade | Instructional |
| IT | 8th – 10th Grade | Guidance |
| Sciences | 8th – 10th Grade | Guidance |

---

## Key Program Features

- Proven overall improvement — builds solid foundations, confidence, self-reliance, and reduced stress
- Carefully crafted group learning setting for academically motivated kids
- Taught by experienced, skillful, and inspired teachers using best practices in teaching methods and child psychology
- Curriculum aligns with NC Common Core | AIG Standards; also serves Home Schools and Charter Schools (e.g., LNC)
- ELA instruction naturally prepares students for SAT-like tests
- Promotes creativity, communication, and confidence

---

## Session Dates (2025–2026)

| Milestone | Date |
|-----------|------|
| Registration By | June 15, 2025 |
| Open House | August 15, 2025 |
| Classes Start | August 18, 2025 |

---

## Session Dates (2024–2025) — Historical Reference

| Milestone | Date |
|-----------|------|
| Last Date for Registration | July 19, 2024 |
| Open House | August 22, 2024 |
| Classes Start | August 26, 2024 |

---

## Special Feature: Teaching Assistant Role

Students who demonstrate:
- High academic performance
- Suitable talent
- Clear intent to contribute

...may be offered a **Teaching Assistant role** with a **monthly part-time salary**.

---

## Teachers

| Name | Role |
|------|------|
| Krishna Chaitanya | Main Teacher (all batches) |
| Neelima | Support Teacher (Elementary) |
| Ravi Gannamraju | Support Teacher (Middle/High); Main Teacher (Grade 2, Venue 2) |

---

## AI-First SDLC

The MTS system is built on an **AI-First Software Development Lifecycle** — every phase of building, testing, observing, and improving is designed to be AI-native, traceable, and self-improving.

### The Loop

```
PRD → Spec → Build → Run → Eval → Observe → Learn → Heal → (back to Spec)
```

No phase is manual-only. Every phase produces artifacts. Every artifact feeds the next phase.

### SDLC Layer Definitions

| Layer | Purpose | Primary Artifact |
|-------|---------|------------------|
| **PRD** | Defines *why* — user stories, personas, success metrics, non-goals | `compact_source-prd.md` |
| **Spec** | Defines *what* — contracts, acceptance criteria, edge case catalogue | `compact_source-spec.md` |
| **Build** | Implements the spec — pipeline code, agents, orchestrator | `src/` modules |
| **Run** | Executes the pipeline against real inputs | `run-telemetry.json`, compaction-report.md |
| **Eval** | Scores output quality across defined dimensions | `eval-score.json`, `eval-report.md` |
| **Observe** | Aggregates run telemetry, identifies trends and regressions | `runs/summary.json`, structured logs |
| **Learn** | Extracts lessons from failures and quality gaps | `learnings.md` (auto-populated) |
| **Heal** | Applies targeted fixes autonomously; escalates when retries fail | Self-healing engine, `bugs.md` |

### Authority Chain (Extended for SDLC)

```
Soul → Constitution → PRD → Spec → Eval → Build → Run → Observe → Learn → Heal
```

- A spec cannot contradict the PRD. A build cannot contradict the spec.
- An eval failure blocks the run from being marked PASS.
- A P1/P2 bug blocks new feature work until resolved.
- Only humans close bugs — agents may only set status to `fix-applied`.

---

## Harness Engineering Standards

Harness engineering is the full set of infrastructure that makes the pipeline **safe to change, safe to run, and safe to trust**.

### Required for Every Feature

| Harness Layer | Standard | Status |
|---------------|----------|--------|
| **Test suite** | pytest — unit tests per module, integration test end-to-end, Claude API mocked | ❌ Missing |
| **Structured logging** | `logging` module, per-run log file, severity levels — no bare `print()` in pipeline | ❌ Missing |
| **Run telemetry** | Machine-readable `run-telemetry.json` in every run folder | ❌ Missing |
| **API resilience** | Exponential backoff + jitter on all Claude API calls, configurable timeout | ❌ Missing |
| **Input validation** | Validate PDF before pipeline starts — readable, not corrupted, not password-protected | ❌ Missing |
| **Evaluator module** | `evaluator.py` — scores output on 5 quality dimensions after every run | ❌ Missing |
| **Quality gate** | Pipeline blocks PASS if eval score below threshold | ❌ Missing |
| **Exception taxonomy** | `src/exceptions.py` — typed exceptions, not bare `Exception` | ❌ Missing |
| **Type checking** | `mypy` enforced in CI | ❌ Missing |
| **CI pipeline** | GitHub Actions: lint, typecheck, test on every push | ❌ Missing |
| **Dependency lock** | `requirements.lock` — exact pinned versions via pip-tools | ❌ Missing |
| **Self-healing engine** | Classify defect → apply repair strategy → retry → escalate | ❌ Missing |
| **Learnings extractor** | Post-eval writer to `learnings.md` — classifies failures by category | ❌ Missing |
| **Golden regression** | Per-exam approved reference outputs; comparator runs on every matching run | ✅ Comparator exists; golden files not yet registered |
| **Compaction report** | Machine-readable structured report per run | ✅ Exists (md only) |
| **Bug tracking** | `bugs.md` with severity, run ID, root cause | ✅ Template exists |
| **Backlog tracking** | `backlog.md` with type, priority, status | ✅ Template exists |

### Eval Quality Dimensions (compact_source)

Every run is scored on these 5 dimensions. Score 1–5 per dimension. Overall PASS requires all ≥ 4.

| # | Dimension | Method | Pass Threshold |
|---|-----------|--------|----------------|
| 1 | **Question count accuracy** | Detected blocks vs known total (if available) | ≥ 95% |
| 2 | **Visual integrity** | Claude vision: no blank pages, no clipped questions, no garbled layout | ≥ 4/5 |
| 3 | **Layout integrity** | Page count in expected range, no oversized blocks, no column overflow | All pass |
| 4 | **File size reasonableness** | Output file within configured size bounds | Within bounds |
| 5 | **Source fidelity** | Claude vision: output images match source visual content | ≥ 4/5 |

### Self-Healing Repair Playbook

| Defect Class | Detection Signal | Repair Strategy | Escalate If |
|---|---|---|---|
| `layout_overflow` | Block extends beyond page boundary | Reduce `scale_factor` by 10% | After 3 retries |
| `question_undercount` | Detected blocks < 80% of expected | Re-run with lower `IMAGE_HEAVY_PAGE_MAX_WORDS` or vision fallback | After 2 retries |
| `blank_output` | Output PDF < 10 KB | Full pipeline re-run | Immediately |
| `file_too_large` | Output > 20 MB | Reduce DPI by 20% | If DPI already at minimum |
| `golden_regression` | Pixel diff above threshold | Log defect, do not auto-repair | Immediately |
