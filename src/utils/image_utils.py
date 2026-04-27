"""
image_utils.py

Shared image-analysis utilities for the compact_source pipeline.

Provides pixel-level inspection of PNG block images — specifically,
measuring blank (near-white) rows at the bottom of a block image to
detect excess whitespace captured during block extraction.

Used by:
  - block_extractor.py  — trim trailing blank rows from cropped slices
  - reporter.py         — whitespace efficiency check on extracted blocks
"""

from __future__ import annotations

import fitz  # PyMuPDF


# ─── Constants ────────────────────────────────────────────────────────────────

# RGB channel value at or above which a pixel is considered near-white (blank).
DEFAULT_BLANK_THRESHOLD: int = 245

# Maximum fraction of an image height that will be scanned for blank rows.
# Prevents false-positive trimming of intentionally sparse content.
DEFAULT_MAX_BLANK_FRACTION: float = 0.5


# ─── Functions ────────────────────────────────────────────────────────────────


def count_bottom_blank_rows(
    png_bytes: bytes,
    threshold: int = DEFAULT_BLANK_THRESHOLD,
    max_fraction: float = DEFAULT_MAX_BLANK_FRACTION,
) -> int:
    """
    Count continuous blank (near-white) rows at the bottom of a PNG image.

    A row is considered blank if every pixel in that row has all RGB
    channels >= threshold. Scanning proceeds from the image bottom upward
    until a non-blank row is found or max_fraction of the image height
    is reached — whichever comes first.

    Args:
        png_bytes:    PNG-encoded image bytes.
        threshold:    Per-channel value above which a pixel is near-white.
        max_fraction: Maximum fraction of image height to scan (0.0–1.0).

    Returns:
        Number of continuous blank rows at the bottom. 0 if none or empty.
    """
    # fitz.Pixmap(bytes) decodes PNG/image bytes directly into a Pixmap
    # without going through the document API — single-pass, no temp file.
    pm = fitz.Pixmap(png_bytes)
    return _count_blank_rows_from_pixmap(pm, threshold, max_fraction)


def blank_bottom_fraction(
    png_bytes: bytes,
    threshold: int = DEFAULT_BLANK_THRESHOLD,
    max_fraction: float = DEFAULT_MAX_BLANK_FRACTION,
) -> float:
    """
    Return the fraction of an image's height that is blank rows at the bottom.

    Args:
        png_bytes:    PNG-encoded image bytes.
        threshold:    Per-channel threshold for near-white classification.
        max_fraction: Maximum fraction of height to scan.

    Returns:
        Float in [0.0, max_fraction]. Returns 0.0 for zero-height images.
    """
    pm = fitz.Pixmap(png_bytes)
    if pm.height == 0:
        return 0.0
    blank_rows = _count_blank_rows_from_pixmap(pm, threshold, max_fraction)
    return blank_rows / pm.height


def count_bottom_blank_rows_from_pixmap(
    pixmap: fitz.Pixmap,
    threshold: int = DEFAULT_BLANK_THRESHOLD,
    max_fraction: float = DEFAULT_MAX_BLANK_FRACTION,
) -> int:
    """
    Count continuous blank rows at the bottom of an already-decoded fitz Pixmap.

    This variant avoids re-decoding PNG bytes when the caller already holds
    a Pixmap (e.g., block_extractor.py during crop trimming).

    Args:
        pixmap:       Decoded fitz.Pixmap.
        threshold:    Per-channel threshold for near-white classification.
        max_fraction: Maximum fraction of height to scan.

    Returns:
        Number of continuous blank rows at the bottom. 0 for empty images.
    """
    return _count_blank_rows_from_pixmap(pixmap, threshold, max_fraction)


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _count_blank_rows_from_pixmap(
    pm: fitz.Pixmap,
    threshold: int,
    max_fraction: float,
) -> int:
    """
    Core row-scanning logic shared by all public functions.

    Scans pixel rows from the image bottom upward. A row is blank when
    every RGB pixel value is >= threshold. Alpha channels are ignored.

    Args:
        pm:           fitz.Pixmap to inspect.
        threshold:    Per-channel near-white threshold.
        max_fraction: Maximum fraction of height to scan.

    Returns:
        Count of continuous blank rows from the bottom. 0 for empty images.
    """
    if pm is None or pm.width == 0 or pm.height == 0:
        return 0

    n = pm.n            # bytes per pixel (3 = RGB, 4 = RGBA)
    w = pm.width
    h = pm.height
    row_stride = w * n
    samples = pm.samples

    # Cap the scan range to avoid trimming oversized amounts by accident.
    max_rows = int(h * max_fraction)
    if max_rows <= 0:
        return 0

    blank_rows = 0
    for row in range(h - 1, h - 1 - max_rows, -1):
        start = row * row_stride
        row_bytes = samples[start: start + row_stride]

        # Check every pixel in the row; stop at first non-blank pixel.
        is_blank = True
        for px in range(0, len(row_bytes), n):
            if n >= 3:
                r, g, b = row_bytes[px], row_bytes[px + 1], row_bytes[px + 2]
            else:
                # Grayscale — replicate value across channels.
                r = g = b = row_bytes[px]
            if r < threshold or g < threshold or b < threshold:
                is_blank = False
                break

        if is_blank:
            blank_rows += 1
        else:
            break

    return blank_rows
