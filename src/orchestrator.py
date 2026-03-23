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

from src.compact_source.block_detector import BlockDetector, BlockDetectionError
from src.compact_source.block_extractor import BlockExtractor
from src.compact_source.pdf_packer import PdfPacker
from src.compact_source.reporter import Reporter
from src.utils.artifact_writer import ArtifactWriter
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import get_page_count


def run_compact_source(pdf_path: Path, grade: int, subject: str) -> None:
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

    print(f"\n[MTS] compact_source — {pdf_path.name}")
    print(f"[MTS] Grade: {grade} | Subject: {subject}")

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
    packer = PdfPacker()
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
        )
    elif args.mode == "generate_worksheet":
        run_generate_worksheet(request_path=args.request)


if __name__ == "__main__":
    main()
