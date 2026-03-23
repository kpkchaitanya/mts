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

from src.compact_source.boundary_detector import BoundaryDetector, BoundaryNotFoundError
from src.compact_source.compactor import Compactor
from src.compact_source.reporter import Reporter
from src.compact_source.stripper import Stripper
from src.utils.artifact_writer import ArtifactWriter
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import extract_text_by_page, get_page_count
from src.utils.markdown_utils import frontmatter, horizontal_rule
from src.utils.pdf_renderer import render_markdown_to_pdf
from src.config import LINES_PER_PAGE_ESTIMATE


def run_compact_source(pdf_path: Path, grade: int, subject: str) -> None:
    """
    Execute the full compact_source pipeline for a given state exam PDF.

    Pipeline steps:
    1. Extract text from all PDF pages
    2. BoundaryDetector  → locate Q1 and Qn
    3. Stripper          → remove pre/post content, write source-boundary-map.md
    4. Compactor         → reflow questions, eliminate gaps
    5. Reporter          → validate integrity, write compaction-report.md
    6. ArtifactWriter    → write compacted-source.md

    Args:
        pdf_path: Path to the input PDF file.
        grade: Grade level of the exam.
        subject: Subject area (e.g., "Math").

    Raises:
        FileNotFoundError: If the PDF does not exist at pdf_path.
        BoundaryNotFoundError: If question boundaries cannot be detected.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: '{pdf_path}'. "
            "Check the file path and try again."
        )

    print(f"\n[MTS] compact_source — {pdf_path.name}")
    print(f"[MTS] Grade: {grade} | Subject: {subject}")

    # Initialize shared dependencies used across pipeline steps
    claude_client = ClaudeClient()
    artifact_writer = ArtifactWriter()
    source_filename = pdf_path.name

    print(f"[MTS] Run ID: {artifact_writer.run_id}")
    print(f"[MTS] Artifacts: {artifact_writer.run_path}\n")

    # ── Step 1: Extract text from all pages ──────────────────────────────────
    print("[1/4] Extracting text from PDF...")
    page_texts = extract_text_by_page(pdf_path)
    original_page_count = get_page_count(pdf_path)
    print(f"      {original_page_count} pages found")

    # ── Step 2: Detect question boundaries ───────────────────────────────────
    print("[2/4] Detecting question boundaries...")
    detector = BoundaryDetector(claude_client)
    boundaries = detector.detect(pdf_path, page_texts)
    print(
        f"      Q1 on page {boundaries.first_question.page_number} | "
        f"Q{boundaries.total_questions} on page {boundaries.last_question.page_number} | "
        f"Total: {boundaries.total_questions} questions"
    )
    if boundaries.used_vision_fallback:
        print("      (Claude vision fallback used for boundary detection)")

    # ── Step 3: Strip non-question content ───────────────────────────────────
    print("[3/4] Stripping non-question content...")
    stripper = Stripper()
    stripped_content, boundary_map_md = stripper.strip(
        page_texts, boundaries, source_filename, artifact_writer.run_id, grade, subject
    )
    artifact_writer.write("source-boundary-map.md", boundary_map_md)
    print(
        f"      Removed ~{stripped_content.lines_removed_before} lines before Q1, "
        f"~{stripped_content.lines_removed_after} lines after Qn"
    )

    # ── Step 4: Compact the stripped content ─────────────────────────────────
    print("[4/4] Compacting questions...")
    compactor = Compactor()
    compacted_body = compactor.compact(stripped_content)

    # Prepend a standard header to the compacted output for traceability
    header = (
        "# Compacted Source\n\n"
        + frontmatter(artifact_writer.run_id, source_filename, grade, subject)
        + horizontal_rule()
        + f"**Questions:** {boundaries.total_questions} | "
        f"**Original pages:** {original_page_count}\n"
        + horizontal_rule()
        + "\n"
    )
    compacted_md_content = header + compacted_body
    artifact_writer.write("compacted-source.md", compacted_md_content)

    pdf_output_path = artifact_writer.artifact_path("compacted-source.pdf")
    render_markdown_to_pdf(compacted_md_content, pdf_output_path)

    # ── Step 5: Generate compaction report ───────────────────────────────────
    # Estimate compacted page count from line count and configured lines-per-page
    compacted_line_count = len(compacted_body.splitlines())
    compacted_page_estimate = max(1, compacted_line_count // LINES_PER_PAGE_ESTIMATE)

    reporter = Reporter()
    report_md, passed = reporter.generate(
        compacted_markdown=compacted_body,
        boundaries=boundaries,
        original_page_count=original_page_count,
        compacted_page_estimate=compacted_page_estimate,
        source_filename=source_filename,
        run_id=artifact_writer.run_id,
        grade=grade,
        subject=subject,
    )
    artifact_writer.write("compaction-report.md", report_md)

    # ── Final result ──────────────────────────────────────────────────────────
    verdict = "PASS" if passed else "FAIL"
    print(f"\n[MTS] Result: {verdict}")
    print(f"[MTS] Original: {original_page_count} pages -> Compacted: ~{compacted_page_estimate} pages")
    print(f"[MTS] Artifacts written to: {artifact_writer.run_path}")
    print(f"[MTS] PDF: {pdf_output_path}")

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
    """
    Build the CLI argument parser for the MTS orchestrator.

    Returns:
        Configured ArgumentParser with subcommands for each pipeline mode.
    """
    parser = argparse.ArgumentParser(
        description="MTS Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.orchestrator compact_source "
            "--pdf docs/strategy/flyers/exam.pdf --grade 8 --subject Math\n"
            "  python -m src.orchestrator generate_worksheet "
            "--request requests/worksheet-request.json\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    # ── compact_source subcommand ─────────────────────────────────────────────
    compact_parser = subparsers.add_parser(
        "compact_source",
        help="Strip non-question content from a state exam PDF and compact for printing",
    )
    compact_parser.add_argument(
        "--pdf", type=Path, required=True,
        help="Path to the input state exam PDF",
    )
    compact_parser.add_argument(
        "--grade", type=int, required=True,
        help="Grade level of the exam (e.g., 8)",
    )
    compact_parser.add_argument(
        "--subject", type=str, default="Math",
        help="Subject area (default: Math)",
    )

    # ── generate_worksheet subcommand ─────────────────────────────────────────
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
    """
    Parse CLI arguments and dispatch to the appropriate pipeline mode.
    """
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
