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
from typing import Optional

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
        layout_log_path: Optional[Path] = None,
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
        # Optional path to write layout placements for debugging
        self._layout_log_path = Path(layout_log_path) if layout_log_path is not None else None
        # Small vertical padding (pts) inserted after each block to avoid
        # any rendering overlap due to image antialiasing or insert_image
        # edge effects. Default 1.0 pt keeps layout tight while preventing
        # inadvertent overlaps.
        self._vertical_padding = 1.0

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
        out_page_index = 0
        if self._layout_log_path:
            self._layout_log_path.parent.mkdir(parents=True, exist_ok=True)
            # start fresh for this run
            with open(self._layout_log_path, "w", encoding="utf-8") as f:
                f.write("block,output_page,x0,y0,x1,y1,scaled_w,scaled_h\n")

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
                out_page_index = len(doc) - 1

            # Place the block image — zero gap after previous block
            rect = fitz.Rect(
                self._margin,
                current_y,
                self._margin + scaled_w,
                current_y + scaled_h,
            )
            page.insert_image(rect, stream=block.png_bytes)
            # Write placement info for debugging if requested
            if self._layout_log_path:
                with open(self._layout_log_path, "a", encoding="utf-8") as f:
                    f.write(
                        f"{block.question_number},{out_page_index},{rect.x0:.1f},{rect.y0:.1f},{rect.x1:.1f},{rect.y1:.1f},{scaled_w:.1f},{scaled_h:.1f}\n"
                    )

            # Advance y pointer and add tiny vertical padding to prevent
            # pixel/antialias overlap between adjacent block images.
            current_y += scaled_h + self._vertical_padding

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        page_count = len(doc)
        doc.close()
        return page_count

    def _new_page(self, doc: fitz.Document) -> fitz.Page:
        """Add and return a new blank page with the configured dimensions."""
        return doc.new_page(width=self._page_w, height=self._page_h)
