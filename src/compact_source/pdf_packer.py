"""
pdf_packer.py

Assembles extracted question block images into a compact output PDF.

Layout rules (per spec):
  - Blocks are placed sequentially top to bottom with ZERO vertical gap.
  - All blocks are scaled to fit the content width (preserving aspect ratio).
  - When a block won't fit on the remaining space of the current page,
    a new page is started before placing it.
  - Blocks taller than the full content area are scaled down uniformly
    to fit on one page (minimum readable size; never cropped or split).

Output: a PDF file at output_path; returns the number of pages written.
"""

from pathlib import Path

import fitz  # PyMuPDF

from src.compact_source.block_extractor import ExtractedBlock
from src.config import (
    OUTPUT_PAGE_HEIGHT_PTS,
    OUTPUT_PAGE_MARGIN_PTS,
    OUTPUT_PAGE_WIDTH_PTS,
)


class PdfPacker:
    """
    Packs extracted question block images into a compact output PDF.

    Each block is placed as a PNG image inserted into a PyMuPDF page.
    No text is re-rendered — all visual content is carried directly from
    the cropped source images.
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

    def pack(self, blocks: list[ExtractedBlock], output_path: Path) -> int:
        """
        Pack all block images into a PDF file at output_path.

        Args:
            blocks: Extracted question blocks in document order.
            output_path: Destination path for the output PDF.

        Returns:
            Total number of pages in the output PDF.
        """
        doc = fitz.open()
        page = self._new_page(doc)
        current_y = float(self._margin)

        for block in blocks:
            # Scale block to fit content width, preserving aspect ratio
            scale = self._content_w / block.source_width_pts
            scaled_h = block.total_height_pts * scale

            # If the block is taller than the full content area, scale it down
            # uniformly so it fits on exactly one page
            if scaled_h > self._content_h:
                scale = self._content_h / block.total_height_pts
                scaled_h = self._content_h

            scaled_w = block.source_width_pts * scale

            # Start a new page if this block won't fit on the remaining space
            if current_y + scaled_h > self._page_h - self._margin:
                page = self._new_page(doc)
                current_y = float(self._margin)

            # Place the block image — zero gap after previous block
            rect = fitz.Rect(
                self._margin,
                current_y,
                self._margin + scaled_w,
                current_y + scaled_h,
            )
            page.insert_image(rect, stream=block.png_bytes)

            # Advance y pointer with no extra spacing
            current_y += scaled_h

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        page_count = len(doc)
        doc.close()
        return page_count

    def _new_page(self, doc: fitz.Document) -> fitz.Page:
        """Add and return a new blank page with the configured dimensions."""
        return doc.new_page(width=self._page_w, height=self._page_h)
