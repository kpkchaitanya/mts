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
import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_logger = logging.getLogger("mts")

# Maximum seconds allowed for pdfminer to parse a single page.
# Some PDFs contain malformed content streams that cause pdfminer to spin
# indefinitely; pages that exceed this budget are skipped.
_PAGE_PARSE_TIMEOUT_S = 10

import pdfplumber
import fitz  # PyMuPDF — used in _detect_image_heavy_blocks for content bbox queries

from src.config import (
    CR_BLANK_GAP_THRESHOLD,
    CR_BLANK_LINES_KEEP,
    CR_LINE_HEIGHT_PTS,
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
# Matches a standalone question number on its own line, as used in
# NY released-test format (e.g., NY Grades 3–8 Mathematics assessments).
# In this format the question number appears as a sidebar label on a line
# by itself, positioned 6–10 pts below the first line of the question stem:
#
#   "What is the product of 432 and 6 ?"   ← stem line  (y=278)
#   "5"                                    ← number line (y=284)
#   "A  2,482"                             ← first choice
#
# Pattern captures 1–2 digit numbers (question numbers are typically 1–30)
# on a line that contains NOTHING else (after stripping whitespace).
# False-positive numbers embedded in content (e.g., fractions, equations)
# are eliminated by Pass 1 validation which requires adjacent A/B/C/D choices.
NY_SIDEBAR_NUMBER_PATTERN = re.compile(r"^\s*(\d{1,2})\s*$")

# Maximum vertical distance (PDF points) between the NY sidebar number line
# and the stem line immediately above it.  The offset in released NY PDFs is
# consistently 6–7 pts.  The lookahead is set to 20 pts to tolerate font or
# layout variation without catching unrelated number lines on the same page.
NY_NUMBER_STEM_LOOKAHEAD_PTS: float = 20.0

# Maximum x0 (distance from left page edge, in PDF points) for a standalone
# number to be treated as an NY sidebar question marker.  Real question numbers
# appear in the narrow left sidebar (x0 ≈ 42–56 pts).  Numbers embedded in
# problem text — fractions, inline answers, page labels — appear at x0 ≥ 79.
# A threshold of 72 (1 inch) cleanly separates the two populations.
NY_SIDEBAR_MAX_X_PTS: float = 72.0
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

# Minimum vertical gap (PDF points) between a block's text-based y_bottom and
# the bottom of detected drawings on the same page before the drawing-expansion
# pass will extend the block's y_bottom.  Small gaps (< 20 pts) are typically
# decorative underlines or grid lines; large gaps indicate answer-choice diagrams
# that extend well below their letter labels.
VECTOR_EXPANSION_MIN_GAP_PTS: float = 20.0

# Fraction of page area (width × height) that a single embedded raster image
# must cover for the page to be treated as a full-page image block in a
# mixed-format text_rich document.  0.85 = 85% of the page area — this allows
# for small white borders around scanned question images.
MIXED_FORMAT_IMAGE_MIN_COVERAGE: float = 0.85

# Maximum pixel standard deviation (0–255 range) of a downsampled page render
# for the page to be treated as a question page in a mixed-format document.
#
# Black-text-on-white question pages have low std-dev (~10) because most pixels
# are near-white with occasional near-black text pixels.  Colorful cover pages,
# session header pages, and instruction pages with background fills have high
# std-dev (~40+) due to color variation.  A threshold of 25 reliably separates
# the two groups without needing any color-specific logic.
MIXED_FORMAT_IMAGE_MAX_PIXEL_STDDEV: float = 25.0

# ─── Constructed-Response Trimming ───────────────────────────────────────────

# Lowercase prefix strings that mark the start of a constructed-response work
# area.  When any line in a block starts with one of these strings (after
# case-folding and stripping), the block's y_bottom is trimmed to just below
# that line + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS.
#
# Matching is startswith() so "Answer ___" and "Answer the question" both
# match "answer".  This produces a known false positive when a stem asks
# "Answer the following..." — accepted as a v1 trade-off (EC-CR-03).
CR_TRIM_MARKERS: list[str] = [
    "answer",
    "show your work",
    "explain",
    "describe",
    "justify",
    "write your answer",
]

# ─── Format Auto-detection ────────────────────────────────────────────────────

# Number of content pages sampled to classify PDF format.
IMAGE_HEAVY_SAMPLE_PAGES: int = 10

# If the sampled content pages average fewer than this many words, the PDF is
# classified as image-heavy (one visual question per page, e.g. EOG format).
# STAAR pages average 50-200 words; EOG question pages average ~3 words.
# NOTE: IMAGE_HEAVY_AVG_WORDS_THRESHOLD is retained for reference but is no longer
# used by _classify_format. Classification now uses IMAGE_HEAVY_MIN_FRACTION (majority
# vote) which is robust to PDFs that mix cover/instruction pages (word-rich) with
# image-heavy question pages — a pattern seen in NY released test PDFs.
IMAGE_HEAVY_AVG_WORDS_THRESHOLD: int = 10

# Fraction of sampled content pages that must have at most IMAGE_HEAVY_PAGE_MAX_WORDS
# words for the PDF to be classified as 'image_heavy'. Using a fraction (majority vote)
# instead of an average prevents instruction/cover pages from skewing the classification.
#
# Example: an NY released-test PDF with 3 instruction pages (word-rich) and 7 question
# pages (image-only, ≤5 words) in the first 10 sampled pages → fraction = 0.70 ≥ 0.5
# → correctly classified as 'image_heavy'.
#
# A STAAR PDF where all 10 sampled pages are word-rich → fraction = 0.00 < 0.5
# → correctly classified as 'text_rich'.
IMAGE_HEAVY_MIN_FRACTION: float = 0.5

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

        # Apply the answer key fence to the text_rich path so that answer key
        # pages (common in released test PDFs) are excluded from marker scanning.
        total_pages = len(page_heights)
        fence = self._find_answer_key_fence(pdf_path, total_pages)

        # All markers, not yet deduplicated — dedup happens after validation
        all_markers = self._find_all_question_markers(pdf_path)

        # Filter out markers on or after the answer key fence page.
        all_markers = [m for m in all_markers if m.page_number < fence]
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

        # In mixed-format documents (e.g. NY released tests), some pages are
        # raster images with no extractable text — pdfplumber returns 0 words.
        # Add full-page blocks for those pages so their questions are not lost.
        image_blocks = self._find_mixed_format_image_blocks(
            pdf_path, page_heights, fence
        )
        if image_blocks:
            all_pages_covered = {s.page_number for b in blocks for s in b.slices}
            new_image_blocks = [
                b for b in image_blocks
                if b.slices[0].page_number not in all_pages_covered
            ]
            if new_image_blocks:
                blocks = sorted(
                    blocks + new_image_blocks,
                    key=lambda b: (b.slices[0].page_number, b.slices[0].y_top),
                )

        # Expand y_bottom to include vector-drawn answer choice diagrams (e.g. NY
        # released-test geometry questions where A/B/C/D options are drawings, not
        # text).  This is a no-op for purely text-choice exams (STAAR).
        blocks = self._expand_blocks_for_vector_choices(pdf_path, blocks, page_heights)

        # Trim constructed-response blocks: shorten y_bottom to just below the
        # first "Answer"/"Explain"/"Show your work" line + 2 blank lines, so the
        # compacted output does not waste space on large blank work areas.
        blocks = self._trim_constructed_response_blocks(pdf_path, blocks)

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
        Uses a fraction-based majority vote: if at least IMAGE_HEAVY_MIN_FRACTION
        of sampled pages have at most IMAGE_HEAVY_PAGE_MAX_WORDS words, the format
        is classified as 'image_heavy'.

        This approach is robust to PDFs that mix word-rich cover/instruction pages
        with image-heavy question pages (e.g. NY released test format), where a
        simple average would inflate the word count and produce a wrong classification.

        Returns:
            'image_heavy' or 'text_rich'
        """
        # Count how many sampled pages qualify as image-heavy (≤ max words per page).
        # Each qualifying page represents one image-based question page.
        image_heavy_page_count = 0
        pages_sampled = 0
        with pdfplumber.open(pdf_path) as pdf:
            sample_end = min(MIN_CONTENT_PAGE + IMAGE_HEAVY_SAMPLE_PAGES, len(pdf.pages))
            for page_idx in range(MIN_CONTENT_PAGE, sample_end):
                word_count = len(pdf.pages[page_idx].extract_words())
                # A page qualifies as image-heavy when its word count falls at or below
                # IMAGE_HEAVY_PAGE_MAX_WORDS (default 5). Blank pages (0 words) are
                # included in the count; they are already excluded by _detect_image_heavy_blocks.
                if word_count <= IMAGE_HEAVY_PAGE_MAX_WORDS:
                    image_heavy_page_count += 1
                pages_sampled += 1
        if pages_sampled == 0:
            return "text_rich"
        fraction = image_heavy_page_count / pages_sampled
        return "image_heavy" if fraction >= IMAGE_HEAVY_MIN_FRACTION else "text_rich"

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

        Supports two question numbering formats:

        STAAR-style (standard): question number leads the line.
            Example: "1. Which of the following ..."
            Detected by QUESTION_LINE_PATTERN.

        NY released-test style (sidebar number): the question number appears
        on its own line just below the first line of the stem (6–10 pts gap).
            Example: stem line "What is the product of 432 and 6?" at y=278,
                     then "5" on its own line at y=284.
            Detected by NY_SIDEBAR_NUMBER_PATTERN; y_top is walked back to the
            stem line above the number (within NY_NUMBER_STEM_LOOKAHEAD_PTS).

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

                # Extract all lines for this page so we can look backwards for
                # the NY-style stem line that precedes a sidebar number.
                _ex = ThreadPoolExecutor(max_workers=1)
                try:
                    lines = _ex.submit(
                        _extract_lines_with_coords, page
                    ).result(timeout=_PAGE_PARSE_TIMEOUT_S)
                except FuturesTimeoutError:
                    _logger.warning(
                        f"Page {page_idx + 1} timed out during marker scan "
                        f"({_PAGE_PARSE_TIMEOUT_S}s) — skipping."
                    )
                    _ex.shutdown(wait=False)
                    continue
                except Exception as exc:
                    _logger.warning(
                        f"Page {page_idx + 1} failed during marker scan: {exc} — skipping."
                    )
                    continue
                finally:
                    _ex.shutdown(wait=False)

                for line_idx, (y_top, y_bottom, line_text, x_min) in enumerate(lines):
                    # ── STAAR path: number leads the line ("1. Which...") ─────
                    match = QUESTION_LINE_PATTERN.match(line_text)
                    if match:
                        markers.append(_QuestionMarker(
                            question_number=int(match.group(1)),
                            page_number=page_idx,
                            y_top=y_top,
                            text_preview=line_text[:60],
                        ))
                        continue

                    # ── NY path: standalone number below the stem line ────────
                    # The number appears on its own line (e.g., just "5") with
                    # the question stem on the line immediately above within
                    # NY_NUMBER_STEM_LOOKAHEAD_PTS vertical distance.
                    ny_match = NY_SIDEBAR_NUMBER_PATTERN.match(line_text)
                    if ny_match:
                        # Reject numbers that appear in mid-page content (fractions,
                        # inline answers).  Real NY sidebar question numbers sit at
                        # the left margin (x0 ≤ NY_SIDEBAR_MAX_X_PTS).
                        if x_min > NY_SIDEBAR_MAX_X_PTS:
                            continue
                        q_num = int(ny_match.group(1))
                        # Walk back to find the stem line immediately above.
                        # Only look at the single preceding line; if it is within
                        # the lookahead window, use its y_top as the block start.
                        stem_y = y_top
                        stem_preview = line_text[:60]
                        if line_idx > 0:
                            prev_y_top, _prev_y_bot, prev_text, _prev_x = lines[line_idx - 1]
                            gap = y_top - prev_y_top
                            if 0 < gap <= NY_NUMBER_STEM_LOOKAHEAD_PTS:
                                # Found the stem — anchor the block at the stem,
                                # not at the number line.
                                stem_y = prev_y_top
                                stem_preview = prev_text[:60]
                        markers.append(_QuestionMarker(
                            question_number=q_num,
                            page_number=page_idx,
                            y_top=stem_y,
                            text_preview=stem_preview,
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
                # Use a per-page thread so a hung pdfminer parse can be abandoned
                # without blocking every subsequent page.
                _ex = ThreadPoolExecutor(max_workers=1)
                try:
                    lines = _ex.submit(
                        _extract_lines_with_coords, page
                    ).result(timeout=_PAGE_PARSE_TIMEOUT_S)
                except FuturesTimeoutError:
                    _logger.warning(
                        f"Page {page_idx + 1} timed out during answer-choice scan "
                        f"({_PAGE_PARSE_TIMEOUT_S}s) — skipping."
                    )
                    _ex.shutdown(wait=False)
                    continue
                except Exception as exc:
                    _logger.warning(
                        f"Page {page_idx + 1} failed during answer-choice scan: {exc} — skipping."
                    )
                    continue
                finally:
                    _ex.shutdown(wait=False)
                for y_top, y_bottom, line_text, _x_min in lines:
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
            # On the end page: choice must be strictly above the next question marker.
            # Use strict > (not >=) so that choices whose y_top coincides exactly
            # with the next marker's y_top are still attributed to the current block.
            # In NY sidebar format the next question's number label and the current
            # question's first answer choice share the same y-coordinate; the >=
            # form incorrectly excluded those choices (BUG-XXX).
            if choice.page_number == end_page and choice.y_top > end_y:
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

    # ── Mixed-format raster page detection ───────────────────────────────────

    def _find_mixed_format_image_blocks(
        self,
        pdf_path: Path,
        page_heights: list[float],
        fence: int,
    ) -> list[QuestionBlock]:
        """
        Find full-page raster pages in a text_rich document and return them as blocks.

        Some NY released-test PDFs embed a handful of pages as scanned bitmaps
        (0 extractable words, one full-page JPEG/FlateDecode image) while the rest
        of the document has rich text.  These pages contain real questions that the
        text-based marker scan cannot detect.

        A page qualifies as a mixed-format image block when ALL of:
          1. pdfplumber word count == 0 (no extractable text)
          2. At least one embedded image exists whose bbox covers ≥
             MIXED_FORMAT_IMAGE_MIN_COVERAGE (85%) of the page area
          3. Page index is ≥ MIN_CONTENT_PAGE and < fence

        Each qualifying page produces one QuestionBlock (full-page slice), using
        the same y_bottom logic as _find_image_heavy_y_bottom.  The
        question_number is set to 0 — upstream code sorts by page order so the
        block lands in the right position; the label overlay is suppressed for
        text_rich mode anyway.

        Args:
            pdf_path:     Source PDF path.
            page_heights: Page heights in PDF points (from _get_page_geometry).
            fence:        Answer key fence page index (exclusive upper bound).

        Returns:
            List of QuestionBlock (may be empty if no raster pages found).
        """
        blocks: list[QuestionBlock] = []
        fitz_doc = fitz.open(str(pdf_path))
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_idx in range(MIN_CONTENT_PAGE, min(fence, len(page_heights))):
                    # Must have zero pdfplumber words
                    plumber_words = pdf.pages[page_idx].extract_words()
                    if plumber_words:
                        continue


                    # Must have at least one full-page-covering image
                    fitz_page = fitz_doc[page_idx]
                    page_w = fitz_page.rect.width
                    page_h = fitz_page.rect.height
                    page_area = page_w * page_h
                    if page_area <= 0:
                        continue

                    has_full_page_image = False
                    for info in fitz_page.get_image_info():
                        bbox = info.get("bbox")
                        if bbox is None:
                            continue
                        img_w = bbox[2] - bbox[0]
                        img_h = bbox[3] - bbox[1]
                        coverage = (img_w * img_h) / page_area
                        if coverage >= MIXED_FORMAT_IMAGE_MIN_COVERAGE:
                            has_full_page_image = True
                            break

                    if not has_full_page_image:
                        continue

                    # Reject colorful instruction/section-header pages that happen
                    # to be raster.  Question pages are black-text on white — low
                    # pixel std-dev.  Cover/session-header pages with background
                    # fills have high std-dev (≥ 25).  We render a tiny 10%-scale
                    # thumbnail of the center 80% of the page for speed.
                    center_clip = fitz.Rect(
                        fitz_page.rect.width * 0.1,
                        fitz_page.rect.height * 0.1,
                        fitz_page.rect.width * 0.9,
                        fitz_page.rect.height * 0.9,
                    )
                    thumb = fitz_page.get_pixmap(
                        matrix=fitz.Matrix(0.1, 0.1),
                        clip=center_clip,
                        colorspace=fitz.csGRAY,
                    )
                    if thumb.samples:
                        vals = list(thumb.samples)
                        mean_v = sum(vals) / len(vals)
                        variance = sum((v - mean_v) ** 2 for v in vals) / len(vals)
                        stddev = variance ** 0.5
                        if stddev >= MIXED_FORMAT_IMAGE_MAX_PIXEL_STDDEV:
                            # Likely a coloured heading / instruction page — skip
                            continue
                    y_bottom = self._find_image_heavy_y_bottom(
                        fitz_page, page_heights[page_idx], plumber_words
                    )
                    blocks.append(QuestionBlock(
                        question_number=0,
                        slices=[PageSlice(
                            page_number=page_idx,
                            y_top=0.0,
                            y_bottom=y_bottom,
                        )],
                        text_preview=f"(image page {page_idx + 1})",
                    ))
        finally:
            fitz_doc.close()

        return blocks

    # ── Vector-choice expansion ───────────────────────────────────────────────

    def _expand_blocks_for_vector_choices(
        self,
        pdf_path: Path,
        blocks: list[QuestionBlock],
        page_heights: list[float],
    ) -> list[QuestionBlock]:
        """
        Extend each block's y_bottom to cover vector-drawn answer choice diagrams.

        Some exam formats (e.g. NY released tests) use geometric or pictorial
        answer choices rendered as PDF vector drawings rather than text.  In
        these blocks the text anchor for pdfplumber is only the letter labels
        (A, B, C, D) — the actual shapes extend significantly below.

        Strategy:
          For each block, query PyMuPDF drawing bboxes on the last slice's
          page.  A drawing qualifies for expansion if:
            (a) its bottom (y1) extends past the current text-based y_bottom,
            (b) it is within the content zone (above the footer zone),
            (c) it is not a white-filled layout container (all fill channels >= 0.95).
          The maximum qualifying y1 + BLOCK_BOTTOM_PADDING becomes the new
          y_bottom, capped at the footer zone top and the next block's y_top
          on the same page.  If the net gain is < VECTOR_EXPANSION_MIN_GAP_PTS
          the block is not expanded (avoids spurious expansions from thin rules).

        This is a no-op for purely text-choice exams (STAAR) where drawings
        are decorative and the text y_bottom is already correct.

        Args:
            pdf_path:     Source PDF path.
            blocks:       Current list of QuestionBlock from _build_blocks.
            page_heights: Page heights in PDF points.

        Returns:
            New list of QuestionBlock with expanded y_bottom where applicable.
        """
        if not blocks:
            return blocks

        # Build a page → [block_idx, ...] index for next-block lookup
        page_to_blocks: dict[int, list[int]] = {}
        for idx, block in enumerate(blocks):
            last_page = block.slices[-1].page_number
            page_to_blocks.setdefault(last_page, []).append(idx)

        fitz_doc = fitz.open(str(pdf_path))
        try:
            for block_idx, block in enumerate(blocks):
                last_slice = block.slices[-1]
                page_idx = last_slice.page_number
                page_height = page_heights[page_idx]
                current_y_bottom = last_slice.y_bottom

                # Footer zone: do not extend into it
                footer_zone_top = page_height * (1.0 - IMAGE_HEAVY_FOOTER_ZONE_FRACTION)

                if current_y_bottom >= footer_zone_top:
                    # Already reaches the footer zone — nothing to expand
                    continue

                # Find the next block that starts on the same page (upper bound
                # for expansion so we never overlap the next question).
                next_block_y_top_same_page: float = footer_zone_top
                for other_idx in page_to_blocks.get(page_idx, []):
                    if other_idx <= block_idx:
                        continue
                    other_first_slice = blocks[other_idx].slices[0]
                    if other_first_slice.page_number == page_idx:
                        next_block_y_top_same_page = min(
                            next_block_y_top_same_page,
                            other_first_slice.y_top,
                        )

                # Query PyMuPDF drawings on this page
                fitz_page = fitz_doc[page_idx]
                max_drawing_y: float = current_y_bottom
                for drawing in fitz_page.get_drawings():
                    rect = drawing.get("rect")
                    if rect is None:
                        continue

                    # Skip white-filled rectangles — these are layout containers
                    # (answer-box backgrounds, section dividers) rather than
                    # content shapes.  White fill: all channels >= 0.95.
                    fill = drawing.get("fill")
                    if fill is not None and all(ch >= 0.95 for ch in fill[:3]):
                        continue

                    draw_y1 = rect.y1

                    # Include drawings whose bottom extends past the current
                    # crop boundary AND lies within the allowed expansion zone.
                    # Using rect.y1 > current_y_bottom (not rect.y0) captures
                    # shapes that START before the text label (as is typical for
                    # side-by-side image choices) but END below the text y_bottom.
                    if (rect.y1 > current_y_bottom
                            and draw_y1 <= footer_zone_top
                            and draw_y1 <= next_block_y_top_same_page):
                        max_drawing_y = max(max_drawing_y, draw_y1)

                gap = max_drawing_y - current_y_bottom
                if gap < VECTOR_EXPANSION_MIN_GAP_PTS:
                    # Drawings only marginally extend beyond text bottom
                    # (e.g., decorative underlines) — do not expand
                    continue

                # Expand the last slice's y_bottom
                new_y_bottom = min(
                    max_drawing_y + BLOCK_BOTTOM_PADDING,
                    footer_zone_top,
                    next_block_y_top_same_page,
                )
                expanded_slice = PageSlice(
                    page_number=last_slice.page_number,
                    y_top=last_slice.y_top,
                    y_bottom=new_y_bottom,
                )
                blocks[block_idx] = QuestionBlock(
                    question_number=block.question_number,
                    slices=block.slices[:-1] + [expanded_slice],
                    text_preview=block.text_preview,
                )
        finally:
            fitz_doc.close()

        return blocks

    # ── Constructed-Response Trimming ─────────────────────────────────────────

    def _trim_constructed_response_blocks(
        self,
        pdf_path: Path,
        blocks: list[QuestionBlock],
    ) -> list[QuestionBlock]:
        """
        Shorten constructed-response blocks by trimming blank work-area space.

        Strategy — two-pass:
          Pass 1 (CR detection): confirm the block is a constructed-response
            block by checking whether any line within the slice starts with a
            CR_TRIM_MARKERS string.
          Pass 2 (crop point): scan consecutive-line gaps > CR_BLANK_GAP_THRESHOLD
            (default 100 pts).  For each candidate gap, verify via PyMuPDF that
            no drawings exist in the interval — diagram regions between text lines
            must not be mistaken for student-work blanks.  Crop at the first
            *empty* gap: y_bottom = last_content_line_y + CR_BLANK_LINES_KEEP *
            CR_LINE_HEIGHT_PTS.

          Fallback: if no empty large gap is found but a trim marker was
            detected, crop at trim_marker_y + padding.
        """
        if not blocks:
            return blocks

        trimmed: list[QuestionBlock] = []
        fitz_doc = fitz.open(str(pdf_path))
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for block in blocks:
                    last_slice = block.slices[-1]
                    page_idx = last_slice.page_number

                    if page_idx >= len(pdf.pages):
                        trimmed.append(block)
                        continue

                    plumber_page = pdf.pages[page_idx]
                    words = plumber_page.extract_words(
                        x_tolerance=3,
                        y_tolerance=3,
                        keep_blank_chars=False,
                    )

                    # Build sorted line list within the slice's vertical span
                    lines: list[tuple[float, str]] = []
                    current_line_y: float = -999.0
                    current_words: list[str] = []
                    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
                        if abs(word["top"] - current_line_y) > LINE_Y_TOLERANCE:
                            if current_words:
                                lines.append((current_line_y, " ".join(current_words)))
                            current_line_y = word["top"]
                            current_words = [word["text"]]
                        else:
                            current_words.append(word["text"])
                    if current_words:
                        lines.append((current_line_y, " ".join(current_words)))

                    slice_lines = [
                        (y, txt) for y, txt in lines
                        if last_slice.y_top <= y <= last_slice.y_bottom
                    ]

                    # ── Pass 1: confirm CR block ───────────────────────────
                    is_cr = False
                    first_trim_y: Optional[float] = None
                    for line_y, line_text in slice_lines:
                        lowered = line_text.strip().lower()
                        for marker in CR_TRIM_MARKERS:
                            if lowered.startswith(marker):
                                is_cr = True
                                if first_trim_y is None:
                                    first_trim_y = line_y
                                break

                    if not is_cr:
                        trimmed.append(block)
                        continue

                    # ── Pass 2: find first empty large gap ─────────────────
                    # Collect drawing y-extents to distinguish content-filled
                    # gaps (diagrams) from truly blank student-work areas.
                    fitz_page = fitz_doc[page_idx]
                    drawing_intervals: list[tuple[float, float]] = []
                    for drawing in fitz_page.get_drawings():
                        rect = drawing.get("rect")
                        if rect is None:
                            continue
                        fill = drawing.get("fill")
                        if fill is not None and all(ch >= 0.95 for ch in fill[:3]):
                            continue  # skip white-fill layout containers
                        drawing_intervals.append((rect.y0, rect.y1))

                    def gap_has_drawing(y_start: float, y_end: float) -> bool:
                        # A drawing counts as gap content only if it overlaps
                        # the gap by a meaningful amount (≥ 5 pts).  This
                        # prevents the question-number label box (which sits
                        # just above the gap start and overlaps by ~2 pts) from
                        # being mistaken for diagram content inside the blank.
                        MIN_OVERLAP = 5.0
                        for dy0, dy1 in drawing_intervals:
                            overlap = min(dy1, y_end) - max(dy0, y_start)
                            if overlap >= MIN_OVERLAP:
                                return True
                        return False

                    crop_y: Optional[float] = None
                    for i in range(len(slice_lines) - 1):
                        y_curr, _ = slice_lines[i]
                        y_next, _ = slice_lines[i + 1]
                        if y_next - y_curr > CR_BLANK_GAP_THRESHOLD:
                            if not gap_has_drawing(y_curr, y_next):
                                crop_y = y_curr
                                break
                            # Gap contains drawings — skip, keep scanning

                    if crop_y is not None:
                        new_y_bottom = crop_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS
                    elif first_trim_y is not None:
                        new_y_bottom = first_trim_y + CR_BLANK_LINES_KEEP * CR_LINE_HEIGHT_PTS
                    else:
                        trimmed.append(block)
                        continue

                    # Safety clamps
                    new_y_bottom = min(new_y_bottom, last_slice.y_bottom)
                    new_y_bottom = max(new_y_bottom, last_slice.y_top + CR_LINE_HEIGHT_PTS)

                    trimmed_slice = PageSlice(
                        page_number=last_slice.page_number,
                        y_top=last_slice.y_top,
                        y_bottom=new_y_bottom,
                    )
                    trimmed.append(QuestionBlock(
                        question_number=block.question_number,
                        slices=block.slices[:-1] + [trimmed_slice],
                        text_preview=block.text_preview,
                    ))
        finally:
            fitz_doc.close()

        return trimmed

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


def _extract_lines_with_coords(page) -> list[tuple[float, float, str, float]]:
    """
    Group pdfplumber words into text lines by y-coordinate proximity.

    Words within LINE_Y_TOLERANCE pts of each other are treated as the
    same line. Returns list of (y_top, y_bottom, line_text, x_min) sorted
    top to bottom.

    y_top is the minimum word 'top' value in the line cluster.
    y_bottom is the maximum word 'bottom' value in the line cluster — used
    to compute tight crop boundaries below the last answer choice.
    x_min is the minimum word 'x0' value in the line cluster — used to
    distinguish left-margin sidebar numbers from mid-page embedded numbers.

    Args:
        page: A pdfplumber Page object.

    Returns:
        List of (y_top, y_bottom, line_text, x_min) tuples sorted top to bottom.
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
    lines: list[tuple[float, float, str, float]] = []
    for y, group_words in sorted(groups.items()):
        sorted_words = sorted(group_words, key=lambda w: float(w["x0"]))
        line_text = " ".join(w["text"] for w in sorted_words)
        y_bottom = max(float(w["bottom"]) for w in group_words)
        x_min = min(float(w["x0"]) for w in group_words)
        lines.append((y, y_bottom, line_text, x_min))

    return lines


# ─── Exceptions ───────────────────────────────────────────────────────────────


class BlockDetectionError(Exception):
    """Raised when question block boundaries cannot be detected in a PDF."""
    pass
