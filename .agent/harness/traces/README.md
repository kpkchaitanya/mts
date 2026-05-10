# harness/traces

Execution traces from pipeline runs.

Each trace captures the full context of a run: inputs, decisions, outputs, timing, and eval scores.

## Naming Convention

```text
traces/
└── <feature>/<YYYY-MM-DD>-<run-id>/
    ├── run_log.md
    ├── stage_01_intake.md
    ├── stage_02_detection.md
    ├── stage_03_extraction.md
    ├── stage_04_packing.md
    └── eval_report.md
```

Traces feed the failure archive and replay harness.
