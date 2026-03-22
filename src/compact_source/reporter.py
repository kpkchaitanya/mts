"""
reporter.py

Generates the compaction-report.md artifact for a compact_source run.
Validates that all questions were retained and documents page reduction metrics.
This is Step 4 (final step) of the compact_source pipeline.

Inputs:  Compacted markdown, BoundaryResult, original and estimated page counts
Outputs: compaction-report.md artifact string, overall pass/fail boolean
"""

import re

from src.compact_source.boundary_detector import BoundaryResult
from src.utils.markdown_utils import frontmatter, horizontal_rule, section_header, pass_fail_icon


# Pattern used to count numbered questions in the compacted markdown output.
# Must be consistent with ANY_QUESTION_PATTERN in boundary_detector.py.
QUESTION_COUNT_PATTERN: str = r"^\s*\d+[\.\)]\s+\S"


class Reporter:
    """
    Generates the compaction report and determines the overall pass/fail verdict.

    Responsibilities:
    - Count numbered questions in the compacted output
    - Compare against the expected count from BoundaryResult
    - Calculate page reduction metrics
    - Produce a structured, readable markdown report

    Does NOT modify content — this is a read-only validation step.
    """

    def generate(
        self,
        compacted_markdown: str,
        boundaries: BoundaryResult,
        original_page_count: int,
        compacted_page_estimate: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> tuple[str, bool]:
        """
        Generate the compaction report and return the overall pass/fail result.

        Args:
            compacted_markdown: Full compacted content from the Compactor step.
            boundaries: Boundary detection result containing expected question count.
            original_page_count: Total pages in the original PDF.
            compacted_page_estimate: Estimated pages in the compacted output.
            source_filename: Original PDF filename.
            run_id: Current pipeline run ID.
            grade: Grade level of the exam.
            subject: Subject area.

        Returns:
            Tuple of (report_markdown_string, passed).
            passed is True only if all integrity checks pass.
        """
        questions_in_output = self._count_questions(compacted_markdown)
        questions_in_source = boundaries.total_questions

        # Core integrity check: every question must be present in the output
        integrity_pass = (questions_in_output == questions_in_source)

        # Calculate page reduction metrics
        pages_saved = original_page_count - compacted_page_estimate
        reduction_percent = (
            round((pages_saved / original_page_count) * 100, 1)
            if original_page_count > 0
            else 0.0
        )

        overall_pass = integrity_pass

        report_md = self._build_report(
            run_id=run_id,
            source_filename=source_filename,
            grade=grade,
            subject=subject,
            questions_in_source=questions_in_source,
            questions_in_output=questions_in_output,
            original_pages=original_page_count,
            compacted_pages=compacted_page_estimate,
            pages_saved=pages_saved,
            reduction_percent=reduction_percent,
            integrity_pass=integrity_pass,
            overall_pass=overall_pass,
        )

        return report_md, overall_pass

    def _count_questions(self, markdown: str) -> int:
        """
        Count the number of numbered question markers in the compacted markdown.

        Uses the same pattern as boundary_detector.py for consistency.

        Args:
            markdown: The full compacted markdown content.

        Returns:
            Count of numbered question markers found (e.g., "1.", "2)", "3.").
        """
        pattern = re.compile(QUESTION_COUNT_PATTERN, re.MULTILINE)
        return len(pattern.findall(markdown))

    def _build_report(
        self,
        run_id: str,
        source_filename: str,
        grade: int,
        subject: str,
        questions_in_source: int,
        questions_in_output: int,
        original_pages: int,
        compacted_pages: int,
        pages_saved: int,
        reduction_percent: float,
        integrity_pass: bool,
        overall_pass: bool,
    ) -> str:
        """
        Assemble the full compaction-report.md markdown string.

        Args:
            (All parameters correspond to report fields — see generate() docstring.)

        Returns:
            Complete markdown string for the compaction report artifact.
        """
        verdict = "✅ PASS" if overall_pass else "❌ FAIL"

        # Build failure details only when there are failures to report
        failure_lines: list[str] = []
        if not integrity_pass:
            failure_lines.append(
                f"- Question count mismatch: "
                f"expected {questions_in_source}, found {questions_in_output} in output."
            )

        lines: list[str] = [
            "# Compaction Report",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Page Reduction Summary"),
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Original Pages | {original_pages} |",
            f"| Compacted Pages (estimate) | {compacted_pages} |",
            f"| Pages Saved | {pages_saved} |",
            f"| Reduction | {reduction_percent}% |",
            horizontal_rule(),
            section_header("Question Integrity Check"),
            "",
            "| Check | Result |",
            "|-------|--------|",
            f"| Questions in source | {questions_in_source} |",
            f"| Questions in output | {questions_in_output} |",
            f"| All questions retained | {pass_fail_icon(integrity_pass)} |",
            horizontal_rule(),
            section_header("Verdict"),
            "",
            f"**{verdict}**",
        ]

        # Append failure details if any checks failed
        if failure_lines:
            lines.append("")
            lines.extend(failure_lines)

        lines += [
            horizontal_rule(),
            section_header("Notes"),
            "",
            "_Review compacted-source.md to inspect the output._",
            "_Review source-boundary-map.md to see what was stripped._",
        ]

        return "\n".join(lines)
