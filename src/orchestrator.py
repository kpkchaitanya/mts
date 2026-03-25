"""
orchestrator.py

Entry point for the MTS pipeline system.
Routes requests to the correct transformation mode and runs the full pipeline.

Usage (run from the project root):
    python -m src.orchestrator compact_source --pdf <path> --grade <n> --subject <subject>
    python -m src.orchestrator generate_worksheet --request <path>
"""

import argparse
import sys
from pathlib import Path

from src.compact_source.block_detector import (
    BlockDetector,
    BlockDetectionError,
    BlockDetectionResult,
)
from src.compact_source.block_extractor import BlockExtractor
from src.compact_source.pdf_packer import PdfPacker
from src.compact_source.reporter import Reporter
from src.compact_source.comparator import compare_pdfs
from src.utils.artifact_writer import ArtifactWriter
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import get_page_count


def run_compact_source(
    pdf_path: Path,
    grade: int,
    subject: str,
    scale_factor: float = None,
    max_pages: int = None,
    columns: int = 1,
    max_block_pages: int = None,
    problem_list: str | None = None,
    compare: bool = False,
    golden: Path | None = None,
) -> None:
    """
    Execute the full compact_source pipeline for a given source worksheet PDF.

    Pipeline steps:
    1. BlockDetector  — locate question blocks using pdfplumber y-coordinates
    2. BlockExtractor — crop each block region from the rendered source pages
    3. PdfPacker      — pack cropped block images into a compact output PDF
    4. Reporter       — validate integrity, write source-boundary-map.md
                        and compaction-report.md

    No text is re-rendered at any step. All content is carried as cropped
    images from the original PDF, preserving math symbols, graphs, and
    diagrams exactly as they appear in the source.

    Args:
        pdf_path: Path to the input source worksheet PDF.
        grade: Grade level.
        subject: Subject area (e.g., "Math").

    Raises:
        FileNotFoundError: If the PDF does not exist at pdf_path.
        BlockDetectionError: If question boundaries cannot be detected.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: '{pdf_path}'. "
            "Check the file path and try again."
        )

    from src.config import BLOCK_SCALE_FACTOR, DEFAULT_MAX_BLOCK_PAGES

    if scale_factor is None:
        scale_factor = BLOCK_SCALE_FACTOR

    if max_block_pages is None:
        max_block_pages = DEFAULT_MAX_BLOCK_PAGES

    print(f"\n[MTS] compact_source — {pdf_path.name}")
    print(
        f"[MTS] Grade: {grade} | Subject: {subject} | Scale: {scale_factor}% | "
        f"Columns: {columns}"
        + (f" | Max pages: {max_pages}" if max_pages is not None else "")
    )

    claude_client = ClaudeClient()
    artifact_writer = ArtifactWriter()
    source_filename = pdf_path.name

    print(f"[MTS] Run ID: {artifact_writer.run_id}")
    print(f"[MTS] Artifacts: {artifact_writer.run_path}\n")

    original_page_count = get_page_count(pdf_path)
    print(f"[MTS] Source: {original_page_count} pages")

    # ── Step 1: Detect question blocks ───────────────────────────────────────
    print("[1/3] Detecting question blocks...")
    detector = BlockDetector(claude_client)
    detection_result = detector.detect(pdf_path)
    # Apply problem list filter (e.g., ALL, "1-10", "1,3,5")
    def _parse_problem_list(plist: str | None):
        if not plist:
            return None
        s = plist.strip()
        if s.upper() == "ALL":
            return None
        nums: set[int] = set()
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                nums.update(range(int(a), int(b) + 1))
            else:
                nums.add(int(part))
        return nums

    selected = _parse_problem_list(problem_list)
    if selected is not None:
        filtered_blocks = [b for b in detection_result.blocks if b.question_number in selected]
    else:
        filtered_blocks = detection_result.blocks
    # Build a replacement detection_result for reporting using filtered blocks
    detection_result = BlockDetectionResult(
        blocks=filtered_blocks,
        total_questions=len(filtered_blocks),
        page_heights=detection_result.page_heights,
        page_widths=detection_result.page_widths,
        used_vision_fallback=detection_result.used_vision_fallback,
    )
    print(
        f"      {detection_result.total_questions} question blocks detected"
        + (" (vision fallback used)" if detection_result.used_vision_fallback else "")
    )

    # ── Step 2: Extract block images ─────────────────────────────────────────
    print("[2/3] Extracting question block images...")
    extractor = BlockExtractor()
    extracted_blocks = extractor.extract(pdf_path, detection_result.blocks)
    print(f"      {len(extracted_blocks)} block images extracted")

    # ── Step 3: Pack into output PDF ──────────────────────────────────────────
    print("[3/3] Packing blocks into output PDF...")
    # Enable layout logging into the run artifacts to debug overlaps
    layout_log_path = artifact_writer.run_path / "pack_layouts.csv"
    packer = PdfPacker(
        scale_factor=scale_factor,
        max_pages=max_pages,
        columns=columns,
        max_block_pages=max_block_pages,
        layout_log_path=layout_log_path,
    )
    output_pdf_path = artifact_writer.bin_path("compacted-source.pdf")
    output_page_count = packer.pack(extracted_blocks, output_pdf_path)
    print(f"      Output: {output_page_count} pages -> {output_pdf_path}")

    # ── Step 4: Generate reports ──────────────────────────────────────────────
    reporter = Reporter()
    boundary_map_md, report_md, passed = reporter.generate(
        detection_result=detection_result,
        original_page_count=original_page_count,
        output_page_count=output_page_count,
        source_filename=source_filename,
        run_id=artifact_writer.run_id,
        grade=grade,
        subject=subject,
    )
    artifact_writer.write("source-boundary-map.md", boundary_map_md)
    artifact_writer.write("compaction-report.md", report_md)

    # ── Final result ──────────────────────────────────────────────────────────
    verdict = "PASS" if passed else "FAIL"
    pages_saved = original_page_count - output_page_count
    reduction = round((pages_saved / original_page_count) * 100, 1) if original_page_count else 0.0

    print(f"\n[MTS] Result: {verdict}")
    print(
        f"[MTS] {original_page_count} pages -> {output_page_count} pages "
        f"({pages_saved} saved, {reduction}% reduction)"
    )
    print(f"[MTS] PDF:       {output_pdf_path}")
    print(f"[MTS] Artifacts: {artifact_writer.run_path}")

    if not passed:
        print("[MTS] Review compaction-report.md for failure details.")
        sys.exit(1)

    # Optional: run visual comparator against a golden sample
    if compare:
        if golden is None:
            print("[MTS] Comparison requested but no --golden path provided.")
            sys.exit(2)
        print("[MTS] Running visual comparison against golden sample...")
        comp_dir = artifact_writer.run_path / "comparisons"
        summary = compare_pdfs(golden_pdf=golden, output_pdf=output_pdf_path, report_dir=comp_dir)
        print(f"[MTS] Comparison summary: {summary.get('defect_count', 0)} defects")
        if summary.get("defect_count", 0) > 0:
            print(f"[MTS] Defects found. See comparison artifacts in: {comp_dir}")
            print("[MTS] Please review defects before enabling automated repair.")
            sys.exit(3)


def run_generate_worksheet(request_path: Path) -> None:
    """
    Execute the generate_worksheet pipeline. (Phase 3 — not yet implemented)

    Args:
        request_path: Path to the worksheet request JSON file.
    """
    print("[MTS] generate_worksheet mode is Phase 3 — not yet implemented.")
    print(f"[MTS] Request file provided: {request_path}")
    sys.exit(1)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the MTS orchestrator."""
    parser = argparse.ArgumentParser(
        description="MTS Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.orchestrator compact_source "
            "--pdf docs/exams/exam.pdf --grade 8 --subject Math\n"
            "  python -m src.orchestrator generate_worksheet "
            "--request requests/worksheet-request.json\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    compact_parser = subparsers.add_parser(
        "compact_source",
        help="Compact a source worksheet PDF into a print-efficient PDF",
    )
    compact_parser.add_argument(
        "--pdf", type=Path, required=True,
        help="Path to the input source worksheet PDF",
    )
    compact_parser.add_argument(
        "--grade", type=int, required=True,
        help="Grade level (e.g., 8)",
    )
    compact_parser.add_argument(
        "--subject", type=str, default="Math",
        help="Subject area (default: Math)",
    )
    compact_parser.add_argument(
        "--scale-factor", type=float, default=None,
        help=(
            "Scale blocks as %% of their natural fit width "
            "(default: BLOCK_SCALE_FACTOR from config, initially 100). "
            "Example: --scale-factor 85 shrinks each block to 85%%."
        ),
    )
    compact_parser.add_argument(
        "--max-pages", type=int, default=None,
        help=(
            "Target total number of output pages. The packer auto-computes a "
            "scale factor so all blocks fit within this page budget. Combined "
            "with --scale-factor, the smaller of the two scales is used."
        ),
    )
    compact_parser.add_argument(
        "--columns", type=int, default=1, choices=[1, 2],
        help="Number of columns in the output layout (1 or 2, default 1).",
    )
    compact_parser.add_argument(
        "--max-block-pages", type=int, default=None,
        help=(
            "Internal safety cap: maximum number of output column-heights a single "
            "block may occupy before being force-downscaled "
            "(default: DEFAULT_MAX_BLOCK_PAGES from config, 2)."
        ),
    )
    compact_parser.add_argument(
        "--problem-list", type=str, default="ALL",
        help=(
            "Filter which problems to include in the compacted output. "
            "Values: ALL (default), ranges like '1-10', or comma lists like '1,3,5'."
        ),
    )
    compact_parser.add_argument(
        "--compare", action="store_true",
        help="Run visual comparison against a golden sample after packing (requires --golden).",
    )
    compact_parser.add_argument(
        "--golden", type=Path, default=None,
        help="Path to the golden sample PDF to compare the output against.",
    )

    worksheet_parser = subparsers.add_parser(
        "generate_worksheet",
        help="Generate an MTS worksheet from a source document (Phase 3)",
    )
    worksheet_parser.add_argument(
        "--request", type=Path, required=True,
        help="Path to the worksheet request JSON file",
    )

    return parser


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate pipeline mode."""
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.mode == "compact_source":
        run_compact_source(
            pdf_path=args.pdf,
            grade=args.grade,
            subject=args.subject,
            scale_factor=args.scale_factor,
            max_pages=args.max_pages,
            columns=args.columns,
            max_block_pages=args.max_block_pages,
            problem_list=args.problem_list,
            compare=args.compare,
            golden=args.golden,
        )
    elif args.mode == "generate_worksheet":
        run_generate_worksheet(request_path=args.request)


if __name__ == "__main__":
    main()
