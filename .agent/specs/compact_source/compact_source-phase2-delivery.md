# compact_source — Phase 2 Delivery: Observability

> **Superseded.** Content merged into [compact_source-design.md](compact_source-design.md) §6.1.

---

## 1. Platform Contract (pointer)

This delivery implements the full platform observability contract.

| Document | Covers |
|----------|--------|
| [platform-observability-spec.md §3](../platform/observability/platform-observability-spec.md) | Required artifact fields, defect entry schema, logging contract |
| [platform-observability-spec.md §4.1](../platform/observability/platform-observability-spec.md) | `compact_source`-specific `parameters`, `stages`, and `summary` field definitions |
| [platform-observability-design.md](../platform/observability/platform-observability-design.md) | `RunTelemetry` class, logging wiring, handler lifecycle, `telemetry.py` location |

All 12 platform testability claims (TC-OBS-01 through TC-OBS-12) apply to this delivery without modification.

---

## 2. compact_source Modules Affected

The new `src/utils/telemetry.py` platform module and logging infrastructure are defined in the platform design. What is unique to this delivery is which compact_source modules need their `print()` calls replaced:

| Module | Change |
|--------|--------|
| `src/orchestrator.py` | Wrap each stage call with `time.perf_counter()`; populate and save `RunTelemetry`; write `batch-telemetry.json` in folder mode; replace all `print()` |
| `src/compact_source/block_detector.py` | Replace `print()` → `logger.debug/info/warning` |
| `src/compact_source/block_extractor.py` | Replace `print()` → `logger.debug/info` |
| `src/compact_source/pdf_packer.py` | Replace `print()` → `logger.debug/info` |
| `src/compact_source/reporter.py` | Replace `print()` → `logger.debug/info` |

No public function signatures change. No callers break.

---

## 3. compact_source Defect Codes

Codes that `compact_source` will emit into the `defects` array. Phase 5 self-healing pattern-matches on these. Codes are permanent — never renamed once assigned.

| Code | Stage | Severity | Trigger |
|------|-------|----------|---------|
| `VISION_FALLBACK_USED` | `block_detection` | `warning` | Text scan found < 3 blocks; Claude vision activated |
| `ZERO_BLOCKS_DETECTED` | `block_detection` | `error` | No question blocks found after all detection paths |
| `ANSWER_KEY_FENCE_NOT_FOUND` | `block_detection` | `info` | No answer key page found; all pages included |
| `OUTPUT_LARGER_THAN_SOURCE` | `reporting` | `info` | Output PDF is larger than source file |

---

## 4. Acceptance Criteria (compact_source-specific)

The full platform AC list is in the platform spec (TC-OBS-01 through TC-OBS-12). The following are additional criteria unique to compact_source.

| ID | Criterion |
|----|-----------|
| AC-CS-01 | `{stem}_run-telemetry.json` contains correct `stages.format_detection.format_detected` for a known EOG PDF (`"image_heavy"`) |
| AC-CS-02 | `{stem}_run-telemetry.json` contains correct `stages.block_detection.blocks_detected` matching golden counts (gr_3=40, gr_4=50, gr_5=50) |
| AC-CS-03 | `defects` array contains `VISION_FALLBACK_USED` entry when vision fallback was activated |
| AC-CS-04 | `summary.pages_saved` equals source page count minus output page count |
| AC-CS-05 | `batch-telemetry.json.runs` has one entry per PDF file in the folder |

---

## 5. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| Q1 | Should `run.log` have a max size cap (e.g. 10 MB) for very large batches? | Ravi | Open |
| Q2 | Should `format_detection` timing be broken out of `block_detection` timing, or is lumping them together sufficient? | Tech | Start lumped; split if per-stage granularity is needed by evaluator |
