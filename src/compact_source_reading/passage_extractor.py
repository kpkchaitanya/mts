"""
passage_extractor.py

Renders each page of a PassageGroup from the source ELA PDF as a PNG image,
trimming blank whitespace from the bottom of each page.

Unlike the math extractor (which crops sub-page regions per question block),
the reading extractor works at full-page granularity — each page is rendered
at the configured DPI, the blank footer rows are trimmed, and the result is
returned as PNG bytes.

Output: list of ExtractedPassageGroup objects, one per PassageGroup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from src.compact_source_reading.passage_detector import PassageGroup
from src.config import PDF_RENDER_DPI
from src.utils.image_utils import count_bottom_blank_rows_from_pixmap


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class ExtractedPage:
    """
    One rendered PDF page as a PNG image, ready for packing.

    Attributes:
        page_index:        Zero-based source page index.
        png_bytes:         PNG-encoded bytes of the (possibly trimmed) page.
        source_width_pts:  Page width in PDF points (pre-DPI).
        rendered_height_pts: Actual rendered height in PDF points after
                             blank-row trimming.
    """

    page_index: int
    png_bytes: bytes
    source_width_pts: float
    rendered_height_pts: float


@dataclass
class ExtractedPassageGroup:
    """
    All rendered pages for one PassageGroup, in output order.

    Attributes:
        passage_id:     The 4-digit selection ID from the source (e.g. "1503").
        pages:          Passage pages followed by question pages.
        passage_count:  Number of passage pages.
        question_count: Number of question pages.
    """

    passage_id: str
    pages: list[ExtractedPage] = field(default_factory=list)
    passage_count: int = 0
    question_count: int = 0


# ─── Extractor ────────────────────────────────────────────────────────────────


class PassageExtractor:
    """
    Renders passage group pages from a PDF as trimmed PNG images.

    Each page is rendered at the configured DPI.  Blank rows at the bottom
    of each page image are counted and trimmed in a second crop pass so that
    footers and trailing whitespace do not inflate the output height.
    """

    def __init__(self, dpi: int = PDF_RENDER_DPI) -> None:
        self._dpi = dpi

    def extract(
        self, pdf_path: Path, groups: list[PassageGroup]
    ) -> list[ExtractedPassageGroup]:
        """
        Render all pages of every passage group.

        Opens the PDF once and processes pages in document order for
        efficiency.

        Args:
            pdf_path: Path to the ELA source PDF.
            groups:   Ordered list of PassageGroups from PassageDetector.

        Returns:
            List of ExtractedPassageGroup objects in the same order as groups.
        """
        # Build a set of all page indices we need
        needed: dict[int, list[tuple[int, str]]] = {}
        for g_idx, group in enumerate(groups):
            for page_idx in group.passage_pages:
                needed.setdefault(page_idx, []).append((g_idx, "passage"))
            for page_idx in group.question_pages:
                needed.setdefault(page_idx, []).append((g_idx, "question"))

        doc = fitz.open(str(pdf_path))
        zoom = self._dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        # Initialise result containers
        results: list[ExtractedPassageGroup] = [
            ExtractedPassageGroup(
                passage_id=g.passage_id,
                passage_count=len(g.passage_pages),
                question_count=len(g.question_pages),
            )
            for g in groups
        ]

        # Render each needed page once, distribute to groups
        page_cache: dict[int, ExtractedPage] = {}
        for page_idx in sorted(needed.keys()):
            page_cache[page_idx] = self._render_page(doc, page_idx, matrix)

        doc.close()

        # Assemble groups in passage_pages + question_pages order
        for g_idx, group in enumerate(groups):
            extracted = results[g_idx]
            for page_idx in group.passage_pages:
                extracted.pages.append(page_cache[page_idx])
            for page_idx in group.question_pages:
                extracted.pages.append(page_cache[page_idx])

        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _render_page(
        self,
        doc: fitz.Document,
        page_idx: int,
        matrix: fitz.Matrix,
    ) -> ExtractedPage:
        """
        Render one PDF page as a PNG, trimming blank rows at the bottom.

        Args:
            doc:       Open PyMuPDF document.
            page_idx:  Zero-based page index.
            matrix:    Zoom matrix derived from configured DPI.

        Returns:
            ExtractedPage with trimmed PNG bytes and dimensions.
        """
        page = doc[page_idx]
        source_width_pts = page.rect.width
        page_height_pts = page.rect.height

        # Full-page render
        pm = page.get_pixmap(matrix=matrix)

        # Detect blank rows at the bottom
        blank_rows = count_bottom_blank_rows_from_pixmap(pm)
        if blank_rows > 0:
            trim_pts = (blank_rows * 72.0) / self._dpi
            new_bottom = max(0.0, page_height_pts - trim_pts)
            clip = fitz.Rect(0, 0, source_width_pts, new_bottom)
            pm = page.get_pixmap(matrix=matrix, clip=clip)

        rendered_height_pts = pm.height * 72.0 / self._dpi

        return ExtractedPage(
            page_index=page_idx,
            png_bytes=pm.tobytes("png"),
            source_width_pts=source_width_pts,
            rendered_height_pts=rendered_height_pts,
        )
