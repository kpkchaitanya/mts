"""
comparator.py

Compare an output PDF against a golden sample PDF and emit a defects
report (JSON + per-page diff images). The comparison is purely visual
 (pixel-based) to ensure fidelity of the compacted output.

The module intentionally avoids OCR/text comparisons to remain robust
across fonts and small rendering differences; it uses a configurable
pixel-diff threshold and page-level ratio thresholds to classify defects.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from PIL import Image
import numpy as np
import fitz

from src.config import (
    COMPARATOR_RENDER_DPI,
    DIFF_PIXEL_THRESHOLD,
    DIFF_PAGE_RATIO_THRESHOLD,
    BLANK_BAND_FRACTION_THRESHOLD,
    ARTIFACTS_BASE_PATH,
    FEATURE_NAME,
)


def _render_page_to_pil(doc: fitz.Document, page_idx: int, dpi: int) -> Image.Image:
    page = doc[page_idx]
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    data = pix.tobytes("png")
    return Image.open(io.BytesIO(data)).convert("L")  # grayscale


def _compute_diff(img_a: Image.Image, img_b: Image.Image) -> tuple[np.ndarray, float]:
    # Resize to same dimensions if needed (use smaller as target to avoid upscaling)
    if img_a.size != img_b.size:
        target = img_a if (img_a.size[0] * img_a.size[1]) <= (img_b.size[0] * img_b.size[1]) else img_b
        img_a = img_a.resize(target.size, resample=Image.LANCZOS)
        img_b = img_b.resize(target.size, resample=Image.LANCZOS)

    a = np.asarray(img_a, dtype=np.int16)
    b = np.asarray(img_b, dtype=np.int16)
    diff = np.abs(a - b).astype(np.uint8)
    # Count pixels above per-pixel threshold
    changed = (diff > DIFF_PIXEL_THRESHOLD)
    ratio = float(changed.sum()) / float(changed.size)
    return diff, ratio


def _detect_blank_band(img: Image.Image) -> float:
    """Return the fraction (0..1) of the page height that is the largest
    continuous run of near-white rows at the bottom of the image.
    """
    arr = np.asarray(img, dtype=np.uint8)
    h = arr.shape[0]
    # Row is near-white if median >= 250 (very conservative)
    row_meds = np.median(arr, axis=1)
    white = row_meds >= 250
    # find longest consecutive True run
    max_run = 0
    cur = 0
    for v in white:
        if v:
            cur += 1
            if cur > max_run:
                max_run = cur
        else:
            cur = 0
    return float(max_run) / float(h)


def compare_pdfs(
    golden_pdf: Path,
    output_pdf: Path,
    report_dir: Path | None = None,
    dpi: int = COMPARATOR_RENDER_DPI,
) -> dict[str, Any]:
    """
    Compare `output_pdf` to `golden_pdf` and write a defects report to
    `report_dir` (created if necessary). Returns a summary dict.
    """
    report_dir = Path(report_dir) if report_dir is not None else Path(ARTIFACTS_BASE_PATH) / FEATURE_NAME / "comparisons"
    report_dir.mkdir(parents=True, exist_ok=True)

    doc_g = fitz.open(str(golden_pdf))
    doc_o = fitz.open(str(output_pdf))

    pages_g = len(doc_g)
    pages_o = len(doc_o)

    defects: list[dict[str, Any]] = []

    if pages_g != pages_o:
        defects.append({"type": "page_count_mismatch", "golden_pages": pages_g, "output_pages": pages_o})

    pages = min(pages_g, pages_o)
    for i in range(pages):
        img_g = _render_page_to_pil(doc_g, i, dpi)
        img_o = _render_page_to_pil(doc_o, i, dpi)

        diff_arr, ratio = _compute_diff(img_g, img_o)
        page_defects: dict[str, Any] = {"page": i + 1, "diff_ratio": ratio}

        if ratio > DIFF_PAGE_RATIO_THRESHOLD:
            # Save diff visualization
            diff_vis = Image.fromarray(diff_arr).convert("L")
            diff_path = report_dir / f"page_{i+1:03d}_diff.png"
            diff_vis.save(diff_path)
            page_defects["type"] = "visual_diff"
            page_defects["diff_image"] = str(diff_path)
            defects.append(page_defects)
            continue

        # check for large blank bands in the output (indicates wasted space)
        blank_frac = _detect_blank_band(img_o)
        if blank_frac >= BLANK_BAND_FRACTION_THRESHOLD:
            page_defects["type"] = "large_blank_band"
            page_defects["blank_band_fraction"] = blank_frac
            defects.append(page_defects)

    # If output has extra pages beyond golden, flag them
    if pages_o > pages_g:
        for i in range(pages_g, pages_o):
            img_o = _render_page_to_pil(doc_o, i, dpi)
            blank_frac = _detect_blank_band(img_o)
            defects.append({"page": i + 1, "type": "extra_output_page", "blank_band_fraction": blank_frac})

    summary = {
        "golden_pages": pages_g,
        "output_pages": pages_o,
        "defect_count": len(defects),
        "defects": defects,
    }

    # write JSON report
    report_path = report_dir / "comparison_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    doc_g.close()
    doc_o.close()
    return summary
