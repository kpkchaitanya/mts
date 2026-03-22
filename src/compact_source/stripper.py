"""
stripper.py

Removes all content before the first question and after the last question
in a state exam PDF. This is Step 2 of the compact_source pipeline.

Inputs:  PageText list, BoundaryResult from boundary_detector
Outputs: StrippedContent (lines within question boundaries),
         source-boundary-map.md artifact string
"""

import datetime
from dataclasses import dataclass, field
from pathlib import Path

from src.compact_source.boundary_detector import BoundaryResult, BoundaryLocation
from src.utils.pdf_utils import PageText
from src.utils.markdown_utils import frontmatter, horizontal_rule, section_header


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class StrippedContent:
    """
    The result of stripping non-question content from a PDF.

    Attributes:
        pages: Lines of text per page, containing only question content.
        first_page_number: Zero-based page where question content begins.
        last_page_number: Zero-based page where question content ends.
        lines_removed_before: Approximate line count stripped before Q1.
        lines_removed_after: Approximate line count stripped after Qn.
    """
    pages: list[list[str]] = field(default_factory=list)
    first_page_number: int = 0
    last_page_number: int = 0
    lines_removed_before: int = 0
    lines_removed_after: int = 0


# ─── Stripper ─────────────────────────────────────────────────────────────────

class Stripper:
    """
    Strips non-question content from extracted PDF page texts.

    Responsibilities:
    - Remove all lines before the first question boundary
    - Remove all lines after the last question boundary
    - Generate the source-boundary-map.md artifact

    Does NOT compact spacing — that is handled by Compactor.
    """

    def strip(
        self,
        page_texts: list[PageText],
        boundaries: BoundaryResult,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> tuple[StrippedContent, str]:
        """
        Strip non-question content and generate the boundary map artifact.

        Args:
            page_texts: Full extracted page texts from the source PDF.
            boundaries: First and last question boundaries from BoundaryDetector.
            source_filename: Original PDF filename (for artifact metadata).
            run_id: Current pipeline run ID (for artifact metadata).
            grade: Grade level of the exam.
            subject: Subject area (e.g., "Math").

        Returns:
            Tuple of:
            - StrippedContent: Lines and metadata for the question-only content
            - str: Full markdown string for the source-boundary-map.md artifact
        """
        first = boundaries.first_question
        last = boundaries.last_question

        # Count how many lines exist before Q1 and after Qn for the report
        lines_before = self._count_lines_before(page_texts, first)
        lines_after = self._count_lines_after(page_texts, last)

        # Extract only the lines that fall between Q1 and Qn (inclusive)
        question_pages = self._extract_question_lines(page_texts, first, last)

        content = StrippedContent(
            pages=question_pages,
            first_page_number=first.page_number,
            last_page_number=last.page_number,
            lines_removed_before=lines_before,
            lines_removed_after=lines_after,
        )

        boundary_map_md = self._build_boundary_map(
            boundaries=boundaries,
            content=content,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
            total_pages=len(page_texts),
        )

        return content, boundary_map_md

    def _count_lines_before(
        self, page_texts: list[PageText], first: BoundaryLocation
    ) -> int:
        """
        Count all lines that appear before Q1's location.

        Args:
            page_texts: All extracted page texts.
            first: Location of the first question.

        Returns:
            Total line count before Q1 (across all pre-Q1 pages and the partial Q1 page).
        """
        total = 0
        # Sum all lines on pages that appear entirely before Q1's page
        for page in page_texts[:first.page_number]:
            total += len(page.lines)
        # Add the lines on Q1's page that appear before the Q1 line
        total += first.line_number
        return total

    def _count_lines_after(
        self, page_texts: list[PageText], last: BoundaryLocation
    ) -> int:
        """
        Count all lines that appear after Qn's location.

        Args:
            page_texts: All extracted page texts.
            last: Location of the last question.

        Returns:
            Total line count after Qn (partial last page + all subsequent pages).
        """
        total = 0
        # Sum all lines on pages that appear entirely after Qn's page
        for page in page_texts[last.page_number + 1:]:
            total += len(page.lines)
        # Count lines on Qn's page that appear after the Qn line
        if last.page_number < len(page_texts):
            last_page_lines = page_texts[last.page_number].lines
            lines_after_last = len(last_page_lines) - last.line_number - 1
            total += max(0, lines_after_last)
        return total

    def _extract_question_lines(
        self,
        page_texts: list[PageText],
        first: BoundaryLocation,
        last: BoundaryLocation,
    ) -> list[list[str]]:
        """
        Extract lines of text that fall between Q1 and Qn (inclusive).

        Handles three cases:
        - Single page: both Q1 and Qn are on the same page
        - First page of a multi-page range: Q1 to end of page
        - Middle pages: all lines included
        - Last page of a multi-page range: start of page to Qn line

        Args:
            page_texts: All extracted page texts.
            first: Location of the first question.
            last: Location of the last question.

        Returns:
            List of line lists, one entry per page in the question range.
        """
        result: list[list[str]] = []

        # Only process pages that fall within the Q1–Qn page range
        for page in page_texts[first.page_number: last.page_number + 1]:
            pn = page.page_number

            if pn == first.page_number and pn == last.page_number:
                # Both boundaries are on the same page — slice between them
                result.append(page.lines[first.line_number: last.line_number + 1])
            elif pn == first.page_number:
                # First page: include from Q1 line to end of page
                result.append(page.lines[first.line_number:])
            elif pn == last.page_number:
                # Last page: include from start of page to Qn line
                result.append(page.lines[: last.line_number + 1])
            else:
                # Middle page: include all lines
                result.append(page.lines[:])

        return result

    def _build_boundary_map(
        self,
        boundaries: BoundaryResult,
        content: StrippedContent,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
        total_pages: int,
    ) -> str:
        """
        Build the source-boundary-map.md artifact content.

        Args:
            boundaries: Detected boundary locations and question count.
            content: Stripped content metadata (line counts, page numbers).
            source_filename: Original PDF filename.
            run_id: Pipeline run ID.
            grade: Grade level.
            subject: Subject area.
            total_pages: Total page count in the original PDF.

        Returns:
            Full markdown string for the boundary map artifact.
        """
        first = boundaries.first_question
        last = boundaries.last_question
        detection_method = "Text + Vision fallback" if boundaries.used_vision_fallback else "Text (regex)"

        lines: list[str] = [
            "# Source Boundary Map",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Boundary Detection"),
            "",
            "| Boundary | Text Preview | Page (0-based) | Line |",
            "|----------|-------------|----------------|------|",
            f"| First Question (Q1) | `{first.text_preview}` | {first.page_number} | {first.line_number} |",
            f"| Last Question  (Qn) | `{last.text_preview}` | {last.page_number} | {last.line_number} |",
            "",
            f"**Detection method:** {detection_method}",
            horizontal_rule(),
            section_header("Content Stripped"),
            "",
            f"- **Before Q1:** ~{content.lines_removed_before} lines "
            f"(pages 0 – {max(0, first.page_number - 1)})",
            f"- **After Qn:** ~{content.lines_removed_after} lines "
            f"(pages {last.page_number + 1} – {total_pages - 1})",
            horizontal_rule(),
            section_header("Summary"),
            "",
            f"- **Total questions detected:** {boundaries.total_questions}",
            f"- **Question content spans pages:** {first.page_number} – {last.page_number}",
            f"- **Total pages in source PDF:** {total_pages}",
        ]

        return "\n".join(lines)
