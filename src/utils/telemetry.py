"""
telemetry.py

Platform-level run telemetry for the MTS pipeline system.

Provides RunTelemetry, StageTimings, and Defect dataclasses that capture
execution metadata, per-stage timing, and structured defects for every
pipeline run.  Each feature orchestrator populates and saves an instance;
the platform does not import feature-specific modules.

Output: <stem>_run-telemetry.json written via ArtifactWriter.write().
"""

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StageTimings:
    """
    Captures wall-clock execution time for each pipeline stage.

    Use record() after each stage completes.  total_duration_s should be set
    by the orchestrator once the full run finishes.
    """

    total_duration_s: float = 0.0
    stage_breakdown: dict[str, float] = field(default_factory=dict)

    def record(self, stage_name: str, duration_s: float) -> None:
        """Record the duration for a single stage (rounded to 3 decimal places)."""
        self.stage_breakdown[stage_name] = round(duration_s, 3)


@dataclass
class Defect:
    """
    A structured observation raised during a pipeline run.

    severity:
        "info"    — noteworthy but not a quality concern
        "warning" — reduced quality or unexpected path taken
        "error"   — unrecoverable failure (run likely halted)

    code:
        Short uppercase string identifying the defect type.
        Examples: VISION_FALLBACK_USED, ZERO_BLOCKS_DETECTED,
                  OUTPUT_LARGER_THAN_SOURCE.
    """

    stage: str
    severity: str
    code: str
    message: str
    context: dict = field(default_factory=dict)


@dataclass
class RunTelemetry:
    """
    Immutable snapshot of a single pipeline run.

    Feature orchestrators populate `parameters`, `stages`, `source_stats`,
    `output_stats`, and `verdict` then call save() to persist the record.
    Platform infrastructure (timings, defects) is populated inline.

    Schema version 1.0 fields:
        schema_version  — for forward-compatibility checks
        run_id          — UUID from ArtifactWriter
        feature         — e.g. "compact_source"
        source_file     — basename of the input file
        source_path     — absolute path of the input file
        timestamp_utc   — ISO-8601 UTC timestamp at run start
        parameters      — feature-specific CLI parameters
        stages          — per-stage metadata (feature fills)
        source_stats    — page count, file size, etc.
        output_stats    — page count, file size, etc.
        verdict         — "PASS" | "FAIL"
        timings         — StageTimings instance
        defects         — list of Defect instances
    """

    schema_version: str = "1.0"
    run_id: str = ""
    feature: str = ""
    source_file: str = ""
    source_path: str = ""
    timestamp_utc: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    parameters: dict = field(default_factory=dict)
    stages: dict = field(default_factory=dict)
    source_stats: dict = field(default_factory=dict)
    output_stats: dict = field(default_factory=dict)
    verdict: str = ""
    timings: StageTimings = field(default_factory=StageTimings)
    defects: list[Defect] = field(default_factory=list)

    def add_defect(
        self,
        stage: str,
        severity: str,
        code: str,
        message: str,
        context: dict | None = None,
    ) -> None:
        """Append a structured defect to the run record."""
        self.defects.append(
            Defect(
                stage=stage,
                severity=severity,
                code=code,
                message=message,
                context=context or {},
            )
        )

    def to_dict(self) -> dict:
        """Return the telemetry record as a plain dict ready for JSON serialisation."""
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "feature": self.feature,
            "source_file": self.source_file,
            "source_path": self.source_path,
            "timestamp_utc": self.timestamp_utc,
            "parameters": self.parameters,
            "stages": self.stages,
            "source_stats": self.source_stats,
            "output_stats": self.output_stats,
            "summary": {"verdict": self.verdict},
            "defects": [vars(d) for d in self.defects],
            "timings": {
                "total_duration_s": round(self.timings.total_duration_s, 3),
                "stage_breakdown": self.timings.stage_breakdown,
            },
        }

    def save(self, artifact_writer, stem: str) -> Path:
        """
        Serialise the telemetry record and write it via ArtifactWriter.

        Args:
            artifact_writer: ArtifactWriter instance for the current run.
            stem:            Base name for the output file (e.g. PDF stem).

        Returns:
            Path to the written JSON file.
        """
        content = json.dumps(self.to_dict(), indent=2)
        return artifact_writer.write(f"{stem}_run-telemetry.json", content)
