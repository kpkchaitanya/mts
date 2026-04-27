"""
block_detector.py

Detects question block boundaries in a source worksheet PDF using
pdfplumber y-coordinate extraction.

Each question block (stem + answer choices + any embedded diagram) is
represented as a list of PageSlice objects — typically one slice for a
single-page question, or multiple slices for a question that crosses a
page boundary.

Output: BlockDetectionResult with an ordered list of QuestionBlock objects.

Boundary detection strategy:
  - TOP of each block: the question number marker's y-coordinate minus
    BLOCK_TOP_PADDING (a small upward buffer to capture the number itself).
  - BOTTOM of each block: the y_bottom of the LAST answer choice line
    (A/B/C/D or F/G/H/J) detected within the block's span, plus
    BLOCK_BOTTOM_PADDING. This eliminates trailing whitespace between the
    last answer choice and the next question marker.
  - Markers with no detectable answer choices that span more than
    MAX_QUESTION_SPAN_PAGES are treated as non-question content (formula
    charts, reference pages, numbered instructions) and filtered out.
"""

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF — used in _detect_image_heavy_blocks for content bbox queries

from src.config import (
    MAX_QUESTION_SPAN_PAGES,
    MAX_VISION_SCAN_PAGES,
    MIN_CONTENT_PAGE,
)
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import render_page_as_image


# ─── Patterns ─────────────────────────────────────────────────────────────────

# Matches the start of a numbered question line, e.g.:
#   "1. Which of..."   "1) Which of..."   "1 Which of..."
#
# NOTE: re.IGNORECASE is intentionally NOT used here. Question text always
# begins with an uppercase letter (e.g., "Which", "How", "What"). Lowercase
# starts (e.g., "1 mile = ...", "1 yard = ...") are measurement conversions
# on reference charts and must NOT match as question markers.
QUESTION_LINE_PATTERN = re.compile(
    r"^\s*(\d+)(?:[\.\)]\s|\s+[A-Z])",
)

# Matches an answer choice line at the start of a text line.
# Covers three common formats for A/B/C/D and STAAR's F/G/H/J answer choices:
#   "A. rectangle"   — letter + dot + space  (traditional)
#   "B) 14"          — letter + paren + space (traditional)
#   "C 730 < 806"    — letter + space only   (STAAR format)
# The letter must be immediately at the start of the line (after optional
# whitespace) to avoid matching mid-line occurrences.
ANSWER_CHOICE_PATTERN = re.compile(r"^\s*[A-DFGHJ](?:[\.\)]\s|\s)")

# ─── Padding Constants ────────────────────────────────────────────────────────

# Small upward offset so the crop starts just above the question number marker.
BLOCK_TOP_PADDING: float = 4.0

# Small downward offset below the last answer choice line.
# Ensures the last option is not clipped at the crop boundary.
BLOCK_BOTTOM_PADDING: float = 6.0

# Words on the same text line cluster within this vertical tolerance (PDF points).
LINE_Y_TOLERANCE: float = 3.0

# Minimum vertical height (PDF points) a number marker's span must have for it
# to be treated as a real question when no text answer choices are found.
# Formula chart rows span ~20 pts; the shortest real questions span ≥ ~120 pts.
# This threshold separates griddable questions and image-choice questions from
# numbered reference entries (unit conversions, numbered instructions, etc.).
MIN_QUESTION_HEIGHT_PTS: float = 80.0

# ─── Format Auto-detection ────────────────────────────────────────────────────

# Number of content pages sampled to classify PDF format.
IMAGE_HEAVY_SAMPLE_PAGES: int = 10

# If the sampled content pages average fewer than this many words, the PDF is
# classified as image-heavy (one visual question per page, e.g. EOG format).
# STAAR pages average 50-200 words; EOG question pages average ~3 words.
IMAGE_HEAVY_AVG_WORDS_THRESHOLD: int = 10

# A content page is counted as image-heavy if it has at most this many words.
# EOG question pages carry just "N of 40" (3 words) as a footer.
# Section-break notices like "The first section of the test ends here." have
# 8 words and must be excluded. Setting the cap to 5 separates question pages
# from all non-question low-text pages.
IMAGE_HEAVY_PAGE_MAX_WORDS: int = 5

# Regex that matches a page-number footer of the form "N of M"
# (e.g. "1 of 40", "12 of 50").  Used to exclude the footer from content-bbox
# calculations so it does not anchor y_bottom back to the bottom of the page.
IMAGE_HEAVY_FOOTER_PATTERN: re.Pattern = re.compile(r"^\d+\s+of\s+\d+$", re.IGNORECASE)

# The footer is expected to sit within this fraction of page height from the
# bottom (default 15 %).  A text block matches the footer exclusion rule only
# when it is BOTH inside this zone AND matches IMAGE_HEAVY_FOOTER_PATTERN.
IMAGE_HEAVY_FOOTER_ZONE_FRACTION: float = 0.15


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class PageSlice:
    """
    A rectangular region of one PDF page that forms part of a question block.

    Coordinates are in PDF points measured from the TOP of the page
    (matching pdfplumber's convention and compatible with PyMuPDF clip rects).
    """

    page_number: int    # Zero-based page index
    y_top: float        # Distance from top of page (PDF points)
    y_bottom: float     # Distance from top of page (PDF points)

    @property
    def height(self) -> float:
        return max(0.0, self.y_bottom - self.y_top)


@dataclass
class QuestionBlock:
    """
    A single question (stem + answer choices + any diagram) from the source PDF.

    Most questions fit on one page (single PageSlice). Questions that begin
    near the bottom of a page and continue onto the next produce two or more
    slices that are combined into one image during extraction.
    """

    question_number: int
    slices: list[PageSlice] = field(default_factory=list)
    text_preview: str = ""

    @property
    def total_height_pts(self) -> float:
        return sum(s.height for s in self.slices)


@dataclass
class BlockDetectionResult:
    """Complete result of question block detection for one source PDF."""

    blocks: list[QuestionBlock]
    total_questions: int
    page_heights: list[float]   # Height of each source page in PDF points
    page_widths: list[float]    # Width of each source page in PDF points
    used_vision_fallback: bool
    is_image_heavy: bool = False  # True when PDF was classified as image-heavy (EOG style)


@dataclass
class _QuestionMarker:
    """Internal: a detected question number and its position in the document."""

    question_number: int
    page_number: int    # Zero-based
    y_top: float        # Top of the question line in PDF points from page top
    text_preview: str


@dataclass
class _AnswerChoiceLine:
    """
    Internal: a detected answer choice line (A./B./C./D. or F./G./H./J.)
    and its vertical extent on the page.
    """

    page_number: int    # Zero-based
    y_top: float        # Top of the choice line in PDF points from page top
    y_bottom: float     # Bottom of the choice line in PDF points from page top


# ─── Detector ─────────────────────────────────────────────────────────────────


class BlockDetector:
    """
    Detects question block boundaries using pdfplumber y-coordinate extraction.

    Primary path: scans word positions on each page to locate question number
    markers and answer choice lines, then computes each block's PageSlice(s)
    using the answer choice y_bottom as the tight bottom boundary.

    Non-question markers (formula charts, numbered instructions) are filtered
    out by checking whether answer choices exist within their span.

    Fallback path: if text extraction finds no markers, Claude vision is used
    to locate Q1 so at least one block can anchor the detection.
    """

    def __init__(self, claude_client: ClaudeClient) -> None:
        self._claude = claude_client

    def detect(self, pdf_path: Path) -> BlockDetectionResult:
        """
        Detect all question blocks in the source PDF.

        Auto-detects the PDF format by sampling word counts from the first
        content pages:
          - text_rich (STAAR-style): multiple questions per page with extractable
            text → existing text/vision detection pipeline.
          - image_heavy (EOG-style): one visual question per page with almost no
            extractable text → full-page block per content page, stopping at
            any detectable answer key section.

        Args:
            pdf_path: Path to the source worksheet PDF.

        Returns:
            BlockDetectionResult with all question blocks and page geometry.

        Raises:
            BlockDetectionError: If no question markers can be found, or if all
                detected markers are filtered as non-question content.
        """
        page_heights, page_widths = self._get_page_geometry(pdf_path)

        # Auto-detect format before running text-based detection
        fmt = self._classify_format(pdf_path)
        if fmt == "image_heavy":
            return self._detect_image_heavy_blocks(pdf_path, page_heights, page_widths)

        # All markers, not yet deduplicated — dedup happens after validation
        all_markers = self._find_all_question_markers(pdf_path)
        used_vision = False

        if not all_markers:
            first = self._find_first_marker_by_vision(pdf_path, page_heights)
            if first is None:
                raise BlockDetectionError(
                    f"No question markers found in '{pdf_path.name}'. "
                    "Ensure the PDF contains numbered questions (e.g., '1.', '1)')."
                )
            all_markers = [first]
            used_vision = True

        answer_choices = self._find_answer_choices(pdf_path)
        blocks = self._build_blocks(all_markers, answer_choices, page_heights)

        if not blocks:
            raise BlockDetectionError(
                f"No valid question blocks found in '{pdf_path.name}'. "
                "All detected number markers were filtered as non-question content "
                "(no A/B/C/D answer choices detected adjacent to any number marker). "
                "Check that the PDF contains standard multiple-choice questions "
                "with choices in text (A/B/C/D or F/G/H/J)."
            )

        return BlockDetectionResult(
            blocks=blocks,
            total_questions=len(blocks),
            page_heights=page_heights,
            page_widths=page_widths,
            used_vision_fallback=used_vision,
        )

    # ── Format Classification ─────────────────────────────────────────────────

    def _classify_format(self, pdf_path: Path) -> str:
        """
        Classify the PDF as 'text_rich' or 'image_heavy' by sampling content pages.

        Samples up to IMAGE_HEAVY_SAMPLE_PAGES pages starting at MIN_CONTENT_PAGE.
        If the average word count across sampled pages is below
        IMAGE_HEAVY_AVG_WORDS_THRESHOLD, the format is 'image_heavy'.

        Returns:
            'image_heavy' or 'text_rich'
        """
        total_words = 0
        pages_sampled = 0
        with pdfplumber.open(pdf_path) as pdf:
            sample_end = min(MIN_CONTENT_PAGE + IMAGE_HEAVY_SAMPLE_PAGES, len(pdf.pages))
            for page_idx in range(MIN_CONTENT_PAGE, sample_end):
                total_words += len(pdf.pages[page_idx].extract_words())
                pages_sampled += 1
        if pages_sampled == 0:
            return "text_rich"
        avg = total_words / pages_sampled
        return "image_heavy" if avg < IMAGE_HEAVY_AVG_WORDS_THRESHOLD else "text_rich"

    def _find_answer_key_fence(self, pdf_path: Path, total_pages: int) -> int:
        """
        Return the zero-based page index of the first answer key page.

        Scans every page for co-occurrence of the words 'answer' and 'key'
        (case-insensitive). Returns total_pages if no answer key is found.
        """
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx in range(total_pages):
                words = {w["text"].lower() for w in pdf.pages[page_idx].extract_words()}
                if "answer" in words and "key" in words:
                    return page_idx
        return total_pages

    def _detect_image_heavy_blocks(self, pdf_path: Path, page_heights: list[float], page_widths: list[float]) -> BlockDetectionResult:
        """
        Build one full-page block per content page for image-heavy PDFs (EOG style).

        Content pages are those between MIN_CONTENT_PAGE and the answer key fence
        whose word count is at or below IMAGE_HEAVY_PAGE_MAX_WORDS. Each such page
        becomes one QuestionBlock containing the full visible area of the page.

        The answer key section (and any appendix after it) is excluded entirely.
        """
        total_pages = len(page_heights)
        fence = self._find_answer_key_fence(pdf_path, total_pages)
        blocks: list[QuestionBlock] = []
        question_number = 1

        with pdfplumber.open(pdf_path) as pdf:
            fitz_doc = fitz.open(str(pdf_path))
            try:
                for page_idx in range(MIN_CONTENT_PAGE, fence):
                    words = pdf.pages[page_idx].extract_words()
                    word_count = len(words)
                    if 0 < word_count <= IMAGE_HEAVY_PAGE_MAX_WORDS:
                        # Compute y_bottom by locating the footer ("N of M") and
                        # positioning the block boundary just above it.  This
                        # eliminates the blank gap between the last answer choice
                        # and the page-number footer that plagued BUG-002.
                        y_bottom = self._find_image_heavy_y_bottom(
                            fitz_doc[page_idx], page_heights[page_idx], words
                        )
                        slices = [PageSlice(
                            page_number=page_idx,
                            y_top=0.0,
                            y_bottom=y_bottom,
                        )]
                        blocks.append(QuestionBlock(
                            question_number=question_number,
                            slices=slices,
                            text_preview=f"(image-based question {question_number})",
                        ))
                        question_number += 1
            finally:
                fitz_doc.close()

        if not blocks:
            raise BlockDetectionError(
                f"No image-based content pages found in '{pdf_path.name}'. "
                "All content pages exceed the image-heavy word threshold."
            )

        return BlockDetectionResult(
            blocks=blocks,
            total_questions=len(blocks),
            page_heights=page_heights,
            page_widths=page_widths,
            used_vision_fallback=False,
            is_image_heavy=True,
        )

    # ── Image-heavy helpers ───────────────────────────────────────────────────

    def _find_image_heavy_y_bottom(
        self,
        fitz_page: fitz.Page,
        page_height: float,
        pdfplumber_words: list | None = None,
    ) -> float:
        """
        Return the content-aware y_bottom for an image-heavy question page.

        Primary strategy — footer exclusion (preferred):
            Locate the page-number footer ("N of M") in the pdfplumber word
            list and position y_bottom just above it.  The embedded raster
            question image occupies the full page bbox, so querying image
            bboxes always returns page_height; only the footer's text
            position gives us the true content boundary.

        Fallback strategy — PyMuPDF content bboxes:
            If no footer words are provided (or none match), queries text
            blocks (footer-filtered), embedded images, and vector drawings
            via PyMuPDF, takes the max content y, adds padding.

        Args:
            fitz_page:          PyMuPDF page object.
            page_height:        Full page height in PDF points.
            pdfplumber_words:   Words extracted by pdfplumber from this page
                                (same coordinate system — top-origin pts).

        Returns:
            y_bottom in PDF points, capped at page_height.
        """
        # ── Primary: locate footer and cut just above it ──────────────────
        if pdfplumber_words:
            footer_zone_y = page_height * (1.0 - IMAGE_HEAVY_FOOTER_ZONE_FRACTION)
            # Collect all words sitting in the bottom footer zone.
            footer_words = [w for w in pdfplumber_words if float(w.get("top", 0)) >= footer_zone_y]
            if footer_words:
                footer_text = " ".join(w["text"] for w in footer_words)
                if IMAGE_HEAVY_FOOTER_PATTERN.search(footer_text):
                    # Confirmed footer — position block bottom just above it.
                    footer_top = min(float(w["top"]) for w in footer_words)
                    return max(0.0, footer_top - BLOCK_BOTTOM_PADDING)

        # ── Fallback: PyMuPDF content bboxes (footer-filtered) ────────────
        max_y: float = 0.0
        footer_zone_y = page_height * (1.0 - IMAGE_HEAVY_FOOTER_ZONE_FRACTION)

        for block in fitz_page.get_text("blocks"):
            block_text = block[4].strip()
            block_y1   = block[3]
            if block_y1 > footer_zone_y and IMAGE_HEAVY_FOOTER_PATTERN.search(block_text):
                continue
            max_y = max(max_y, block_y1)

        for img_info in fitz_page.get_image_info():
            bbox = img_info.get("bbox")
            if bbox:
                max_y = max(max_y, bbox[3])

        for drawing in fitz_page.get_drawings():
            rect = drawing.get("rect")
            if rect:
                max_y = max(max_y, rect.y1)

        if max_y > 0:
            return min(max_y + BLOCK_BOTTOM_PADDING, page_height)

        return page_height

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _get_page_geometry(self, pdf_path: Path) -> tuple[list[float], list[float]]:
        """Return (heights, widths) in PDF points for every page."""
        heights: list[float] = []
        widths: list[float] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                heights.append(float(page.height))
                widths.append(float(page.width))
        return heights, widths

    # ── Marker Detection ──────────────────────────────────────────────────────

    def _find_all_question_markers(self, pdf_path: Path) -> list[_QuestionMarker]:
        """
        Scan all pages for question number markers using word y-coordinates.

        Returns all markers sorted by document order (page, then y_top).
        Does NOT deduplicate — duplicate question numbers are removed later
        in _build_blocks, after non-question markers have been filtered out.
        This ensures a false-positive early marker (e.g., '1.' in a formula
        chart) does not prevent the real Q1 from being detected.
        """
        markers: list[_QuestionMarker] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                # Skip cover and instruction pages before question content starts
                if page_idx < MIN_CONTENT_PAGE:
                    continue
                for y_top, _y_bottom, line_text in _extract_lines_with_coords(page):
                    match = QUESTION_LINE_PATTERN.match(line_text)
                    if match:
                        markers.append(_QuestionMarker(
                            question_number=int(match.group(1)),
                            page_number=page_idx,
                            y_top=y_top,
                            text_preview=line_text[:60],
                        ))

        markers.sort(key=lambda m: (m.page_number, m.y_top))
        return markers

    # ── Answer Choice Detection ────────────────────────────────────────────────

    def _find_answer_choices(self, pdf_path: Path) -> list[_AnswerChoiceLine]:
        """
        Scan all pages for answer choice lines (A./B./C./D. or F./G./H./J.).

        Scans the full document (no page skip) because answer choices always
        appear within question blocks, and the block-range filter in
        _find_last_answer_choice_in_range ensures choices are attributed to
        the correct question.

        Returns choices sorted by document order (page, then y_top).
        """
        choices: list[_AnswerChoiceLine] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                for y_top, y_bottom, line_text in _extract_lines_with_coords(page):
                    if ANSWER_CHOICE_PATTERN.match(line_text):
                        choices.append(_AnswerChoiceLine(
                            page_number=page_idx,
                            y_top=y_top,
                            y_bottom=y_bottom,
                        ))

        choices.sort(key=lambda c: (c.page_number, c.y_top))
        return choices

    def _find_last_answer_choice_in_range(
        self,
        answer_choices: list[_AnswerChoiceLine],
        start_page: int,
        start_y: float,
        end_page: int,
        end_y: float,
    ) -> Optional[_AnswerChoiceLine]:
        """
        Return the last answer choice line within the given document range.

        The range is [start_page/start_y, end_page/end_y] inclusive.
        Returns None if no answer choices are found in the range.

        Args:
            answer_choices: Full sorted list of all answer choice lines in the PDF.
            start_page:     Zero-based page index where the search range begins.
            start_y:        y_top of the question marker (range start).
            end_page:       Zero-based page index where the search range ends.
            end_y:          y_top of the next question marker (range end).
        """
        candidates: list[_AnswerChoiceLine] = []

        for choice in answer_choices:
            if choice.page_number < start_page or choice.page_number > end_page:
                continue
            # On the start page: choice must be at or below the question marker
            if choice.page_number == start_page and choice.y_top < start_y:
                continue
            # On the end page: choice must be above the next question marker
            if choice.page_number == end_page and choice.y_top >= end_y:
                continue
            candidates.append(choice)

        if len(candidates) < 2:
            # A single match is almost always a false positive (e.g., a stem line
            # like "Find the value of A and B" → "A " matches the pattern).
            # Real answer sets always have at least two detectable choice lines.
            return None
        # The last candidate by document position is the final answer choice
        return max(candidates, key=lambda c: (c.page_number, c.y_top))

    # ── Block Building ────────────────────────────────────────────────────────

    def _build_blocks(
        self,
        all_markers: list[_QuestionMarker],
        answer_choices: list[_AnswerChoiceLine],
        page_heights: list[float],
    ) -> list[QuestionBlock]:
        """
        Build QuestionBlock objects from all detected question markers.

        Two-pass process:

        Pass 1 — Validate markers:
          For each marker, search for answer choices in its raw span (marker
          to next raw marker). Markers with no choices that span more than
          MAX_QUESTION_SPAN_PAGES are non-question content and are discarded.
          Markers with no choices but a short span are kept — their answer
          choices may be embedded in images rather than extractable text.

        Pass 2 — Build tight blocks:
          Using only the validated markers (after deduplication by question
          number), recompute spans between consecutive valid markers, then
          anchor each block's bottom to the last answer choice y_bottom plus
          BLOCK_BOTTOM_PADDING. Falls back to the preliminary bottom for
          blocks where no text choices were found (image-based choices).
        """
        # ── Pass 1: Validate each raw marker ──────────────────────────────────
        #
        # A marker is valid only if text answer choices (A/B/C/D) are found
        # within its raw preliminary span (marker → next raw marker).
        #
        # This discards formula chart rows, numbered instruction lines, and
        # other non-question "1." patterns that have no adjacent choices.
        # It does NOT use a span-length fallback — a short span with no choices
        # (e.g., "1 mile = ..." immediately followed by "1 yard = ...") must
        # still be discarded.

        valid_markers: list[_QuestionMarker] = []

        for i, marker in enumerate(all_markers):
            next_raw = all_markers[i + 1] if i + 1 < len(all_markers) else None
            prelim_end_page, prelim_end_y = self._compute_prelim_end(
                marker, next_raw, page_heights
            )

            last_choice = self._find_last_answer_choice_in_range(
                answer_choices,
                start_page=marker.page_number,
                start_y=marker.y_top,
                end_page=prelim_end_page,
                end_y=prelim_end_y,
            )

            if last_choice is not None:
                # Text answer choices confirmed — this is a real question
                valid_markers.append(marker)
            else:
                # No text choices found — could be a griddable question or one
                # whose choices are embedded in an image.
                # Distinguish from formula chart rows by checking the span height:
                #   formula chart row  →  ~20 pts (adjacent unit conversion lines)
                #   real question      →  ≥ MIN_QUESTION_HEIGHT_PTS pts
                # Also cap by MAX_QUESTION_SPAN_PAGES to reject multi-page reference
                # sections that somehow have no detectable choices.
                prelim_height = self._compute_prelim_height(
                    marker, prelim_end_page, prelim_end_y, page_heights
                )
                span_pages = prelim_end_page - marker.page_number + 1
                if (prelim_height >= MIN_QUESTION_HEIGHT_PTS
                        and span_pages <= MAX_QUESTION_SPAN_PAGES):
                    valid_markers.append(marker)

        # ── Deduplicate: keep first valid occurrence of each question number ──
        seen: set[int] = set()
        deduped: list[_QuestionMarker] = []
        for m in valid_markers:
            if m.question_number not in seen:
                seen.add(m.question_number)
                deduped.append(m)

        # ── Pass 2: Build tight blocks from valid, deduped markers ────────────

        blocks: list[QuestionBlock] = []

        for i, marker in enumerate(deduped):
            next_valid = deduped[i + 1] if i + 1 < len(deduped) else None
            prelim_end_page, prelim_end_y = self._compute_prelim_end(
                marker, next_valid, page_heights
            )

            # Find the tight bottom using the last answer choice in the valid span
            last_choice = self._find_last_answer_choice_in_range(
                answer_choices,
                start_page=marker.page_number,
                start_y=marker.y_top,
                end_page=prelim_end_page,
                end_y=prelim_end_y,
            )

            if last_choice is not None:
                # Tight bottom: end immediately after the last answer choice
                tight_bottom_page = last_choice.page_number
                tight_bottom_y = last_choice.y_bottom + BLOCK_BOTTOM_PADDING
            else:
                # Fallback for image-based choices: cap to current page to avoid
                # capturing the next page's header/passage text in this block's image.
                if prelim_end_page > marker.page_number:
                    tight_bottom_page = marker.page_number
                    tight_bottom_y = page_heights[marker.page_number]
                else:
                    tight_bottom_page = prelim_end_page
                    tight_bottom_y = prelim_end_y

            # Clamp computed tight bottom so it never extends beyond the
            # preliminary end (the next marker's top). This prevents overlapping
            # blocks even when the last choice + padding would otherwise cross
            # page boundaries into the next question's area.
            if (
                tight_bottom_page > prelim_end_page
                or (tight_bottom_page == prelim_end_page and tight_bottom_y > prelim_end_y)
            ):
                tight_bottom_page = prelim_end_page
                tight_bottom_y = prelim_end_y

            y_top = max(0.0, marker.y_top - BLOCK_TOP_PADDING)
            slices = self._make_slices(
                start_page=marker.page_number,
                y_top=y_top,
                end_page=tight_bottom_page,
                y_bottom=min(tight_bottom_y, page_heights[tight_bottom_page]),
                page_heights=page_heights,
            )

            blocks.append(QuestionBlock(
                question_number=marker.question_number,
                slices=slices,
                text_preview=marker.text_preview,
            ))

        return blocks

    # ── Block Building Helpers ────────────────────────────────────────────────

    def _compute_prelim_end(
        self,
        marker: _QuestionMarker,
        next_marker: Optional[_QuestionMarker],
        page_heights: list[float],
    ) -> tuple[int, float]:
        """
        Return (end_page, end_y) for the preliminary span of a question block.

        The span ends just before the next marker starts, or at the bottom of
        the marker's page if there is no next marker.
        """
        if next_marker is None:
            return marker.page_number, page_heights[marker.page_number]
        return next_marker.page_number, next_marker.y_top

    def _compute_prelim_height(
        self,
        marker: _QuestionMarker,
        prelim_end_page: int,
        prelim_end_y: float,
        page_heights: list[float],
    ) -> float:
        """
        Return the total vertical height (PDF points) of a preliminary block span.

        Used to distinguish substantial question spans (griddable questions,
        image-choice questions) from formula chart rows that are only ~20 pts tall.
        """
        if prelim_end_page == marker.page_number:
            return max(0.0, prelim_end_y - marker.y_top)

        # Cross-page span: first page partial + full middle pages + last page partial
        height = page_heights[marker.page_number] - marker.y_top
        for p in range(marker.page_number + 1, prelim_end_page):
            height += page_heights[p]
        height += prelim_end_y
        return height

    def _make_slices(
        self,
        start_page: int,
        y_top: float,
        end_page: int,
        y_bottom: float,
        page_heights: list[float],
    ) -> list[PageSlice]:
        """
        Build PageSlice list for a block that spans start_page/y_top to end_page/y_bottom.

        Single-page blocks produce one slice.
        Cross-page blocks produce one slice per page: the first page from
        y_top to page bottom, any full middle pages, and the final page
        from the top to y_bottom.
        """
        if start_page == end_page:
            return [PageSlice(page_number=start_page, y_top=y_top, y_bottom=y_bottom)]

        slices: list[PageSlice] = []

        # First page: from question marker to end of page
        slices.append(PageSlice(
            page_number=start_page,
            y_top=y_top,
            y_bottom=page_heights[start_page],
        ))

        # Middle pages (rare — only for very tall questions spanning 3+ pages)
        for p in range(start_page + 1, end_page):
            slices.append(PageSlice(
                page_number=p,
                y_top=0.0,
                y_bottom=page_heights[p],
            ))

        # Final page: from top of page to tight bottom boundary
        slices.append(PageSlice(
            page_number=end_page,
            y_top=0.0,
            y_bottom=y_bottom,
        ))

        return slices

    # ── Vision Fallback ───────────────────────────────────────────────────────

    def _find_first_marker_by_vision(
        self,
        pdf_path: Path,
        page_heights: list[float],
    ) -> Optional[_QuestionMarker]:
        """
        Use Claude vision to locate Q1 when text extraction fails.

        Renders candidate pages as PNG images and asks Claude to identify
        the page and approximate vertical position of Q1.

        Returns:
            A single _QuestionMarker for Q1, or None if not found.
        """
        scan_end = min(MIN_CONTENT_PAGE + MAX_VISION_SCAN_PAGES, len(page_heights))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for page_idx in range(MIN_CONTENT_PAGE, scan_end):
                image_path = tmp_path / f"page_{page_idx}.png"
                render_page_as_image(pdf_path, page_idx, image_path)

                prompt = (
                    "This is a page from a math worksheet. "
                    "Does it contain the very first question (labeled '1.' or '1)' or 'Question 1')? "
                    "Respond with JSON only, no explanation: "
                    '{"has_first_question": true, "approximate_y_percent": 0-100} '
                    "where approximate_y_percent is the vertical position of Q1 "
                    "as a percentage from the top of the page (0=top, 100=bottom)."
                )

                response = self._claude.complete_with_image(prompt, image_path)

                if '"has_first_question": true' in response.lower():
                    y_pct = 30.0
                    try:
                        start = response.find('{')
                        end = response.rfind('}') + 1
                        if start >= 0 and end > start:
                            data = json.loads(response[start:end])
                            y_pct = float(data.get("approximate_y_percent", 30))
                    except (json.JSONDecodeError, ValueError, KeyError):
                        pass

                    y_top = page_heights[page_idx] * (y_pct / 100.0)
                    return _QuestionMarker(
                        question_number=1,
                        page_number=page_idx,
                        y_top=y_top,
                        text_preview="[Detected via Claude vision fallback]",
                    )

        return None


# ─── Line Extraction Helper ────────────────────────────────────────────────────


def _extract_lines_with_coords(page) -> list[tuple[float, float, str]]:
    """
    Group pdfplumber words into text lines by y-coordinate proximity.

    Words within LINE_Y_TOLERANCE pts of each other are treated as the
    same line. Returns list of (y_top, y_bottom, line_text) sorted top to bottom.

    y_top is the minimum word 'top' value in the line cluster.
    y_bottom is the maximum word 'bottom' value in the line cluster — used
    to compute tight crop boundaries below the last answer choice.

    Args:
        page: A pdfplumber Page object.

    Returns:
        List of (y_top, y_bottom, line_text) tuples sorted top to bottom.
    """
    words = page.extract_words() or []
    if not words:
        return []

    # Cluster words into lines by proximity of their 'top' coordinate
    groups: dict[float, list[dict]] = {}
    for word in words:
        y = float(word["top"])
        assigned_y: Optional[float] = None
        for group_y in groups:
            if abs(group_y - y) <= LINE_Y_TOLERANCE:
                assigned_y = group_y
                break
        if assigned_y is None:
            groups[y] = [word]
        else:
            groups[assigned_y].append(word)

    # Sort each line's words left to right, then build text and compute bounds
    lines: list[tuple[float, float, str]] = []
    for y, group_words in sorted(groups.items()):
        sorted_words = sorted(group_words, key=lambda w: float(w["x0"]))
        line_text = " ".join(w["text"] for w in sorted_words)
        y_bottom = max(float(w["bottom"]) for w in group_words)
        lines.append((y, y_bottom, line_text))

    return lines


# ─── Exceptions ───────────────────────────────────────────────────────────────


class BlockDetectionError(Exception):
    """Raised when question block boundaries cannot be detected in a PDF."""
    pass
