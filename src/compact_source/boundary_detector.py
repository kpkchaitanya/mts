"""
boundary_detector.py

Locates the first and last question boundaries in a state exam PDF.
This is Step 1 of the compact_source pipeline.

Inputs:  PDF file path, list of PageText extracted from the PDF
Outputs: BoundaryResult with first/last question locations and total question count
"""

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.config import MIN_CONTENT_PAGE, BOUNDARY_DETECTION_MIN_CONFIDENCE, MAX_VISION_SCAN_PAGES
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import PageText, render_page_as_image


# ─── Question Marker Patterns ─────────────────────────────────────────────────

# Patterns that specifically match the first question (number 1)
FIRST_QUESTION_PATTERNS: list[str] = [
    r"^\s*1[\.\)]\s+\S",         # "1. text" or "1) text"
    r"^\s*Question\s+1[\s\.\:]", # "Question 1" / "Question 1." / "Question 1:"
    r"^\s*QUESTION\s+1[\s\.\:]", # "QUESTION 1" (all-caps variant)
    r"^\s*Problem\s+1[\s\.\:]",  # "Problem 1" (some exams use this label)
]

# Pattern matching any numbered question — used to find the last question
ANY_QUESTION_PATTERN: str = r"^\s*(\d+)[\.\)]\s+\S"


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class BoundaryLocation:
    """
    The location of a question boundary within a PDF document.

    Attributes:
        page_number: Zero-based page index where the boundary was found.
        line_number: Zero-based line index within the page.
        text_preview: First 80 characters of the matched line (for reporting).
        confidence: Detection confidence (1.0 = regex; lower = vision estimate).
    """
    page_number: int
    line_number: int
    text_preview: str
    confidence: float


@dataclass
class BoundaryResult:
    """
    The complete boundary detection result for a PDF.

    Attributes:
        first_question: Location of Q1 in the document.
        last_question: Location of the final question in the document.
        total_questions: Total count of numbered questions detected.
        used_vision_fallback: True if Claude vision was invoked for either boundary.
    """
    first_question: BoundaryLocation
    last_question: BoundaryLocation
    total_questions: int
    used_vision_fallback: bool


# ─── Detector ─────────────────────────────────────────────────────────────────

class BoundaryDetector:
    """
    Detects first and last question boundaries in a state exam PDF.

    Responsibilities:
    - Locate Q1 using regex patterns on page text
    - Locate Qn using a reverse scan for the highest question number
    - Fall back to Claude vision when text confidence is below threshold

    Does NOT strip content — stripping is handled by Stripper.
    """

    def __init__(self, claude_client: ClaudeClient) -> None:
        """
        Initialize with a shared Claude API client.

        Args:
            claude_client: Shared Claude client instance for vision fallback.
        """
        self._claude = claude_client

    def detect(self, pdf_path: Path, page_texts: list[PageText]) -> BoundaryResult:
        """
        Detect Q1 and Qn boundaries in the PDF.

        Attempts text-based detection first. Falls back to Claude vision
        if confidence is below BOUNDARY_DETECTION_MIN_CONFIDENCE.

        Args:
            pdf_path: Path to the PDF (used for page rendering in vision fallback).
            page_texts: Extracted page texts in document order.

        Returns:
            BoundaryResult with both boundaries and total question count.

        Raises:
            BoundaryNotFoundError: If boundaries cannot be detected by any method.
        """
        used_vision = False

        # Attempt fast text-based detection for Q1 first
        first_question = self._find_first_by_text(page_texts)

        # Fall back to Claude vision if text detection failed or confidence is low
        if first_question is None or first_question.confidence < BOUNDARY_DETECTION_MIN_CONFIDENCE:
            first_question = self._find_first_by_vision(pdf_path, page_texts)
            used_vision = True

        if first_question is None:
            raise BoundaryNotFoundError(
                f"Could not detect the first question in '{pdf_path.name}'. "
                "Confirm this is a state exam PDF with numbered questions (e.g., '1. ...')."
            )

        # Scan from Q1's page forward to find the highest-numbered question
        last_question, total_questions = self._find_last_by_text(page_texts, first_question)

        if last_question is None:
            raise BoundaryNotFoundError(
                f"Could not detect the last question in '{pdf_path.name}'. "
                "The document may not contain numbered questions after the first."
            )

        return BoundaryResult(
            first_question=first_question,
            last_question=last_question,
            total_questions=total_questions,
            used_vision_fallback=used_vision,
        )

    def _find_first_by_text(self, page_texts: list[PageText]) -> BoundaryLocation | None:
        """
        Scan page text with regex to locate Q1.

        Skips pages before MIN_CONTENT_PAGE to avoid false positives
        in cover pages and instruction sections.

        Args:
            page_texts: All extracted page texts in document order.

        Returns:
            BoundaryLocation if Q1 found, None otherwise.
        """
        # Pre-compile all patterns for efficiency across many pages
        compiled = [re.compile(p, re.IGNORECASE) for p in FIRST_QUESTION_PATTERNS]

        # Only scan pages from MIN_CONTENT_PAGE onward
        for page in page_texts[MIN_CONTENT_PAGE:]:
            for line_idx, line in enumerate(page.lines):
                # Check each Q1 pattern against the current line
                for pattern in compiled:
                    if pattern.match(line):
                        return BoundaryLocation(
                            page_number=page.page_number,
                            line_number=line_idx,
                            text_preview=line[:80],
                            confidence=1.0,
                        )
        return None

    def _find_last_by_text(
        self,
        page_texts: list[PageText],
        first_question: BoundaryLocation,
    ) -> tuple[BoundaryLocation | None, int]:
        """
        Scan pages from Q1's page onward to find the highest-numbered question.

        Tracks every question marker seen and returns the one with the
        highest question number (which is the last question).

        Args:
            page_texts: All extracted page texts.
            first_question: The detected Q1 location (used as scan start).

        Returns:
            Tuple of (BoundaryLocation for last question, total question count).
            Returns (None, 0) if no numbered questions are found after Q1.
        """
        compiled = re.compile(ANY_QUESTION_PATTERN, re.IGNORECASE)
        highest_number = 0
        last_location: BoundaryLocation | None = None

        # Scan only pages from Q1's page to end — nothing before Q1 is relevant
        for page in page_texts[first_question.page_number:]:
            for line_idx, line in enumerate(page.lines):
                match = compiled.match(line)
                if match:
                    question_number = int(match.group(1))
                    # Update if this is the highest question number seen so far
                    if question_number > highest_number:
                        highest_number = question_number
                        last_location = BoundaryLocation(
                            page_number=page.page_number,
                            line_number=line_idx,
                            text_preview=line[:80],
                            confidence=1.0,
                        )

        return last_location, highest_number

    def _find_first_by_vision(
        self, pdf_path: Path, page_texts: list[PageText]
    ) -> BoundaryLocation | None:
        """
        Use Claude vision to locate Q1 when text detection is insufficient.

        Renders candidate pages as PNG images and asks Claude whether
        Q1 appears on each page.

        Args:
            pdf_path: PDF path for page rendering.
            page_texts: Page texts used to select candidate pages.

        Returns:
            BoundaryLocation if Q1 found via vision, None otherwise.
        """
        # Limit vision scan to the first MAX_VISION_SCAN_PAGES pages after MIN_CONTENT_PAGE
        candidate_pages = page_texts[MIN_CONTENT_PAGE: MIN_CONTENT_PAGE + MAX_VISION_SCAN_PAGES]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for page in candidate_pages:
                # Render the candidate page as a PNG for Claude to analyze
                image_path = tmp_path / f"page_{page.page_number}.png"
                render_page_as_image(pdf_path, page.page_number, image_path)

                prompt = (
                    "This is a page from a state exam paper. "
                    "Does this page contain the very first question (labeled '1.' or 'Question 1')? "
                    "Respond with JSON only, no explanation: "
                    '{"has_first_question": true or false, "position": "top", "middle", or "bottom"}'
                )

                response = self._claude.complete_with_image(prompt, image_path)

                # Check for a positive detection in Claude's JSON response
                if '"has_first_question": true' in response.lower():
                    # Use the midpoint of the page as an estimated line number
                    estimated_line = max(0, len(page.lines) // 2)
                    return BoundaryLocation(
                        page_number=page.page_number,
                        line_number=estimated_line,
                        text_preview="[Detected via Claude vision fallback]",
                        confidence=0.6,
                    )

        return None


# ─── Exceptions ───────────────────────────────────────────────────────────────

class BoundaryNotFoundError(Exception):
    """Raised when question boundaries cannot be detected in a PDF."""
    pass
