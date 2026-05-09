"""
passage_detector.py

Detects passage groups in a Reading / ELA test PDF.

A PassageGroup is the atomic output unit for reading: one literary or
informational passage together with all of the question pages that follow it,
kept as an ordered sequence of raw page indices.

Detection strategy (STAAR RLA / NC EOG ELA format):
  - Passage pages begin with a 4-digit standalone numeric ID (e.g. 1503, 2111).
    These IDs are TEA / DPI selection identifiers printed at the top of the
    first page of each passage.
  - Question pages begin with an item-code token of the form NNNNN_N
    (5+ digits, underscore, 1 digit), e.g. 37299_4.  These appear as the
    first text token on STAAR-style question pages.
  - Pages that carry neither marker and occur after the first passage marker
    are treated as passage continuation pages (middle pages of a multi-page
    passage).
  - Cover / instruction pages before the first passage marker are skipped.

Output: PassageDetectionResult containing an ordered list of PassageGroup
objects.  Each PassageGroup records all page indices (zero-based) needed to
reconstruct the passage and its questions in output order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


# ─── Patterns ─────────────────────────────────────────────────────────────────

# First token on the page is a 4-digit number → passage start marker
# (e.g. "1503", "2111").  The number must stand alone at the top of the page.
_PASSAGE_ID_RE = re.compile(r"^\d{4}$")

# First token is a STAAR item code: 5-or-more digits, underscore, 1 digit
# (e.g. "37299_4", "37311_1").
_ITEM_CODE_RE = re.compile(r"^\d{5,}_\d$")


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class PassageGroup:
    """
    One passage and all question pages that follow it.

    Attributes:
        passage_id:       The 4-digit TEA selection ID (e.g. 1503).
        passage_pages:    Zero-based page indices of the passage itself
                          (first page + any continuation pages).
        question_pages:   Zero-based page indices of question pages
                          that belong to this passage.
    """

    passage_id: str
    passage_pages: list[int] = field(default_factory=list)
    question_pages: list[int] = field(default_factory=list)

    @property
    def all_pages(self) -> list[int]:
        """All pages in document order (passage first, then questions)."""
        return self.passage_pages + self.question_pages

    @property
    def total_pages(self) -> int:
        return len(self.passage_pages) + len(self.question_pages)


@dataclass
class PassageDetectionResult:
    """Complete result of passage group detection for one ELA source PDF."""

    groups: list[PassageGroup]
    total_passages: int
    total_question_pages: int
    page_heights: list[float]   # Height of each source page in PDF points
    page_widths: list[float]    # Width of each source page in PDF points


# ─── Detector ─────────────────────────────────────────────────────────────────


class PassageDetector:
    """
    Detects passage group boundaries in a Reading / ELA test PDF.

    Uses pdfplumber to extract the first text token from each page and
    classifies pages as: passage-start, question, or continuation.

    Algorithm
    ---------
    1. Scan pages in order.
    2. If a page's first token matches _PASSAGE_ID_RE → start a new group.
    3. If it matches _ITEM_CODE_RE → add to current group's question_pages.
    4. Otherwise (blank, image-only, or mid-passage text) → continuation
       appended to either the passage or question section depending on
       context.
    5. Pages before the first passage marker are ignored (cover / instructions).
    """

    def detect(self, pdf_path: Path) -> PassageDetectionResult:
        """
        Run passage group detection on the given PDF.

        Args:
            pdf_path: Path to the ELA source PDF.

        Returns:
            PassageDetectionResult with all detected groups.
        """
        groups: list[PassageGroup] = []
        current_group: PassageGroup | None = None
        # Track whether we have seen at least one question page in the
        # current group — used to decide where to append continuation pages.
        seen_questions_in_group: bool = False

        page_heights: list[float] = []
        page_widths: list[float] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_heights.append(float(page.height))
                page_widths.append(float(page.width))

                first_token = self._first_token(page)
                page_type = self._classify(first_token)

                if page_type == "passage_start":
                    # Finalise previous group (if any)
                    if current_group is not None:
                        groups.append(current_group)
                    current_group = PassageGroup(passage_id=first_token)
                    current_group.passage_pages.append(page_idx)
                    seen_questions_in_group = False

                elif page_type == "question":
                    if current_group is None:
                        # Question page before any passage → skip
                        continue
                    current_group.question_pages.append(page_idx)
                    seen_questions_in_group = True

                else:
                    # continuation / blank / image-only
                    if current_group is None:
                        # Before first passage → skip (cover pages)
                        continue
                    words = page.extract_words()
                    # Skip structural / boundary pages: wordless pages and
                    # very sparse pages (e.g. "STAAR READING" answer-doc
                    # separators) that follow the last question section.
                    if not words:
                        continue
                    if seen_questions_in_group and len(words) < 8:
                        # Too sparse to be a real content page — skip
                        continue
                    if seen_questions_in_group:
                        # Continuation after questions → extra question page
                        current_group.question_pages.append(page_idx)
                    else:
                        # Mid-passage continuation
                        current_group.passage_pages.append(page_idx)

        # Append the last group
        if current_group is not None:
            groups.append(current_group)

        total_question_pages = sum(len(g.question_pages) for g in groups)

        return PassageDetectionResult(
            groups=groups,
            total_passages=len(groups),
            total_question_pages=total_question_pages,
            page_heights=page_heights,
            page_widths=page_widths,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _first_token(page: pdfplumber.page.Page) -> str:
        """
        Return the first non-whitespace word on the page, or "" if none.

        Uses pdfplumber word extraction so multi-column and multi-font pages
        are handled correctly regardless of text order in the PDF stream.
        """
        words = page.extract_words()
        if not words:
            return ""
        # Words are sorted by top (y) then x by pdfplumber's default.
        return words[0]["text"].strip()

    @staticmethod
    def _classify(token: str) -> str:
        """
        Classify the page type based on its first token.

        Returns one of:
          "passage_start" — 4-digit selection ID
          "question"      — STAAR item code  (NNNNN_N)
          "continuation"  — everything else
        """
        if not token:
            return "continuation"
        if _PASSAGE_ID_RE.match(token):
            return "passage_start"
        if _ITEM_CODE_RE.match(token):
            return "question"
        return "continuation"
