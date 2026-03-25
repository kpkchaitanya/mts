"""
pdf_packer.py

Assembles extracted question block images into a compact output PDF.

Layout rules:
  - Blocks are placed sequentially top-to-bottom with ZERO vertical gap.
  - Supports 1-column and 2-column layouts.
  - All blocks are scaled to fit the column width (preserving aspect ratio).
  - Blocks are never upscaled beyond their natural 1:1 size.
  - When a block won't fit on the remaining space of the current column,
    a gap-fill attempt is made before advancing to the next column/page.
  - Gap-fill: if the leftover gap is large enough AND the next block can be
    pulled in by downscaling all blocks in the current column by at most
    MAX_SCALE_REDUCTION of base_scale, the column is re-laid-out with the
    extra block included.
  - Blocks taller than max_block_pages columns are force-fit by downscaling.
  - A two-phase approach (compute layout, then render) keeps the logic clean.

Output: a PDF file at output_path; returns the number of pages written.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from src.compact_source.block_extractor import ExtractedBlock
from src.config import (
    COLUMN_GAP_PTS,
    GAP_THRESHOLD_PTS,
    MAX_SCALE_REDUCTION,
    OUTPUT_PAGE_HEIGHT_PTS,
    OUTPUT_PAGE_MARGIN_PTS,
    OUTPUT_PAGE_WIDTH_PTS,
)


# ─── Layout Data Classes ───────────────────────────────────────────────────────


@dataclass
class _PlacedBlock:
    """A single block with its computed position and scale for rendering."""

    block: ExtractedBlock
    page_index: int        # Zero-based output page index
    x: float               # Left edge of image rect (PDF points)
    y: float               # Top edge of image rect (PDF points)
    w: float               # Rendered width (PDF points)
    h: float               # Rendered height (PDF points)
    effective_scale: float # Scale factor applied to this block


# ─── Packer ───────────────────────────────────────────────────────────────────


class PdfPacker:
    """
    Packs extracted question block images into a compact output PDF.

    Each block is placed as a PNG image inserted into a PyMuPDF page.
    No text is re-rendered — all visual content is carried directly from
    the cropped source images.

    Two-phase process:
      Phase 1 — compute_layout: assign blocks to columns/pages, compute scales
      Phase 2 — render: insert images at computed positions into a fitz.Document
    """

    def __init__(
        self,
        page_width: float = OUTPUT_PAGE_WIDTH_PTS,
        page_height: float = OUTPUT_PAGE_HEIGHT_PTS,
        margin: float = OUTPUT_PAGE_MARGIN_PTS,
        scale_factor: float = 100.0,
        max_pages: Optional[int] = None,
        columns: int = 1,
        max_block_pages: int = 2,
        layout_log_path: Optional[Path] = None,
    ) -> None:
        self._page_w = page_width
        self._page_h = page_height
        self._margin = margin
        self._columns = max(1, int(columns))
        self._max_block_pages = max(1, int(max_block_pages))
        self._layout_log_path = Path(layout_log_path) if layout_log_path is not None else None

        # Content area dimensions
        self._content_w = page_width - 2 * margin
        self._content_h = page_height - 2 * margin

        # Column width accounts for the gap between columns
        if self._columns == 2:
            self._col_w = (self._content_w - COLUMN_GAP_PTS) / 2.0
        else:
            self._col_w = self._content_w

        self._col_h = self._content_h  # Same as content height

        # Compute base_scale (as a fraction, not %)
        # scale_factor is in % (100 = natural fit width), max_pages is optional
        sf_frac = max(0.01, float(scale_factor) / 100.0)

        if max_pages is not None and max_pages > 0:
            # Will be computed after we know total block heights — store for later
            self._max_pages = int(max_pages)
        else:
            self._max_pages = None

        # Store raw scale_factor fraction for use in _compute_base_scale
        self._sf_frac = sf_frac

    # ── Public API ────────────────────────────────────────────────────────────

    def pack(self, blocks: list[ExtractedBlock], output_path: Path) -> int:
        """
        Pack all block images into a PDF file at output_path.

        Args:
            blocks: Extracted question blocks in document order.
            output_path: Destination path for the output PDF.

        Returns:
            Total number of pages in the output PDF.
        """
        if not blocks:
            doc = fitz.open()
            doc.new_page(width=self._page_w, height=self._page_h)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
            doc.close()
            return 1

        # Phase 1: Compute layout
        layout = self._compute_layout(blocks)

        # Phase 2: Render
        page_count = self._render(layout, blocks, output_path)
        return page_count

    # ── Phase 1: Layout Computation ───────────────────────────────────────────

    def _compute_layout(self, blocks: list[ExtractedBlock]) -> list[_PlacedBlock]:
        """
        Compute the position, scale, and page assignment for every block.

        Returns a flat list of _PlacedBlock in document order.
        """
        base_scale = self._compute_base_scale(blocks)

        # X-coordinate of each column's left edge
        col_x: list[float] = [self._margin]
        if self._columns == 2:
            col_x.append(self._margin + self._col_w + COLUMN_GAP_PTS)

        placed: list[_PlacedBlock] = []

        current_col = 0
        current_page = 0
        col_y = self._margin         # Current y position in the active column
        col_blocks: list[_PlacedBlock] = []  # Blocks placed in the current column

        block_idx = 0
        n = len(blocks)

        while block_idx < n:
            block = blocks[block_idx]

            # Per-block natural scale: fills column width, never upscale
            natural_scale = self._col_w / block.source_width_pts
            natural_scale = min(natural_scale, 1.0)

            # Effective scale for this block
            eff_scale = min(base_scale, natural_scale)

            # Safety cap: block taller than max_block_pages columns → force fit
            max_allowed_h = self._col_h * self._max_block_pages
            scaled_h = block.total_height_pts * eff_scale
            if scaled_h > max_allowed_h:
                eff_scale = max_allowed_h / block.total_height_pts
                scaled_h = block.total_height_pts * eff_scale

            scaled_w = block.source_width_pts * eff_scale

            col_bottom = self._margin + self._col_h

            # Check if block fits in remaining column space
            if col_y + scaled_h > col_bottom:
                # Try gap-fill by pulling in one or more next blocks
                gap_fill_result = self._try_gap_fill_multi(
                    col_blocks, blocks, block_idx, base_scale, col_x[current_col]
                )

                if gap_fill_result is not None:
                    # gap_fill_result: (new_col_blocks, consumed_count)
                    new_col_blocks, consumed = gap_fill_result
                    # Replace the col_blocks entries in placed[] with re-scaled versions
                    n_col = len(col_blocks)
                    del placed[-n_col:]
                    col_blocks = new_col_blocks
                    placed.extend(col_blocks)
                    col_y = col_blocks[-1].y + col_blocks[-1].h
                    block_idx += consumed
                    # Advance to next column/page after filling this one
                    current_col, current_page = self._advance_column(
                        current_col, current_page
                    )
                    col_y = self._margin
                    col_blocks = []
                    continue

                # If gap-fill failed, try shrinking the current column uniformly
                shrink_result = self._try_shrink_column(col_blocks, base_scale, col_x[current_col])
                if shrink_result is not None:
                    # Replace placed entries with shrunk column and advance
                    n_col = len(col_blocks)
                    del placed[-n_col:]
                    col_blocks = shrink_result
                    placed.extend(col_blocks)
                    # Column now considered full; move to next column/page
                    current_col, current_page = self._advance_column(
                        current_col, current_page
                    )
                    col_y = self._margin
                    col_blocks = []
                    continue

                # Gap-fill declined and shrink not possible — advance column/page
                current_col, current_page = self._advance_column(
                    current_col, current_page
                )
                col_y = self._margin
                col_blocks = []
                # Re-compute (same block_idx, new column)
                continue

            # Place the block
            pb = _PlacedBlock(
                block=block,
                page_index=current_page,
                x=col_x[current_col],
                y=col_y,
                w=scaled_w,
                h=scaled_h,
                effective_scale=eff_scale,
            )
            placed.append(pb)
            col_blocks.append(pb)
            col_y += scaled_h
            block_idx += 1

        # After all blocks: run gap-fill on the final column too (best-effort)
        # (No next block — just leave the gap as-is; this is already as tight
        # as we can make it without pulling phantom content.)

        return placed

    def _compute_base_scale(self, blocks: list[ExtractedBlock]) -> float:
        """
        Compute the base scale fraction to apply to all blocks.

        If max_pages is given, auto-scale so all blocks fit in the target page count.
        If scale_factor is also given, take the minimum.
        Never upscales (capped at 1.0).
        """
        sf = self._sf_frac  # user-provided scale_factor as fraction

        if self._max_pages is not None:
            total_height = sum(b.total_height_pts for b in blocks)
            target_content = self._max_pages * self._col_h * self._columns
            if total_height > 0:
                auto_scale = target_content / total_height
            else:
                auto_scale = 1.0
            auto_scale = min(auto_scale, 1.0)  # never upscale
            return min(sf, auto_scale)

        return min(sf, 1.0)

    def _advance_column(self, current_col: int, current_page: int) -> tuple[int, int]:
        """
        Move to the next column. If we've exhausted all columns on the current
        page, increment the page counter and reset to column 0.

        Returns (new_col, new_page).
        """
        next_col = current_col + 1
        if next_col >= self._columns:
            return 0, current_page + 1
        return next_col, current_page

    def _try_gap_fill(
        self,
        col_blocks: list[_PlacedBlock],
        next_block: ExtractedBlock,
        base_scale: float,
        col_x: float,
    ) -> Optional[list[_PlacedBlock]]:
        """
        Attempt to pull next_block into the current column by uniformly downscaling
        all blocks (col_blocks + next_block) to fit within the column height.

        Returns a new list of _PlacedBlock (for the whole column including next_block)
        if the needed scale is within MAX_SCALE_REDUCTION of base_scale.
        Returns None if the gap is small (not worth filling) or the scale reduction
        would be too large.
        """
        if not col_blocks:
            return None

        # Current fill level: where does the column end?
        last = col_blocks[-1]
        col_y_end = last.y + last.h

        # Gap remaining in this column
        col_bottom = self._margin + self._col_h
        gap = col_bottom - col_y_end

        # Only worth gap-filling if the gap is meaningful
        if gap <= GAP_THRESHOLD_PTS:
            return None

        # Compute natural heights of existing col_blocks + next_block
        sum_natural_h = sum(pb.block.total_height_pts for pb in col_blocks)
        next_natural_h = next_block.total_height_pts

        total_natural_h = sum_natural_h + next_natural_h
        if total_natural_h <= 0:
            return None

        # Scale needed so all blocks fit exactly in the column
        needed_scale = self._col_h / total_natural_h

        # Clamp to never upscale
        needed_scale = min(needed_scale, 1.0)

        # Also respect per-block natural scale caps
        # (each block must not exceed its natural fit width)
        for pb in col_blocks:
            nat = min(self._col_w / pb.block.source_width_pts, 1.0)
            needed_scale = min(needed_scale, nat)
        next_nat = min(self._col_w / next_block.source_width_pts, 1.0)
        needed_scale = min(needed_scale, next_nat)

        # Min allowed scale: base_scale reduced by at most MAX_SCALE_REDUCTION
        min_allowed = base_scale * (1.0 - MAX_SCALE_REDUCTION)

        if needed_scale < min_allowed:
            return None  # Would shrink too much — accept the gap

        # Re-lay the column with needed_scale
        new_col_blocks: list[_PlacedBlock] = []
        y = self._margin
        for pb in col_blocks:
            nat = min(self._col_w / pb.block.source_width_pts, 1.0)
            eff = min(needed_scale, nat)
            h = pb.block.total_height_pts * eff
            w = pb.block.source_width_pts * eff
            new_col_blocks.append(_PlacedBlock(
                block=pb.block,
                page_index=pb.page_index,
                x=col_x,
                y=y,
                w=w,
                h=h,
                effective_scale=eff,
            ))
            y += h

        # Add next_block
        nat_next = min(self._col_w / next_block.source_width_pts, 1.0)
        eff_next = min(needed_scale, nat_next)
        h_next = next_block.total_height_pts * eff_next
        w_next = next_block.source_width_pts * eff_next
        new_col_blocks.append(_PlacedBlock(
            block=next_block,
            page_index=col_blocks[0].page_index,  # same page as the rest of the column
            x=col_x,
            y=y,
            w=w_next,
            h=h_next,
            effective_scale=eff_next,
        ))

        return new_col_blocks

    def _try_gap_fill_multi(
        self,
        col_blocks: list[_PlacedBlock],
        blocks: list[ExtractedBlock],
        start_idx: int,
        base_scale: float,
        col_x: float,
        max_lookahead: int = 5,
    ) -> Optional[tuple[list[_PlacedBlock], int]]:
        """
        Attempt to pull in multiple next blocks (up to max_lookahead) into the
        current column by uniformly downscaling all blocks (existing + pulled)
        to fit within the column height. Returns (new_col_blocks, consumed_count)
        on success, otherwise None.
        """
        if not col_blocks or start_idx >= len(blocks):
            return None

        # Current natural heights of existing column blocks
        sum_natural_h = sum(pb.block.total_height_pts for pb in col_blocks)

        consumed = 0
        candidates: list[ExtractedBlock] = []

        for look in range(max_lookahead):
            idx = start_idx + look
            if idx >= len(blocks):
                break
            candidates.append(blocks[idx])
            consumed = len(candidates)

            total_natural_h = sum_natural_h + sum(b.total_height_pts for b in candidates)
            if total_natural_h <= 0:
                continue

            needed_scale = self._col_h / total_natural_h
            needed_scale = min(needed_scale, 1.0)

            # Respect per-block natural width caps
            for pb in col_blocks:
                nat = min(self._col_w / pb.block.source_width_pts, 1.0)
                needed_scale = min(needed_scale, nat)
            for b in candidates:
                nat_b = min(self._col_w / b.source_width_pts, 1.0)
                needed_scale = min(needed_scale, nat_b)

            min_allowed = base_scale * (1.0 - MAX_SCALE_REDUCTION)
            if needed_scale < min_allowed:
                # Try adding more blocks might worsen needed_scale; continue
                continue

            # Good: re-lay column with needed_scale including candidates
            new_col_blocks: list[_PlacedBlock] = []
            y = self._margin
            for pb in col_blocks:
                nat = min(self._col_w / pb.block.source_width_pts, 1.0)
                eff = min(needed_scale, nat)
                h = pb.block.total_height_pts * eff
                w = pb.block.source_width_pts * eff
                new_col_blocks.append(_PlacedBlock(
                    block=pb.block,
                    page_index=pb.page_index,
                    x=col_x,
                    y=y,
                    w=w,
                    h=h,
                    effective_scale=eff,
                ))
                y += h

            # Add candidate blocks
            for b in candidates:
                nat_b = min(self._col_w / b.source_width_pts, 1.0)
                eff_b = min(needed_scale, nat_b)
                h_b = b.total_height_pts * eff_b
                w_b = b.source_width_pts * eff_b
                new_col_blocks.append(_PlacedBlock(
                    block=b,
                    page_index=col_blocks[0].page_index,
                    x=col_x,
                    y=y,
                    w=w_b,
                    h=h_b,
                    effective_scale=eff_b,
                ))
                y += h_b

            return new_col_blocks, consumed

        return None

    def _try_shrink_column(
        self,
        col_blocks: list[_PlacedBlock],
        base_scale: float,
        col_x: float,
    ) -> Optional[list[_PlacedBlock]]:
        """
        Attempt to uniformly downscale all blocks already placed in the current
        column so that they exactly fill the column height. Returns new column
        blocks on success, otherwise None.
        """
        if not col_blocks:
            return None

        sum_natural_h = sum(pb.block.total_height_pts for pb in col_blocks)
        if sum_natural_h <= 0:
            return None

        needed_scale = self._col_h / sum_natural_h
        needed_scale = min(needed_scale, 1.0)

        # Respect per-block natural width caps
        for pb in col_blocks:
            nat = min(self._col_w / pb.block.source_width_pts, 1.0)
            needed_scale = min(needed_scale, nat)

        min_allowed = base_scale * (1.0 - MAX_SCALE_REDUCTION)
        if needed_scale < min_allowed:
            return None

        # Re-lay the column with needed_scale
        new_col_blocks: list[_PlacedBlock] = []
        y = self._margin
        for pb in col_blocks:
            nat = min(self._col_w / pb.block.source_width_pts, 1.0)
            eff = min(needed_scale, nat)
            h = pb.block.total_height_pts * eff
            w = pb.block.source_width_pts * eff
            new_col_blocks.append(_PlacedBlock(
                block=pb.block,
                page_index=pb.page_index,
                x=col_x,
                y=y,
                w=w,
                h=h,
                effective_scale=eff,
            ))
            y += h

        return new_col_blocks

    # ── Phase 2: Rendering ────────────────────────────────────────────────────

    def _render(
        self,
        layout: list[_PlacedBlock],
        blocks: list[ExtractedBlock],
        output_path: Path,
    ) -> int:
        """
        Render all placed blocks into a fitz.Document and save to output_path.

        Returns the total number of pages written.
        """
        if not layout:
            return 0

        num_pages = max(pb.page_index for pb in layout) + 1

        doc = fitz.open()
        for _ in range(num_pages):
            doc.new_page(width=self._page_w, height=self._page_h)

        for pb in layout:
            # Look up the page by index each time — PyMuPDF invalidates cached
            # page references when new pages are added to the document.
            page = doc[pb.page_index]
            rect = fitz.Rect(pb.x, pb.y, pb.x + pb.w, pb.y + pb.h)
            page.insert_image(rect, stream=pb.block.png_bytes)

        if self._layout_log_path:
            self._write_layout_log(layout)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        page_count = len(doc)
        doc.close()
        return page_count

    def _write_layout_log(self, layout: list[_PlacedBlock]) -> None:
        """Write a CSV layout log for debugging block placements."""
        self._layout_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._layout_log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "block", "output_page", "x0", "y0", "x1", "y1",
                "scaled_w", "scaled_h", "effective_scale",
            ])
            for pb in layout:
                writer.writerow([
                    pb.block.question_number,
                    pb.page_index,
                    f"{pb.x:.1f}",
                    f"{pb.y:.1f}",
                    f"{pb.x + pb.w:.1f}",
                    f"{pb.y + pb.h:.1f}",
                    f"{pb.w:.1f}",
                    f"{pb.h:.1f}",
                    f"{pb.effective_scale:.4f}",
                ])
