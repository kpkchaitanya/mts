"""
tests/test_block_detector.py

Regression and unit tests for BlockDetector._find_image_heavy_y_bottom().

BUG-002 regression: Before the fix, _detect_image_heavy_blocks() hardcoded
y_bottom = page_height for every content page. This produced blocks with a
large blank gap at the bottom (~40 % of page height on EOG-style pages),
which rendered as dead whitespace in the compacted output PDF.

The fix replaced the hardcoded value with _find_image_heavy_y_bottom(), which
queries all PyMuPDF content bounding boxes and returns bottom-of-content +
BLOCK_BOTTOM_PADDING.

These tests verify:
  TC-BD-10  Content-aware y_bottom is well below page_height when content
            occupies only the top portion of the page.
  TC-BD-11  (BUG-002 regression) Hardcoded y_bottom = page_height would
            produce a blank_bottom_fraction > WHITESPACE_WARN_THRESHOLD,
            i.e. the whitespace checker would have flagged it.  The
            content-aware y_bottom does NOT exceed the threshold.
  TC-BD-12  When content spans text blocks, embedded raster images, AND
            vector drawings, y_bottom equals the lowest element + padding.
  TC-BD-13  When a page has no detectable content boxes, the method falls
            back to page_height (defensive guard).
  TC-BD-14  y_bottom never exceeds page_height even if padding would push
            it past the edge.
"""

import io
import pytest
import fitz  # PyMuPDF

from src.compact_source.block_detector import BlockDetector, BLOCK_BOTTOM_PADDING
from src.config import IMAGE_HEAVY_HEIGHT_WARN_FRACTION


# ─── Helpers ──────────────────────────────────────────────────────────────────

PAGE_W = 612.0   # Standard letter width  (PDF points)
PAGE_H = 792.0   # Standard letter height (PDF points)

# The fraction of page height that real content uses in EOG-style questions.
# Content (stem + diagrams + answer choices) ends around 60 % of the page;
# the remaining ~40 % is blank whitespace between the last choice and the
# page-number footer ("1 of 40").
CONTENT_FRACTION = 0.60


def _make_fitz_page_with_content(content_bottom_y: float) -> tuple:
    """
    Return (doc, page) where the page has a gray filled rect ending at
    content_bottom_y.  The area below that line is plain white.
    Caller must call doc.close() when done.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    rect = fitz.Rect(36, 36, PAGE_W - 36, content_bottom_y)
    page.draw_rect(rect, color=(0.5, 0.5, 0.5), fill=(0.5, 0.5, 0.5))
    return doc, page


# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def detector():
    """A BlockDetector instance (no PDF needed for unit-level method tests)."""
    return BlockDetector.__new__(BlockDetector)


# ─── TC-BD-10 ─────────────────────────────────────────────────────────────────

def test_content_aware_y_bottom_is_below_page_height(detector):
    """
    TC-BD-10: When content ends at 60 % of page height, y_bottom must be
    significantly less than page_height (no hardcoded full-page boundary).
    """
    content_bottom = PAGE_H * CONTENT_FRACTION   # 475.2 pts
    doc, page = _make_fitz_page_with_content(content_bottom)

    try:
        y_bottom = detector._find_image_heavy_y_bottom(page, PAGE_H)
    finally:
        doc.close()

    # Content-aware y_bottom should be near content_bottom + padding.
    assert y_bottom < PAGE_H, (
        f"y_bottom ({y_bottom:.1f}) == page_height ({PAGE_H}) — "
        "bug: hardcoded full-page boundary still in use"
    )
    # Should be within a few points of content_bottom + BLOCK_BOTTOM_PADDING.
    expected = content_bottom + BLOCK_BOTTOM_PADDING
    assert abs(y_bottom - expected) < 5.0, (
        f"y_bottom ({y_bottom:.1f}) deviates more than 5 pts from expected "
        f"({expected:.1f})"
    )


# ─── TC-BD-11  BUG-002 regression ─────────────────────────────────────────────

def test_bug_002_regression_height_fraction_check_catches_hardcoded_y_bottom(detector):
    """
    TC-BD-11 / BUG-002 regression:

    The compaction report flags blocks whose y_bottom / page_height >=
    IMAGE_HEAVY_HEIGHT_WARN_FRACTION.  This test verifies that:

      a) The pre-fix y_bottom (hardcoded page_height) produces a height
         fraction >= IMAGE_HEAVY_HEIGHT_WARN_FRACTION — the report WOULD
         have flagged it.

      b) The content-aware y_bottom produces a height fraction <
         IMAGE_HEAVY_HEIGHT_WARN_FRACTION — the report passes.
    """
    content_bottom = PAGE_H * CONTENT_FRACTION   # content ends at ~60 %
    doc, page = _make_fitz_page_with_content(content_bottom)

    try:
        content_aware_y_bottom = detector._find_image_heavy_y_bottom(page, PAGE_H)
    finally:
        doc.close()

    # --- pre-fix: hardcoded page_height ---
    buggy_y_bottom = PAGE_H
    buggy_fraction = buggy_y_bottom / PAGE_H  # 1.0

    # --- fixed: content-aware ---
    fixed_fraction = content_aware_y_bottom / PAGE_H

    assert buggy_fraction >= IMAGE_HEAVY_HEIGHT_WARN_FRACTION, (
        f"Buggy y_bottom fraction ({buggy_fraction:.3f}) should be >= "
        f"IMAGE_HEAVY_HEIGHT_WARN_FRACTION ({IMAGE_HEAVY_HEIGHT_WARN_FRACTION})"
    )

    assert fixed_fraction < IMAGE_HEAVY_HEIGHT_WARN_FRACTION, (
        f"Fixed y_bottom fraction ({fixed_fraction:.3f}) should be < "
        f"IMAGE_HEAVY_HEIGHT_WARN_FRACTION ({IMAGE_HEAVY_HEIGHT_WARN_FRACTION}). "
        "Content-aware y_bottom may still be anchored near page_height."
    )


# ─── TC-BD-12 ─────────────────────────────────────────────────────────────────

def test_y_bottom_uses_max_of_all_content_types(detector):
    """
    TC-BD-12: y_bottom equals the LOWEST element across text, embedded images,
    and vector drawings — whichever extends furthest down the page.

    Here a vector drawing extends lower than the text block, so y_bottom must
    reflect the drawing's bottom, not the text block's bottom.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    text_bottom = PAGE_H * 0.40    # text ends at 40 %
    drawing_bottom = PAGE_H * 0.55  # drawing extends to 55 %

    # Insert a text block via annotation so get_text("blocks") detects it.
    text_rect = fitz.Rect(36, 36, PAGE_W - 36, text_bottom)
    page.insert_textbox(text_rect, "Sample question text A B C D", fontsize=12)

    # Insert a vector drawing (filled rect) that extends past the text.
    draw_rect = fitz.Rect(36, text_bottom + 10, PAGE_W - 36, drawing_bottom)
    page.draw_rect(draw_rect, color=(0, 0, 0), fill=(0.8, 0.8, 0.8))

    try:
        y_bottom = detector._find_image_heavy_y_bottom(page, PAGE_H)
    finally:
        doc.close()

    # y_bottom must be at or below drawing_bottom (the lowest element).
    assert y_bottom >= drawing_bottom, (
        f"y_bottom ({y_bottom:.1f}) is above drawing_bottom ({drawing_bottom:.1f}). "
        "Method must use max across all content types."
    )
    assert y_bottom < PAGE_H, (
        f"y_bottom ({y_bottom:.1f}) == page_height — method fell back to full page."
    )


# ─── TC-BD-13 ─────────────────────────────────────────────────────────────────

def test_no_content_falls_back_to_page_height(detector):
    """
    TC-BD-13: When a page has no detectable content bounding boxes, the method
    must fall back to page_height (defensive guard).
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    # Blank page — no text, no images, no drawings.

    try:
        y_bottom = detector._find_image_heavy_y_bottom(page, PAGE_H)
    finally:
        doc.close()

    assert y_bottom == PAGE_H, (
        f"Expected page_height fallback ({PAGE_H}), got {y_bottom:.1f}"
    )


# ─── TC-BD-14 ─────────────────────────────────────────────────────────────────

def test_y_bottom_never_exceeds_page_height(detector):
    """
    TC-BD-14: y_bottom must be capped at page_height even when content extends
    to the very bottom edge of the page (padding would overshoot).
    """
    # Content ends at exactly page_height — padding would push past it.
    content_bottom = PAGE_H  # right at the edge
    doc, page = _make_fitz_page_with_content(content_bottom)

    try:
        y_bottom = detector._find_image_heavy_y_bottom(page, PAGE_H)
    finally:
        doc.close()

    assert y_bottom <= PAGE_H, (
        f"y_bottom ({y_bottom:.1f}) exceeds page_height ({PAGE_H}) — cap not applied."
    )
