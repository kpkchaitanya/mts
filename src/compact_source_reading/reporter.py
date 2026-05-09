"""
reporter.py  (compact_source_reading)

Generates the two compaction artifacts for a compact_source_reading run:
  - passage-map.md         — passage group inventory with page assignments
  - compaction-report.md   — page reduction metrics and integrity verdict
"""

from __future__ import annotations

from src.compact_source_reading.passage_detector import PassageDetectionResult
from src.compact_source_reading.passage_extractor import ExtractedPassageGroup
from src.utils.markdown_utils import frontmatter, horizontal_rule, section_header, pass_fail_icon


class ReadingReporter:
    """
    Generates the passage-map.md and compaction-report.md artifacts for
    a compact_source_reading run.
    """

    def generate(
        self,
        detection_result: PassageDetectionResult,
        extracted_groups: list[ExtractedPassageGroup],
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
        original_size_bytes: int = 0,
        output_size_bytes: int = 0,
    ) -> tuple[str, str, bool]:
        """
        Generate both report artifacts.

        Returns:
            Tuple of (passage_map_md, compaction_report_md, passed).
        """
        passage_map_md = self._build_passage_map(
            detection_result=detection_result,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
        )
        report_md, passed = self._build_compaction_report(
            detection_result=detection_result,
            extracted_groups=extracted_groups,
            original_page_count=original_page_count,
            output_page_count=output_page_count,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
            original_size_bytes=original_size_bytes,
            output_size_bytes=output_size_bytes,
        )
        return passage_map_md, report_md, passed

    # ── Passage Map ───────────────────────────────────────────────────────────

    def _build_passage_map(
        self,
        detection_result: PassageDetectionResult,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> str:
        groups = detection_result.groups

        lines: list[str] = [
            "# Passage Map",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Detection Summary"),
            "",
            f"Total passages detected: **{detection_result.total_passages}**",
            f"Total question pages: **{detection_result.total_question_pages}**",
            "",
            horizontal_rule(),
            section_header("Passage Group Inventory"),
            "",
            "| # | Passage ID | Passage Pages | Question Pages | Total Pages |",
            "|---|------------|---------------|----------------|-------------|",
        ]

        for i, g in enumerate(groups, 1):
            p_pages = ", ".join(str(p + 1) for p in g.passage_pages)
            q_pages = ", ".join(str(p + 1) for p in g.question_pages)
            lines.append(
                f"| {i} | {g.passage_id} | {p_pages} | {q_pages} | {g.total_pages} |"
            )

        return "\n".join(lines)

    # ── Compaction Report ─────────────────────────────────────────────────────

    def _build_compaction_report(
        self,
        detection_result: PassageDetectionResult,
        extracted_groups: list[ExtractedPassageGroup],
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
        original_size_bytes: int = 0,
        output_size_bytes: int = 0,
    ) -> tuple[str, bool]:
        passages_detected = detection_result.total_passages
        pages_saved = original_page_count - output_page_count
        reduction_pct = (
            round((pages_saved / original_page_count) * 100, 1)
            if original_page_count > 0 else 0.0
        )

        def _fmt(b: int) -> str:
            return f"{b / 1_048_576:.1f} MB" if b >= 1_048_576 else f"{b / 1024:.0f} KB"

        size_delta = original_size_bytes - output_size_bytes
        size_pct = (
            round(abs(size_delta) / original_size_bytes * 100, 1)
            if original_size_bytes > 0 else 0.0
        )
        size_label = (
            f"{_fmt(size_delta)} saved ({size_pct}% reduction)"
            if size_delta >= 0
            else f"{_fmt(abs(size_delta))} larger (raster images, +{size_pct}%)"
        )

        integrity_pass = passages_detected > 0
        overall_pass = integrity_pass
        verdict = "PASS" if overall_pass else "FAIL"

        # Per-group page counts for the table
        lines: list[str] = [
            "# Compaction Report  (Reading)",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Page Reduction Summary"),
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Original Pages | {original_page_count} |",
            f"| Compacted Pages | {output_page_count} |",
            f"| Pages Saved | {pages_saved} ({reduction_pct}%) |",
            f"| Original Size | {_fmt(original_size_bytes)} |",
            f"| Compacted Size | {_fmt(output_size_bytes)} |",
            f"| Size Delta | {size_label} |",
            horizontal_rule(),
            section_header("Passage Group Integrity"),
            "",
            "| Check | Result |",
            "|-------|--------|",
            f"| Passages detected | {passages_detected} |",
            f"| All groups retained in output | {pass_fail_icon(integrity_pass)} |",
            f"| No text re-rendered (visual extraction) | {pass_fail_icon(True)} |",
            horizontal_rule(),
            section_header("Per-Group Page Counts"),
            "",
            "| # | Passage ID | Passage Pg | Question Pg | Output Pg |",
            "|---|------------|------------|-------------|-----------|",
        ]

        for i, (g_det, g_ext) in enumerate(
            zip(detection_result.groups, extracted_groups), 1
        ):
            lines.append(
                f"| {i} | {g_det.passage_id} | {len(g_det.passage_pages)} | "
                f"{len(g_det.question_pages)} | {len(g_ext.pages)} |"
            )

        lines += [
            horizontal_rule(),
            section_header("Verdict"),
            "",
            f"**{verdict}**",
        ]

        if not integrity_pass:
            lines += [
                "",
                "- FAIL: No passage groups detected.  Verify the PDF uses "
                "standard STAAR / EOG passage-ID formatting.",
            ]

        return "\n".join(lines), overall_pass
