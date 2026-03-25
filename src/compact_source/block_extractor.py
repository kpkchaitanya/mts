"""
block_extractor.py

Crops each question block from the source PDF's rendered page images.

For each QuestionBlock produced by BlockDetector, this module:
  1. Renders the relevant page(s) at the configured DPI using PyMuPDF
  2. Crops the exact rectangular region for each PageSlice
  3. Combines multi-slice blocks (cross-page questions) into one image

The crop is done directly from the original PDF rendering — no text is
re-interpreted or re-rendered. The output is pixel-faithful to the source.

Output: list of ExtractedBlock objects, one per QuestionBlock.
"""

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from src.compact_source.block_detector import QuestionBlock, PageSlice
from src.config import PDF_RENDER_DPI


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class ExtractedBlock:
    """
    A question block as a single PNG image, ready for packing into the output PDF.

    Attributes:
        question_number: The question's number from the source PDF.
        png_bytes: PNG-encoded bytes of the complete block image.
        source_width_pts: Block width in PDF points (pre-DPI, used for scaling).
        total_height_pts: Block height in PDF points (pre-DPI, used for scaling).
    """

    question_number: int
    png_bytes: bytes
    source_width_pts: float
    total_height_pts: float


# ─── Extractor ────────────────────────────────────────────────────────────────


class BlockExtractor:
    """
    Crops question block regions from a PDF and returns them as PNG images.

    PyMuPDF renders each page at the configured DPI. The exact bounding box
    for each question block is cropped using a clip rect derived from the
    pdfplumber y-coordinates in PageSlice.

    Coordinate alignment:
        pdfplumber's 'top' field and PyMuPDF clip rects both use PDF points
        measured from the top of the page — no coordinate conversion needed.
    """

    def __init__(self, dpi: int = PDF_RENDER_DPI) -> None:
        self._dpi = dpi

    def extract(self, pdf_path: Path, blocks: list[QuestionBlock]) -> list[ExtractedBlock]:
        """
        Extract all question blocks from the source PDF as PNG images.

        Opens the PDF once and processes all blocks in document order to
        avoid repeated open/close cycles.

        Args:
            pdf_path: Path to the source worksheet PDF.
            blocks: Ordered list of QuestionBlocks from BlockDetector.

        Returns:
            List of ExtractedBlock objects in the same order as blocks.
        """
        doc = fitz.open(str(pdf_path))
        zoom = self._dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        extracted: list[ExtractedBlock] = []
        for block in blocks:
            slice_pixmaps = [
                self._crop_slice(doc, s, matrix) for s in block.slices
            ]
            png_bytes, width_pts, height_pts = self._combine_slices(
                slice_pixmaps, block.slices
            )
            extracted.append(ExtractedBlock(
                question_number=block.question_number,
                png_bytes=png_bytes,
                source_width_pts=width_pts,
                total_height_pts=height_pts,
            ))

        doc.close()
        return extracted

    # ── Cropping ──────────────────────────────────────────────────────────────

    def _crop_slice(
        self,
        doc: fitz.Document,
        page_slice: PageSlice,
        matrix: fitz.Matrix,
    ) -> fitz.Pixmap:
        """
        Render a clipped page region as a Pixmap at the configured DPI.

        The clip rect spans the full page width and the vertical range
        defined by the PageSlice.

        Args:
            doc: Open PyMuPDF document.
            page_slice: Slice defining the page and y-coordinate range.
            matrix: Zoom matrix for DPI scaling.

        Returns:
            Pixmap of the cropped region.
        """
        page = doc[page_slice.page_number]

        # Initial clip for the full slice region
        clip = fitz.Rect(
            0,                    # x_left: start at page left edge
            page_slice.y_top,
            page.rect.width,      # x_right: full page width
            page_slice.y_bottom,
        )

        pm = page.get_pixmap(matrix=matrix, clip=clip)

        # Detect and trim bottom-most blank rows (white/near-white) to
        # avoid leaving large empty areas or page footers when a question
        # continues on the next page. If blank rows are found, re-render
        # the clip with a tightened bottom boundary in PDF points.
        blank_rows = self._count_bottom_blank_rows(pm)
        if blank_rows <= 0:
            return pm

        # Compute trimmed height in PDF points and clamp
        trim_pts = (blank_rows * 72.0) / self._dpi
        new_y_bottom = max(page_slice.y_top, page_slice.y_bottom - trim_pts)
        if new_y_bottom >= page_slice.y_bottom:
            return pm

        tight_clip = fitz.Rect(0, page_slice.y_top, page.rect.width, new_y_bottom)
        return page.get_pixmap(matrix=matrix, clip=tight_clip)

    def _count_bottom_blank_rows(self, pixmap: fitz.Pixmap, threshold: int = 245, max_fraction: float = 0.5) -> int:
        """
        Count continuous blank (near-white) rows at the bottom of a pixmap.

        A row is considered blank if every pixel in the row has all RGB
        channels >= `threshold`. The function scans from the image bottom
        upward until a non-blank row is found or `max_fraction` of the
        image height is reached.
        """
        if pixmap is None or pixmap.width == 0 or pixmap.height == 0:
            return 0

        n = pixmap.n
        w = pixmap.width
        h = pixmap.height
        row_stride = w * n
        samples = pixmap.samples

        # Limit to a reasonable portion of the page to avoid trimming large
        # amounts by accident. Default max_fraction is conservative.
        max_rows = int(h * max_fraction)
        if max_rows <= 0:
            return 0

        blank_rows = 0
        for row in range(h - 1, h - 1 - max_rows, -1):
            start = row * row_stride
            end = start + row_stride
            row_bytes = samples[start:end]
            # Treat pixel as white if all color channels >= threshold
            is_blank = True
            # iterate per-pixel
            for px in range(0, len(row_bytes), n):
                # check RGB channels only (ignore alpha if present)
                if n >= 3:
                    r = row_bytes[px]
                    g = row_bytes[px + 1]
                    b = row_bytes[px + 2]
                else:
                    # grayscale
                    r = row_bytes[px]
                    g = r
                    b = r
                if r < threshold or g < threshold or b < threshold:
                    is_blank = False
                    break
            if is_blank:
                blank_rows += 1
            else:
                break

        return blank_rows

    # ── Combining ─────────────────────────────────────────────────────────────

    def _combine_slices(
        self,
        pixmaps: list[fitz.Pixmap],
        slices: list[PageSlice],
    ) -> tuple[bytes, float, float]:
        """
        Combine one or more slice pixmaps into a single PNG image.

        Single-slice blocks (the common case) are returned directly.
        Multi-slice blocks (cross-page questions) are stacked vertically
        using a temporary in-memory PDF — this preserves rendering fidelity
        without requiring external image libraries.

        Args:
            pixmaps: Rendered pixmaps for each PageSlice, in order.
            slices: Corresponding PageSlice objects (for point dimensions).

        Returns:
            Tuple of (png_bytes, source_width_pts, total_height_pts).
        """
        if len(pixmaps) == 1:
            pm = pixmaps[0]
            width_pts = pm.width * 72.0 / self._dpi
            # Derive height in PDF points from the rendered pixmap so any
            # trimming applied in _crop_slice is accurately reflected.
            height_pts = pm.height * 72.0 / self._dpi
            return pm.tobytes("png"), width_pts, height_pts

        # Multi-slice: stack vertically via a temporary in-memory PDF
        # Use the actual rendered pixmap heights (converted to PDF points)
        # to respect any per-slice trimming performed above.
        heights_pts = [pm.height * 72.0 / self._dpi for pm in pixmaps]
        total_height_pts = sum(heights_pts)
        width_pts = pixmaps[0].width * 72.0 / self._dpi

        tmp_doc = fitz.open()
        page = tmp_doc.new_page(width=width_pts, height=total_height_pts)

        y_pts = 0.0
        for pm, h_pts in zip(pixmaps, heights_pts):
            page.insert_image(fitz.Rect(0, y_pts, width_pts, y_pts + h_pts), pixmap=pm)
            y_pts += h_pts

        # Re-render the combined page at the configured DPI
        zoom = self._dpi / 72.0
        combined = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        tmp_doc.close()

        return combined.tobytes("png"), width_pts, total_height_pts
