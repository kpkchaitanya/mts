# platform-observability-spec.md

**Theme:** Platform
**Sub-theme:** Observability
**Version:** v1
**Status:** Active
**Date:** 2026-04-26
**Applies To:** All MTS pipeline features (`compact_source`, `generate_worksheet`, and all future features)

---

## 1. Purpose

Every MTS pipeline run MUST produce a machine-readable record of what happened. This enables:

- Downstream tooling (evaluator, self-healing engine, learnings extractor) to read structured input
- Debugging without re-running the pipeline
- Trend analysis across runs (is the pipeline getting faster or slower? are defects increasing?)
- Quality gates that can block a PASS verdict based on measured data

This spec defines the **contract** — what artifacts every run MUST produce and what minimum fields they MUST contain. Implementation details (class design, logging wiring) are in [platform-observability-design.md](platform-observability-design.md).

---

## 2. Scope

| In Scope | Out of Scope |
|----------|-------------|
| Per-run telemetry JSON | Log aggregation to external systems |
| Per-run log file | Structured JSON log lines |
| Batch summary JSON (folder-mode runs) | Real-time log streaming |
| Python `logging` module replacing bare `print()` | Third-party APM / tracing tools |

---

## 3. Observability Artifacts Contract

Every pipeline run MUST produce the following artifacts in the run's artifact folder:

### 3.1 `{stem}_run-telemetry.json`

A machine-readable summary of a single-file pipeline run. Written at the end of the run, before exit.

**Required top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Always `"1.0"` |
| `run_id` | string | Timestamp-based unique ID (format `YYYYMMDD_HHMMSS`) |
| `feature` | string | Feature name, e.g. `"compact_source"` |
| `source_file` | string | Filename of the input (PDF, JSON, etc.) |
| `source_path` | string | Relative path from workspace root |
| `timestamp_utc` | string | ISO 8601 UTC timestamp of run start |
| `parameters` | object | Feature-specific input parameters (see §4) |
| `stages` | object | Per-stage timing and result data (see §4) |
| `source_stats` | object | Input file stats (page count, size in bytes) |
| `output_stats` | object | Output file stats (page count, size in bytes, path) |
| `summary` | object | Computed summary (delta stats, `verdict`) |
| `defects` | array | Zero or more defect entries (see §3.3) |
| `timings` | object | `total_duration_s` and per-stage breakdown |

**Required `summary` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verdict` | string | `"PASS"` or `"FAIL"` — always present, never null |

**Testable claim:** Any run that exits with code 0 MUST have `verdict = "PASS"`. Any run that exits with code 1 MUST have `verdict = "FAIL"`.

### 3.2 `run.log`

A plain-text log file capturing all pipeline events for the run at DEBUG level and above.

**Requirements:**
- Written to the artifact bin folder (`{run_path}/bin/run.log`)
- For batch (folder-mode) runs, a single shared `run.log` covers all files processed in that run
- Log lines MUST include: timestamp, log level, logger name, message
- Format: `YYYY-MM-DD HH:MM:SS,mmm [LEVEL] module.name — message`
- The file MUST exist even if the pipeline raises an exception (write in a `finally` block)

**Testable claim:** After any run, `run.log` exists in the artifact bin folder and contains at least one `[INFO]` line per pipeline stage.

### 3.3 Defect Entry Schema

`defects` is an array in `run-telemetry.json`. Each entry MUST contain:

| Field | Type | Constraints |
|-------|------|-------------|
| `stage` | string | Name of the stage where defect occurred |
| `severity` | string | `"info"` \| `"warning"` \| `"error"` |
| `code` | string | Uppercase snake_case, e.g. `"VISION_FALLBACK_USED"` |
| `message` | string | Human-readable description |
| `context` | object | Optional additional diagnostic data |

**Defect code conventions:**
- Codes are permanent identifiers — once assigned, never renamed
- Codes are used by the Phase 5 self-healing engine for programmatic matching
- Codes must be unique within a feature's stage namespace

### 3.4 `batch-telemetry.json` (batch runs only)

Written by the orchestrator at the end of a folder-mode run, after all per-file runs complete.

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Always `"1.0"` |
| `run_id` | string | Shared run ID for the batch |
| `feature` | string | Feature name |
| `timestamp_utc` | string | ISO 8601 UTC timestamp |
| `source_folder` | string | Path to input folder |
| `files_processed` | int | Total PDFs attempted |
| `files_passed` | int | Runs with `verdict = "PASS"` |
| `files_failed` | int | Runs with `verdict = "FAIL"` |
| `total_duration_s` | float | Wall-clock time for the entire batch |
| `runs` | array | One summary entry per file (see §3.4.1) |

**3.4.1 Per-file summary row in `runs` array:**

| Field | Type |
|-------|------|
| `source_file` | string |
| `verdict` | string |
| `total_duration_s` | float |

Features may add additional per-file fields (e.g. `blocks_detected` for `compact_source`).

---

## 4. Feature-Specific Telemetry Extensions

Each feature extends the base schema with feature-specific `parameters` and `stages` fields. The platform schema defines the envelope; features fill the content.

### 4.1 `compact_source` Extensions

**`parameters` object:**

| Field | Type |
|-------|------|
| `grade` | int |
| `subject` | string |
| `columns` | int |
| `scale_factor` | float |
| `max_pages` | int \| null |
| `max_block_pages` | int |
| `problem_list` | string |

**`stages` object:**

| Key | Fields |
|-----|--------|
| `format_detection` | `format_detected`, `avg_words_per_page`, `sample_pages_used`, `duration_s` |
| `block_detection` | `blocks_detected`, `blocks_after_filter`, `used_vision_fallback`, `answer_key_fence_page`, `duration_s` |
| `block_extraction` | `blocks_extracted`, `duration_s` |
| `page_packing` | `input_blocks`, `output_pages`, `duration_s` |
| `reporting` | `duration_s` |

**`summary` additional fields:**

| Field | Type |
|-------|------|
| `pages_saved` | int |
| `page_reduction_pct` | float |
| `size_saved_bytes` | int |
| `size_reduction_pct` | float |

---

## 5. Logging Contract

### 5.1 No Bare `print()` in Pipeline Code

After this spec is implemented, no bare `print()` calls MUST exist in:
- `src/orchestrator.py`
- `src/compact_source/*.py`
- `src/utils/*.py`

All console output MUST go through a named logger.

**Testable claim:** `grep -r "print(" src/` returns 0 results (excluding test files and docstrings).

### 5.2 Log Level Conventions

| Level | Used For | Example |
|-------|---------|---------|
| `DEBUG` | Per-item detail — page word counts, block coordinates | `"Page 3: 4 words, included as image_heavy block"` |
| `INFO` | Stage lifecycle — start, end, summary counts | `"[1/5] Format detection complete: image_heavy"` |
| `WARNING` | Recoverable anomalies — fallback activated, unexpected structure | `"Vision fallback activated: only 2 blocks found by text scan"` |
| `ERROR` | Exceptions before re-raise | `"BlockDetectionError on page 7: ..."` |

### 5.3 Terminal Output Compatibility

The `StreamHandler` MUST produce terminal output visually identical to the current `print()`-based output. Users MUST NOT see any change in what appears on screen.

---

## 6. Implementation Rules

1. `telemetry.py` MUST live in `src/utils/` — it is platform infrastructure, not feature-specific
2. `RunTelemetry` is a generic container; feature-specific fields go in nested `parameters` and `stages` dicts
3. The logging root logger name is `"mts"`; all module loggers use `logging.getLogger(__name__)`
4. Handlers are attached at run start and detached at run end — never at module import time
5. `run.log` is always written via a `finally` block — it MUST exist even when the pipeline fails

---

## 7. Testability Checklist

| ID | Claim | Test Case |
|----|-------|-----------|
| TC-OBS-01 | `{stem}_run-telemetry.json` exists after every successful run | File existence check |
| TC-OBS-02 | `run-telemetry.json` has all required top-level fields (§3.1) | JSON schema validation |
| TC-OBS-03 | `summary.verdict` is `"PASS"` when exit code is 0 | Read JSON, check field |
| TC-OBS-04 | `summary.verdict` is `"FAIL"` when exit code is 1 | Read JSON, check field |
| TC-OBS-05 | `timings.total_duration_s` ≥ sum of stage durations | Arithmetic check |
| TC-OBS-06 | `run.log` exists after every run (including failed runs) | File existence check |
| TC-OBS-07 | `run.log` has at least one `[INFO]` line per stage | Grep for stage markers |
| TC-OBS-08 | No bare `print()` in `src/` pipeline code | `grep -r "print(" src/` == 0 |
| TC-OBS-09 | Batch run produces exactly one `run.log` | Count files in bin/ |
| TC-OBS-10 | Batch run produces `batch-telemetry.json` with correct `files_processed` | Read JSON, compare to folder PDF count |
| TC-OBS-11 | Two sequential runs do not duplicate log lines (handler teardown works) | Count known marker occurrences |
| TC-OBS-12 | `defects` array is present and is an array (may be empty) | JSON schema validation |
