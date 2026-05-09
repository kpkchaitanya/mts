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


_SEVERITY_CRITICAL = "Critical"
_SEVERITY_HIGH     = "High"
_SEVERITY_MEDIUM   = "Medium"
_SEVERITY_LOW      = "Low"

_PRIORITY_P1 = "P1"
_PRIORITY_P2 = "P2"
_PRIORITY_P3 = "P3"
_PRIORITY_P4 = "P4"


def _classify_visual_diff(ratio: float) -> tuple[str, str, str]:
    """Return (severity, priority, description) for a visual_diff defect."""
    pct = round(ratio * 100, 1)
    if ratio >= 0.20:
        return (
            _SEVERITY_CRITICAL, _PRIORITY_P1,
            f"Severe layout deviation on this page — {pct}% of pixels differ from the golden sample. "
            "Content may be shifted, clipped, or missing entirely.",
        )
    if ratio >= 0.10:
        return (
            _SEVERITY_HIGH, _PRIORITY_P2,
            f"Significant visual difference on this page — {pct}% of pixels differ. "
            "Question blocks, spacing, or images likely misaligned relative to the golden.",
        )
    if ratio >= 0.05:
        return (
            _SEVERITY_MEDIUM, _PRIORITY_P3,
            f"Moderate visual difference on this page — {pct}% of pixels differ. "
            "Minor layout shift or scaling variance detected.",
        )
    return (
        _SEVERITY_LOW, _PRIORITY_P4,
        f"Minor visual difference on this page — {pct}% of pixels differ. "
        "Likely a sub-pixel rendering or anti-aliasing artefact.",
    )


def _build_defect(
    defect_id: str,
    defect_type: str,
    page: int | None,
    severity: str,
    priority: str,
    description: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": defect_id,
        "type": defect_type,
        "severity": severity,
        "priority": priority,
        "description": description,
    }
    if page is not None:
        d["page"] = page
    if extras:
        d.update(extras)
    return d


def _write_markdown_report(
    report_dir: Path,
    golden_pdf: Path,
    output_pdf: Path,
    pages_g: int,
    pages_o: int,
    defects: list[dict[str, Any]],
) -> None:
    """Write a Jira-style markdown defect table to defects.md."""
    lines: list[str] = []
    lines.append(f"# Defect Report — {output_pdf.stem}")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| **Golden** | `{golden_pdf.name}` ({pages_g} pages) |")
    lines.append(f"| **Output** | `{output_pdf.name}` ({pages_o} pages) |")
    lines.append(f"| **Total defects** | {len(defects)} |")
    lines.append("")

    if not defects:
        lines.append("✅ No defects found.")
    else:
        lines.append("| ID | Page | Type | Severity | Priority | Description |")
        lines.append("|---|---|---|---|---|---|")
        for d in defects:
            page_str = str(d.get("page", "—"))
            lines.append(
                f"| {d['id']} "
                f"| {page_str} "
                f"| `{d['type']}` "
                f"| **{d['severity']}** "
                f"| {d['priority']} "
                f"| {d['description']} |"
            )

        # Diff images section
        vis_defects = [d for d in defects if d.get("diff_image")]
        if vis_defects:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## Diff Images")
            lines.append("")
            for d in vis_defects:
                img_path = Path(d["diff_image"])
                rel = img_path.name
                lines.append(f"### {d['id']} — Page {d['page']} ({d['severity']} / {d['priority']})")
                lines.append("")
                lines.append(f"_{d['description']}_")
                lines.append("")
                lines.append(f"![{rel}]({rel})")
                lines.append("")

    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "defects.md").write_text("\n".join(lines), encoding="utf-8")


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
    seq = 0

    def _next_id() -> str:
        nonlocal seq
        seq += 1
        return f"DEF-{seq:03d}"

    if pages_g != pages_o:
        delta = pages_o - pages_g
        direction = "more" if delta > 0 else "fewer"
        defects.append(_build_defect(
            defect_id=_next_id(),
            defect_type="page_count_mismatch",
            page=None,
            severity=_SEVERITY_HIGH,
            priority=_PRIORITY_P2,
            description=(
                f"Output has {abs(delta)} {direction} page(s) than the golden sample "
                f"({pages_o} vs {pages_g}). This indicates blocks were split differently "
                "or extra/missing content pages were produced."
            ),
            extras={"golden_pages": pages_g, "output_pages": pages_o},
        ))

    pages = min(pages_g, pages_o)
    for i in range(pages):
        img_g = _render_page_to_pil(doc_g, i, dpi)
        img_o = _render_page_to_pil(doc_o, i, dpi)

        diff_arr, ratio = _compute_diff(img_g, img_o)

        if ratio > DIFF_PAGE_RATIO_THRESHOLD:
            diff_vis = Image.fromarray(diff_arr).convert("L")
            diff_path = report_dir / f"page_{i+1:03d}_diff.png"
            diff_vis.save(diff_path)
            severity, priority, description = _classify_visual_diff(ratio)
            defects.append(_build_defect(
                defect_id=_next_id(),
                defect_type="visual_diff",
                page=i + 1,
                severity=severity,
                priority=priority,
                description=description,
                extras={"diff_ratio": ratio, "diff_image": str(diff_path)},
            ))
            continue

        blank_frac = _detect_blank_band(img_o)
        if blank_frac >= BLANK_BAND_FRACTION_THRESHOLD:
            defects.append(_build_defect(
                defect_id=_next_id(),
                defect_type="large_blank_band",
                page=i + 1,
                severity=_SEVERITY_MEDIUM,
                priority=_PRIORITY_P3,
                description=(
                    f"Output page has a large blank band occupying {round(blank_frac * 100, 1)}% "
                    "of the page height. Indicates inefficient packing or a missed block."
                ),
                extras={"blank_band_fraction": blank_frac},
            ))

    if pages_o > pages_g:
        for i in range(pages_g, pages_o):
            img_o = _render_page_to_pil(doc_o, i, dpi)
            blank_frac = _detect_blank_band(img_o)
            is_blank = blank_frac >= 0.95
            defects.append(_build_defect(
                defect_id=_next_id(),
                defect_type="extra_output_page",
                page=i + 1,
                severity=_SEVERITY_HIGH,
                priority=_PRIORITY_P2,
                description=(
                    f"Output contains an extra page (page {i+1}) not present in the golden sample. "
                    + ("Page appears to be entirely blank — likely a packing overflow." if is_blank
                       else f"Page is {round(blank_frac * 100, 1)}% blank — partial overflow or orphaned block.")
                ),
                extras={"blank_band_fraction": blank_frac},
            ))

    summary = {
        "golden_pages": pages_g,
        "output_pages": pages_o,
        "defect_count": len(defects),
        "defects": defects,
    }

    report_path = report_dir / "comparison_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    _write_markdown_report(report_dir, golden_pdf, output_pdf, pages_g, pages_o, defects)

    doc_g.close()
    doc_o.close()
    return summary
