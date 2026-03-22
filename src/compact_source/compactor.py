"""
compactor.py

Reflows stripped question content into compact markdown by eliminating
blank lines between questions and removing decorative separators.
This is Step 3 of the compact_source pipeline.

Inputs:  StrippedContent from stripper
Outputs: Compacted markdown string (written as compacted-source.md)
"""

import re

from src.compact_source.stripper import StrippedContent


# ─── Decorative Line Patterns ─────────────────────────────────────────────────

# Lines matching any of these patterns are decorative or instructional noise
# and do not contain question content — they are removed during compaction.
DECORATIVE_LINE_PATTERNS: list[str] = [
    r"^[-_=\*]{3,}$",             # --- or ___ or === or *** (separator lines)
    r"^\s*Page\s+\d+\s*$",        # "Page 1", "Page 12" (page number footers)
    r"^\s*GO ON\s*\.?\s*$",       # "GO ON" or "GO ON." (state exam page footers)
    r"^\s*STOP\s*\.?\s*$",        # "STOP" or "STOP." (end-of-section markers)
    r"^\s*Do not go on.*$",       # "Do not go on until told to do so."
    r"^\s*Copyright.*$",          # Copyright notices
    r"^\s*\d+\s*$",               # Lone page numbers (just a number on a line)
]


# ─── Compactor ────────────────────────────────────────────────────────────────

class Compactor:
    """
    Transforms stripped question content into compact, print-ready markdown.

    Responsibilities:
    - Flatten multi-page line lists into a single document
    - Remove decorative lines (footers, separators, page numbers)
    - Collapse multiple consecutive blank lines into one
    - Produce a clean, continuous markdown string

    Does NOT validate question completeness — Reporter handles that.
    """

    def compact(self, content: StrippedContent) -> str:
        """
        Produce a compact markdown string from stripped question content.

        Args:
            content: Stripped content from the Stripper step,
                     containing question lines organized by page.

        Returns:
            Compacted markdown string ready to be written as compacted-source.md.
        """
        # Step 1: Flatten all per-page line lists into a single sequence
        all_lines = self._flatten_pages(content.pages)

        # Step 2: Remove decorative and instructional lines
        filtered_lines = self._remove_decorative_lines(all_lines)

        # Step 3: Collapse consecutive blank lines to a single blank line
        collapsed_lines = self._collapse_blank_lines(filtered_lines)

        # Step 4: Join into a final markdown string
        return "\n".join(collapsed_lines)

    def _flatten_pages(self, pages: list[list[str]]) -> list[str]:
        """
        Flatten page-separated line lists into a single flat list.

        Inserts one blank line between pages to mark the transition.
        These inter-page blanks are later collapsed by _collapse_blank_lines.

        Args:
            pages: Per-page line lists from StrippedContent.

        Returns:
            Single flat list of all lines across all pages.
        """
        flat: list[str] = []
        for page_lines in pages:
            flat.extend(page_lines)
            # Separate pages with a single blank line — will be collapsed if redundant
            flat.append("")
        return flat

    def _remove_decorative_lines(self, lines: list[str]) -> list[str]:
        """
        Filter out decorative, instructional, and structural noise lines.

        Args:
            lines: All lines from the flattened page content.

        Returns:
            Lines with all decorative entries removed.
        """
        # Pre-compile patterns for efficiency across many lines
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in DECORATIVE_LINE_PATTERNS]
        filtered: list[str] = []

        for line in lines:
            # A line is decorative if it matches any of the defined patterns
            is_decorative = any(pattern.match(line) for pattern in compiled_patterns)
            if not is_decorative:
                filtered.append(line)

        return filtered

    def _collapse_blank_lines(self, lines: list[str]) -> list[str]:
        """
        Reduce consecutive blank lines to a single blank line.

        This is the core compaction step. State exam PDFs often have
        multiple blank lines between questions for layout purposes.
        Collapsing them brings questions closer together for printing.

        Args:
            lines: Filtered lines, potentially with consecutive blank lines.

        Returns:
            Lines with no two consecutive blank lines remaining.
        """
        collapsed: list[str] = []
        previous_was_blank = False

        for line in lines:
            is_blank = line.strip() == ""

            # Skip this line if it is blank and the previous line was also blank
            if is_blank and previous_was_blank:
                continue

            collapsed.append(line)
            previous_was_blank = is_blank

        return collapsed
