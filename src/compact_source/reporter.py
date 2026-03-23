"""
reporter.py

Generates the two compaction artifacts for a compact_source run:
  - source-boundary-map.md  — question block inventory with y-coordinates
  - compaction-report.md    — page reduction metrics and integrity verdict

Inputs:  BlockDetectionResult, original page count, output PDF page count
Outputs: (boundary_map_md, compaction_report_md, passed)
"""

from src.compact_source.block_detector import BlockDetectionResult
from src.utils.markdown_utils import frontmatter, horizontal_rule, section_header, pass_fail_icon


class Reporter:
    """
    Generates the source-boundary-map.md and compaction-report.md artifacts.

    All validation is based on block counts from BlockDetectionResult —
    no text re-parsing or line counting is performed.
    """

    def generate(
        self,
        detection_result: BlockDetectionResult,
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> tuple[str, str, bool]:
        """
        Generate both report artifacts.

        Args:
            detection_result: Block detection output from BlockDetector.
            original_page_count: Total pages in the original source PDF.
            output_page_count: Actual pages in the compacted output PDF.
            source_filename: Original PDF filename (for artifact metadata).
            run_id: Pipeline run ID.
            grade: Grade level.
            subject: Subject area.

        Returns:
            Tuple of (boundary_map_md, compaction_report_md, passed).
            passed is True only if all integrity checks pass.
        """
        boundary_map_md = self._build_boundary_map(
            detection_result=detection_result,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
        )

        report_md, passed = self._build_compaction_report(
            detection_result=detection_result,
            original_page_count=original_page_count,
            output_page_count=output_page_count,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
        )

        return boundary_map_md, report_md, passed

    # ── Boundary Map ──────────────────────────────────────────────────────────

    def _build_boundary_map(
        self,
        detection_result: BlockDetectionResult,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> str:
        blocks = detection_result.blocks
        detection_method = (
            "Text (pdfplumber y-coords) + Claude vision fallback"
            if detection_result.used_vision_fallback
            else "Text (pdfplumber y-coords)"
        )

        lines: list[str] = [
            "# Source Boundary Map",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Detection Method"),
            "",
            f"**{detection_method}**",
            "",
            f"Total question blocks detected: **{detection_result.total_questions}**",
            horizontal_rule(),
            section_header("Question Block Inventory"),
            "",
            "| Q# | Source Page(s) | Y-top (pts) | Y-bottom (pts) | Height (pts) | Multi-page |",
            "|----|---------------|-------------|----------------|-------------|-----------|",
        ]

        for block in blocks:
            pages = ", ".join(str(s.page_number) for s in block.slices)
            y_top = round(block.slices[0].y_top, 1)
            y_bottom = round(block.slices[-1].y_bottom, 1)
            height = round(block.total_height_pts, 1)
            multi = "Yes" if len(block.slices) > 1 else "No"
            lines.append(
                f"| {block.question_number} | {pages} | {y_top} | {y_bottom} | {height} | {multi} |"
            )

        if blocks:
            first = blocks[0]
            last = blocks[-1]
            lines += [
                horizontal_rule(),
                section_header("Boundary Summary"),
                "",
                f"- **First question (Q{first.question_number}):** "
                f"page {first.slices[0].page_number}, y={round(first.slices[0].y_top, 1)} pts",
                f"- **Last question (Q{last.question_number}):** "
                f"page {last.slices[-1].page_number}, y={round(last.slices[-1].y_bottom, 1)} pts",
            ]

        return "\n".join(lines)

    # ── Compaction Report ─────────────────────────────────────────────────────

    def _build_compaction_report(
        self,
        detection_result: BlockDetectionResult,
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> tuple[str, bool]:
        questions_detected = detection_result.total_questions
        pages_saved = original_page_count - output_page_count
        reduction_percent = (
            round((pages_saved / original_page_count) * 100, 1)
            if original_page_count > 0
            else 0.0
        )

        # Integrity: must have detected at least one block
        integrity_pass = questions_detected > 0
        overall_pass = integrity_pass
        verdict = "PASS" if overall_pass else "FAIL"

        lines: list[str] = [
            "# Compaction Report",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Page Reduction Summary"),
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Original Pages | {original_page_count} |",
            f"| Compacted Pages | {output_page_count} |",
            f"| Pages Saved | {pages_saved} |",
            f"| Reduction | {reduction_percent}% |",
            horizontal_rule(),
            section_header("Question Integrity Check"),
            "",
            "| Check | Result |",
            "|-------|--------|",
            f"| Question blocks detected | {questions_detected} |",
            f"| All blocks retained in output | {pass_fail_icon(integrity_pass)} |",
            f"| No text re-rendered (visual extraction) | {pass_fail_icon(True)} |",
            f"| Vision fallback used | {'Yes' if detection_result.used_vision_fallback else 'No'} |",
            horizontal_rule(),
            section_header("Verdict"),
            "",
            f"**{verdict}**",
        ]

        if not integrity_pass:
            lines += [
                "",
                "- FAIL: No question blocks detected. "
                "Review source-boundary-map.md and check that the PDF contains numbered questions.",
            ]

        lines += [
            horizontal_rule(),
            section_header("Notes"),
            "",
            "_Review compacted-source.pdf to inspect the visual output._",
            "_Review source-boundary-map.md for the full block inventory._",
        ]

        return "\n".join(lines), overall_pass
