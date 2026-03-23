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
        scale_factor: float = 100.0,
        max_block_pages: int = 2,
    ) -> None:
        self._page_w = page_width
        self._page_h = page_height
        self._margin = margin
        self._content_w = page_width - 2 * margin
        self._content_h = page_height - 2 * margin
        # scale_factor is a percentage (100 = original size)
        self._scale_factor = max(0.01, float(scale_factor) / 100.0)
        # Maximum number of output pages a single block may occupy before
        # forcing a downscale to make it fit. Must be >= 1.
        self._max_block_pages = max(1, int(max_block_pages))

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
            # Compute natural scale to fit the content width, but do not
            # upscale beyond the block's natural 1:1 size. We only allow
            # scaling down per user request.
            natural_scale = self._content_w / block.source_width_pts
            natural_scale = min(natural_scale, 1.0)

            # Apply global scale factor (user-configurable), but do not
            # upscale beyond the natural scale (scale down only).
            scale = natural_scale * self._scale_factor
            scale = min(scale, natural_scale)

            scaled_h = block.total_height_pts * scale

            # Allow blocks to occupy up to `_max_block_pages` of content height
            # before forcing a further downscale.
            max_allowed_h = self._content_h * self._max_block_pages
            if scaled_h > max_allowed_h:
                # Scale down so the block fits within the allowed pages.
                scale = max_allowed_h / block.total_height_pts
                scaled_h = block.total_height_pts * scale

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
