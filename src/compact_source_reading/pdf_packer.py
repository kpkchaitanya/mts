"""
pdf_packer.py  (compact_source_reading)

Assembles extracted passage group page images into a compact output PDF.

Layout rules for reading (ELA):
  - Pages are laid out sequentially, one extracted-page image per output page.
  - Each image is scaled to fill the content width (margin-to-margin),
    preserving aspect ratio.
  - If the scaled image fits entirely within the content height, it is centered
    vertically; otherwise it is placed flush to the top margin and allowed to
    run to the bottom (no cropping — content integrity is paramount).
  - Passage groups are kept together; no group splits across files.

Output: a PDF file at output_path; returns (pages_written, groups_written).
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from src.compact_source_reading.passage_extractor import ExtractedPassageGroup
from src.config import (
    OUTPUT_PAGE_HEIGHT_PTS,
    OUTPUT_PAGE_MARGIN_PTS,
    OUTPUT_PAGE_WIDTH_PTS,
)


class ReadingPdfPacker:
    """
    Packs extracted ELA passage group page images into a compact output PDF.

    Each ExtractedPage in each ExtractedPassageGroup is placed on its own
    output page, scaled to the content width.  Blank whitespace already
    trimmed by PassageExtractor means the rendered height is as tight as
    possible.
    """

    def __init__(
        self,
        page_width: float = OUTPUT_PAGE_WIDTH_PTS,
        page_height: float = OUTPUT_PAGE_HEIGHT_PTS,
        margin: float = OUTPUT_PAGE_MARGIN_PTS,
    ) -> None:
        self._page_w = page_width
        self._page_h = page_height
        self._margin = margin
        self._content_w = page_width - 2 * margin
        self._content_h = page_height - 2 * margin

    def pack(
        self,
        groups: list[ExtractedPassageGroup],
        output_path: Path,
    ) -> tuple[int, int]:
        """
        Write all passage group pages to a single output PDF.

        Args:
            groups:      Ordered list of ExtractedPassageGroup objects.
            output_path: Destination PDF path.

        Returns:
            Tuple of (total_pages_written, total_groups_written).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        pages_written = 0

        for group in groups:
            for ep in group.pages:
                self._place_page(doc, ep.png_bytes, ep.source_width_pts, ep.rendered_height_pts)
                pages_written += 1

        doc.save(str(output_path))
        doc.close()

        return pages_written, len(groups)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _place_page(
        self,
        doc: fitz.Document,
        png_bytes: bytes,
        source_width_pts: float,
        source_height_pts: float,
    ) -> None:
        """
        Insert one PNG image onto a new output page, scaled to content width.
        """
        if source_width_pts > 0:
            scale = self._content_w / source_width_pts
        else:
            scale = 1.0

        rendered_w = self._content_w
        rendered_h = source_height_pts * scale

        # Output page height: content needs + margins, but never smaller than
        # a standard letter page so the document looks consistent.
        out_page_h = max(self._page_h, rendered_h + 2 * self._margin)

        page = doc.new_page(width=self._page_w, height=out_page_h)

        x0 = self._margin
        y0 = self._margin
        x1 = x0 + rendered_w
        y1 = y0 + rendered_h

        page.insert_image(fitz.Rect(x0, y0, x1, y1), stream=png_bytes)
