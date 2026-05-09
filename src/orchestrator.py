"""
orchestrator.py

Entry point for the MTS pipeline system.
Routes requests to the correct transformation mode and runs the full pipeline.

Usage (run from the project root):
    python -m src.orchestrator compact_source_math --pdf <path> --grade <n> --subject <subject>
    python -m src.orchestrator compact_source_reading --pdf <path> --grade <n> --subject <subject>
    python -m src.orchestrator generate_math_worksheet --request <path>
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.compact_source_math.block_detector import (
    BlockDetector,
    BlockDetectionError,
    BlockDetectionResult,
)
from src.compact_source_math.block_extractor import BlockExtractor
from src.compact_source_math.pdf_packer import PdfPacker
from src.compact_source_math.reporter import Reporter
from src.compact_source_math.comparator import compare_pdfs
from src.compact_source_reading.passage_detector import PassageDetector
from src.compact_source_reading.passage_extractor import PassageExtractor
from src.compact_source_reading.pdf_packer import ReadingPdfPacker
from src.compact_source_reading.reporter import ReadingReporter
from src.utils.artifact_writer import ArtifactWriter
from src.utils.claude_client import ClaudeClient
from src.utils.pdf_utils import get_page_count
from src.utils.telemetry import RunTelemetry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("mts")

_LOGGING_HANDLERS: list[logging.Handler] = []


def _setup_run_logging(run_log_path: Path) -> None:
    """
    Attach a StreamHandler (INFO → stdout) and a FileHandler (DEBUG → run.log)
    to the "mts" root logger.

    Call once at the start of a run.  Use _teardown_run_logging() in a finally
    block to ensure handlers are removed even when an exception is raised.

    Args:
        run_log_path: Absolute path for the run's log file.
    """
    mts_logger = logging.getLogger("mts")
    mts_logger.setLevel(logging.DEBUG)

    console_fmt = logging.Formatter("[MTS] %(message)s")
    file_fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s — %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)

    file_handler = logging.FileHandler(run_log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    mts_logger.addHandler(console_handler)
    mts_logger.addHandler(file_handler)

    _LOGGING_HANDLERS.extend([console_handler, file_handler])


def _teardown_run_logging() -> None:
    """
    Detach and close all handlers registered by _setup_run_logging().

    Safe to call multiple times — subsequent calls after teardown are no-ops.
    """
    mts_logger = logging.getLogger("mts")
    for handler in list(_LOGGING_HANDLERS):
        handler.flush()
        handler.close()
        mts_logger.removeHandler(handler)
    _LOGGING_HANDLERS.clear()


def run_compact_source_math(
    pdf_path: Path,
    grade: int,
    subject: str,
    scale_factor: float = None,
    max_pages: int = None,
    columns: int | str = "dual",
    max_block_pages: int = None,
    problem_list: str | None = None,
    compare: bool = False,
    golden: Path | None = None,
    artifact_writer: ArtifactWriter | None = None,
    setup_logging: bool = True,
    add_question_numbers: bool | None = None,
    question_start: int = 1,
    auto_confirm: bool = False,
) -> RunTelemetry:
    """
    Execute the full compact_source_math pipeline for a given source worksheet PDF.

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
        pdf_path:       Path to the input source worksheet PDF.
        grade:          Grade level.
        subject:        Subject area (e.g., "Math").
        setup_logging:  When True (default) attach/detach logging handlers for
                        this run.  Pass False in folder mode where main() owns
                        the handler lifecycle.

    Returns:
        RunTelemetry record for this run.

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

    shared_writer = artifact_writer is not None
    if not shared_writer:
        artifact_writer = ArtifactWriter()

    if setup_logging:
        _setup_run_logging(artifact_writer.artifact_path("run.log"))

    run_start = time.perf_counter()

    tel = RunTelemetry(
        run_id=artifact_writer.run_id,
        feature="compact_source_math",
        source_file=pdf_path.name,
        source_path=str(pdf_path.resolve()),
        parameters={
            "grade": grade,
            "subject": subject,
            "scale_factor": scale_factor,
            "max_pages": max_pages,
            "columns": columns,
            "max_block_pages": max_block_pages,
            "problem_list": problem_list or "ALL",
            "add_question_numbers": add_question_numbers,
            "question_start": question_start,
        },
    )

    try:
        source_filename = pdf_path.name

        logger.info("")
        logger.info(f"compact_source_math — {pdf_path.name}")
        _col_label = "1+2 (dual)" if columns == "dual" else str(columns)
        logger.info(
            f"Grade: {grade} | Subject: {subject} | Scale: {scale_factor}% | "
            f"Columns: {_col_label}"
            + (f" | Max pages: {max_pages}" if max_pages is not None else "")
        )
        logger.info(f"Run ID: {artifact_writer.run_id}")
        logger.info(f"Artifacts: {artifact_writer.run_path}")
        logger.info("")

        original_page_count = get_page_count(pdf_path)
        original_size_bytes = pdf_path.stat().st_size
        logger.info(f"Source: {original_page_count} pages")

        tel.source_stats = {
            "page_count": original_page_count,
            "size_bytes": original_size_bytes,
        }

        claude_client = ClaudeClient()

        # ── Step 1: Detect question blocks ────────────────────────────────────
        logger.info("[1/4] Detecting question blocks...")
        t1 = time.perf_counter()
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

        detection_result = BlockDetectionResult(
            blocks=filtered_blocks,
            total_questions=len(filtered_blocks),
            page_heights=detection_result.page_heights,
            page_widths=detection_result.page_widths,
            used_vision_fallback=detection_result.used_vision_fallback,
            is_image_heavy=detection_result.is_image_heavy,
        )
        tel.timings.record("block_detection", time.perf_counter() - t1)

        if detection_result.used_vision_fallback:
            logger.warning("      Vision fallback used — text extraction was insufficient")
            tel.add_defect(
                stage="block_detection",
                severity="warning",
                code="VISION_FALLBACK_USED",
                message="Claude vision API was used as fallback for block detection.",
            )

        if detection_result.total_questions == 0:
            tel.add_defect(
                stage="block_detection",
                severity="error",
                code="ZERO_BLOCKS_DETECTED",
                message="No question blocks detected in the source PDF.",
            )

        logger.info(
            f"      {detection_result.total_questions} question blocks detected"
            + (" (vision fallback used)" if detection_result.used_vision_fallback else "")
        )
        tel.stages["block_detection"] = {
            "total_questions": detection_result.total_questions,
            "used_vision_fallback": detection_result.used_vision_fallback,
        }

        # ── Human gate: validate question count before extraction ─────────────
        # Block detection can misclassify hybrid-format PDFs (e.g. exam sources
        # with instruction pages that inflate word counts, causing an image-heavy
        # document to be classified as text_rich). This gate gives the operator
        # a chance to abort before extraction produces a wrong output.
        # Pass --yes (auto_confirm=True) to skip in batch / scripted runs.
        if not auto_confirm:
            n = detection_result.total_questions
            low_count = n < 3 or (original_page_count > 0 and n / original_page_count < 0.5)
            if low_count:
                logger.warning(
                    f"      WARNING: only {n} block(s) detected from "
                    f"{original_page_count} source pages. "
                    "This may indicate a format classification error (e.g. "
                    "a hybrid PDF wrongly classified as text_rich). "
                    "Verify the source PDF format before proceeding."
                )
            if sys.stdin.isatty():
                try:
                    prompt_lines = [
                        "",
                        f"[MTS] --- Human Gate: Block Detection Complete ---",
                        f"[MTS] Detected  : {n} question block(s)",
                        f"[MTS] Source    : {original_page_count} pages  ({pdf_path.name})",
                        f"[MTS] Format    : {'image_heavy' if detection_result.is_image_heavy else 'text_rich'}",
                    ]
                    if low_count:
                        prompt_lines.append(
                            f"[MTS] *** LOW COUNT — expected ~1 block per content page ***"
                        )
                    prompt_lines.append("[MTS] Proceed with extraction? [Y/n]: ")
                    sys.stdout.write("\n".join(prompt_lines[:-1]) + "\n")
                    sys.stdout.flush()
                    answer = input(prompt_lines[-1]).strip().lower()
                    if answer in ("n", "no"):
                        logger.info("Run aborted by operator at question-count gate.")
                        sys.exit(0)
                except EOFError:
                    # Non-interactive pipe context — continue silently
                    pass

        # ── Step 2: Extract block images ──────────────────────────────────────
        logger.info("[2/4] Extracting question block images...")
        t2 = time.perf_counter()
        extractor = BlockExtractor()
        extracted_blocks = extractor.extract(pdf_path, detection_result.blocks)
        tel.timings.record("block_extraction", time.perf_counter() - t2)
        logger.info(f"      {len(extracted_blocks)} block images extracted")
        tel.stages["block_extraction"] = {"extracted_blocks": len(extracted_blocks)}

        # ── Step 3: Pack into output PDF ──────────────────────────────────────
        logger.info("[3/4] Packing blocks into output PDF...")
        t3 = time.perf_counter()
        layout_log_path = artifact_writer.run_path / f"{pdf_path.stem}_pack_layouts.csv"
        # Auto-enable question number labels for image-heavy PDFs (e.g. EOG) where
        # the number was embedded in the footer and is removed by the crop operation.
        # The caller can override by passing add_question_numbers explicitly.
        add_question_numbers_effective = add_question_numbers
        if add_question_numbers_effective is None:
            add_question_numbers_effective = detection_result.is_image_heavy

        # Determine columns to produce (dual mode = both 1-col and 2-col)
        _is_dual = columns == "dual"
        _columns_list: list[int] = [1, 2] if _is_dual else [int(columns)]

        packed_outputs: list[tuple[int, Path, int]] = []  # (col_count, pdf_path, page_count)
        for _col in _columns_list:
            packer = PdfPacker(
                scale_factor=scale_factor,
                max_pages=max_pages,
                columns=_col,
                max_block_pages=max_block_pages,
                layout_log_path=layout_log_path,
                add_question_numbers=add_question_numbers_effective,
                question_start=question_start,
            )
            _out_pdf = artifact_writer.artifact_path(
                f"{pdf_path.stem}_Compacted_{_col}col_{artifact_writer.run_id}.pdf"
            )
            _page_count = packer.pack(extracted_blocks, _out_pdf)
            logger.info(f"      {_col}-col: {_page_count} pages -> {_out_pdf}")
            packed_outputs.append((_col, _out_pdf, _page_count))

        tel.timings.record("pdf_packing", time.perf_counter() - t3)
        tel.stages["pdf_packing"] = {
            "outputs": {str(c): pc for c, _, pc in packed_outputs}
        }

        # ── Step 4: Generate reports ──────────────────────────────────────────
        logger.info("[4/4] Generating reports...")
        t4 = time.perf_counter()
        reporter = Reporter()
        passed = True
        _boundary_map_written = False
        for _col, output_pdf_path, output_page_count in packed_outputs:
            output_size_bytes = output_pdf_path.stat().st_size
            _col_label = f"_{_col}col" if _is_dual else ""
            boundary_map_md, report_md, _col_passed = reporter.generate(
                detection_result=detection_result,
                original_page_count=original_page_count,
                output_page_count=output_page_count,
                original_size_bytes=original_size_bytes,
                output_size_bytes=output_size_bytes,
                source_filename=source_filename,
                run_id=artifact_writer.run_id,
                grade=grade,
                subject=subject,
                extracted_blocks=extracted_blocks,
            )
            if not _boundary_map_written:
                _boundary_map_written = True
                logger.info("")
                logger.info(f"── Source Boundary Map: {pdf_path.stem} " + "─" * 20)
                for line in boundary_map_md.splitlines():
                    logger.info(line)
            logger.info("")
            logger.info(f"── Compaction Report: {pdf_path.stem}{_col_label} " + "─" * 20)
            for line in report_md.splitlines():
                logger.info(line)
            if not _col_passed:
                passed = False
        tel.timings.record("reporting", time.perf_counter() - t4)
        tel.stages["reporting"] = {"passed": passed}

        # ── Final result ──────────────────────────────────────────────────────
        verdict = "PASS" if passed else "FAIL"
        # Use the last packed output (2-col in dual mode) for summary stats
        _last_col, output_pdf_path, output_page_count = packed_outputs[-1]
        output_size_bytes = output_pdf_path.stat().st_size
        pages_saved = original_page_count - output_page_count
        reduction = (
            round((pages_saved / original_page_count) * 100, 1) if original_page_count else 0.0
        )

        def _fmt_size(b: int) -> str:
            if b >= 1_048_576:
                return f"{b / 1_048_576:.1f} MB"
            return f"{b / 1024:.0f} KB"

        size_delta = original_size_bytes - output_size_bytes
        size_pct = (
            round(abs(size_delta) / original_size_bytes * 100, 1) if original_size_bytes else 0.0
        )
        size_label = (
            f"{_fmt_size(abs(size_delta))} saved, {size_pct}% reduction"
            if size_delta >= 0
            else f"{_fmt_size(abs(size_delta))} larger (raster images)"
        )

        if size_delta < 0:
            tel.add_defect(
                stage="reporting",
                severity="info",
                code="OUTPUT_LARGER_THAN_SOURCE",
                message="Output PDF is larger than source — raster images inflated file size.",
                context={"source_bytes": original_size_bytes, "output_bytes": output_size_bytes},
            )

        tel.output_stats = {
            "page_count": output_page_count,
            "size_bytes": output_size_bytes,
            "pages_saved": pages_saved,
            "size_bytes_saved": size_delta,
        }
        tel.verdict = verdict
        total_s = time.perf_counter() - run_start
        tel.timings.total_duration_s = total_s

        # ── Consolidated log: pack layouts (read then delete the temp file) ────
        if layout_log_path.exists():
            logger.info("")
            logger.info(f"── Pack Layouts: {pdf_path.stem} " + "─" * 20)
            for line in layout_log_path.read_text(encoding="utf-8").splitlines():
                logger.info(line)
            layout_log_path.unlink(missing_ok=True)

        # ── Consolidated log: telemetry (in-memory, no file written) ────────────
        logger.info("")
        logger.info(f"── Telemetry: {pdf_path.stem} " + "─" * 20)
        for line in json.dumps(tel.to_dict(), indent=2).splitlines():
            logger.info(line)

        def _fmt_duration(s: float) -> str:
            if s >= 60:
                m = int(s) // 60
                sec = s - m * 60
                return f"{m}m {sec:.1f}s"
            return f"{s:.1f}s"

        logger.info("")
        logger.info(f"Result: {verdict}")
        logger.info(
            f"{original_page_count} pages -> {output_page_count} pages "
            f"({pages_saved} saved, {reduction}% reduction)"
        )
        logger.info(
            f"{_fmt_size(original_size_bytes)} -> {_fmt_size(output_size_bytes)} ({size_label})"
        )
        logger.info(f"Runtime:   {_fmt_duration(total_s)}")
        for _c, _p, _pc in packed_outputs:
            logger.info(f"PDF ({_c}-col): {_p}")
        logger.info(f"Artifacts: {artifact_writer.run_path}")

        if not passed:
            _report_suffix = f"_{_last_col}col" if _is_dual else ""
            logger.warning(
                f"Review {pdf_path.stem}{_report_suffix}_compaction-report.md for failure details."
            )
            if shared_writer:
                raise RuntimeError(f"FAIL:compaction")
            sys.exit(1)

        # Optional: run visual comparator against a golden sample
        if compare:
            if golden is None:
                logger.error("Comparison requested but no --golden path provided.")
                if shared_writer:
                    raise RuntimeError(f"No golden provided for {pdf_path.name}")
                sys.exit(2)
            logger.info("Running visual comparison against golden sample...")
            # In shared (folder) mode use a per-file subdir to avoid collisions
            if shared_writer:
                comp_dir = artifact_writer.run_path / "comparisons" / pdf_path.stem
            else:
                comp_dir = artifact_writer.run_path / "comparisons"
            comparison_summary = compare_pdfs(
                golden_pdf=golden, output_pdf=output_pdf_path, report_dir=comp_dir
            )
            defect_count = comparison_summary.get("defect_count", 0)
            logger.info(f"Comparison summary: {defect_count} defects")
            if defect_count > 0:
                logger.warning(f"Defects found. See comparison artifacts in: {comp_dir}")
                logger.warning("Please review defects before enabling automated repair.")
                if shared_writer:
                    raise RuntimeError(f"DEFECTS:{defect_count}")
                sys.exit(3)

        return tel

    finally:
        if setup_logging:
            _teardown_run_logging()


def run_compact_source_reading(
    pdf_path: Path,
    grade: int,
    subject: str,
    artifact_writer: ArtifactWriter | None = None,
    setup_logging: bool = True,
) -> RunTelemetry:
    """
    Execute the full compact_source_reading pipeline for a given ELA source PDF.

    Pipeline steps:
    1. PassageDetector  — locate passage groups using pdfplumber text extraction
    2. PassageExtractor — render each page as a trimmed PNG image
    3. ReadingPdfPacker — assemble page images into a compact output PDF
    4. ReadingReporter  — validate integrity, write passage-map.md
                          and compaction-report.md

    Args:
        pdf_path:      Path to the ELA source PDF.
        grade:         Grade level.
        subject:       Subject area (e.g. "reading", "ELA").
        setup_logging: When True (default) attach/detach logging handlers.

    Returns:
        RunTelemetry record for this run.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: '{pdf_path}'. Check the file path and try again."
        )

    shared_writer = artifact_writer is not None
    if not shared_writer:
        artifact_writer = ArtifactWriter(feature_name="reading_worksheet_generation_from_source")

    if setup_logging:
        _setup_run_logging(artifact_writer.artifact_path("run.log"))

    run_start = time.perf_counter()

    tel = RunTelemetry(
        run_id=artifact_writer.run_id,
        feature="compact_source_reading",
        source_file=pdf_path.name,
        source_path=str(pdf_path.resolve()),
        parameters={"grade": grade, "subject": subject},
    )

    try:
        logger.info("")
        logger.info(f"compact_source_reading — {pdf_path.name}")
        logger.info(f"Grade: {grade} | Subject: {subject}")
        logger.info(f"Run ID: {artifact_writer.run_id}")
        logger.info(f"Artifacts: {artifact_writer.run_path}")
        logger.info("")

        original_page_count = get_page_count(pdf_path)
        original_size_bytes = pdf_path.stat().st_size
        logger.info(f"Source: {original_page_count} pages")

        tel.source_stats = {
            "page_count": original_page_count,
            "size_bytes": original_size_bytes,
        }

        # ── Step 1: Detect passage groups ─────────────────────────────────────
        logger.info("[1/4] Detecting passage groups...")
        t1 = time.perf_counter()
        detector = PassageDetector()
        detection_result = detector.detect(pdf_path)
        tel.timings.record("passage_detection", time.perf_counter() - t1)

        if detection_result.total_passages == 0:
            tel.add_defect(
                stage="passage_detection",
                severity="error",
                code="ZERO_PASSAGES_DETECTED",
                message="No passage groups detected in the source PDF.",
            )

        logger.info(
            f"      {detection_result.total_passages} passage group(s) detected, "
            f"{detection_result.total_question_pages} question page(s)"
        )
        tel.stages["passage_detection"] = {
            "total_passages": detection_result.total_passages,
            "total_question_pages": detection_result.total_question_pages,
        }

        # ── Step 2: Extract page images ───────────────────────────────────────
        logger.info("[2/4] Extracting page images...")
        t2 = time.perf_counter()
        extractor = PassageExtractor()
        extracted_groups = extractor.extract(pdf_path, detection_result.groups)
        total_pages_extracted = sum(len(g.pages) for g in extracted_groups)
        tel.timings.record("page_extraction", time.perf_counter() - t2)
        logger.info(f"      {total_pages_extracted} page image(s) extracted")
        tel.stages["page_extraction"] = {"total_pages": total_pages_extracted}

        # ── Step 3: Pack into output PDF ──────────────────────────────────────
        logger.info("[3/4] Packing pages into output PDF...")
        t3 = time.perf_counter()
        packer = ReadingPdfPacker()
        output_pdf_path = artifact_writer.artifact_path(
            f"{pdf_path.stem}_Compacted_{artifact_writer.run_id}.pdf"
        )
        output_page_count, groups_written = packer.pack(extracted_groups, output_pdf_path)
        tel.timings.record("pdf_packing", time.perf_counter() - t3)
        logger.info(f"      Output: {output_page_count} pages -> {output_pdf_path}")
        tel.stages["pdf_packing"] = {
            "output_page_count": output_page_count,
            "groups_written": groups_written,
        }

        # ── Step 4: Generate reports ──────────────────────────────────────────
        logger.info("[4/4] Generating reports...")
        t4 = time.perf_counter()
        output_size_bytes = output_pdf_path.stat().st_size
        reporter = ReadingReporter()
        passage_map_md, report_md, passed = reporter.generate(
            detection_result=detection_result,
            extracted_groups=extracted_groups,
            original_page_count=original_page_count,
            output_page_count=output_page_count,
            source_filename=pdf_path.name,
            run_id=artifact_writer.run_id,
            grade=grade,
            subject=subject,
            original_size_bytes=original_size_bytes,
            output_size_bytes=output_size_bytes,
        )
        artifact_writer.write(f"{pdf_path.stem}_passage-map.md", passage_map_md)
        artifact_writer.write(f"{pdf_path.stem}_compaction-report.md", report_md)
        tel.timings.record("reporting", time.perf_counter() - t4)
        tel.stages["reporting"] = {"passed": passed}

        # ── Final result ──────────────────────────────────────────────────────
        verdict = "PASS" if passed else "FAIL"
        pages_saved = original_page_count - output_page_count
        reduction = (
            round((pages_saved / original_page_count) * 100, 1)
            if original_page_count else 0.0
        )

        def _fmt_size(b: int) -> str:
            return f"{b / 1_048_576:.1f} MB" if b >= 1_048_576 else f"{b / 1024:.0f} KB"

        size_delta = original_size_bytes - output_size_bytes
        size_pct = (
            round(abs(size_delta) / original_size_bytes * 100, 1)
            if original_size_bytes else 0.0
        )
        size_label = (
            f"{_fmt_size(abs(size_delta))} saved, {size_pct}% reduction"
            if size_delta >= 0
            else f"{_fmt_size(abs(size_delta))} larger (raster images)"
        )

        tel.output_stats = {
            "page_count": output_page_count,
            "size_bytes": output_size_bytes,
            "pages_saved": pages_saved,
            "size_bytes_saved": size_delta,
        }
        tel.verdict = verdict
        total_s = time.perf_counter() - run_start
        tel.timings.total_duration_s = total_s
        tel.save(artifact_writer, pdf_path.stem)

        def _fmt_duration(s: float) -> str:
            if s >= 60:
                m = int(s) // 60
                sec = s - m * 60
                return f"{m}m {sec:.1f}s"
            return f"{s:.1f}s"

        logger.info("")
        logger.info(f"Result: {verdict}")
        logger.info(
            f"{original_page_count} pages -> {output_page_count} pages "
            f"({pages_saved} saved, {reduction}% reduction)"
        )
        logger.info(
            f"{_fmt_size(original_size_bytes)} -> {_fmt_size(output_size_bytes)} ({size_label})"
        )
        logger.info(f"Runtime:   {_fmt_duration(total_s)}")
        logger.info(f"PDF:       {output_pdf_path}")
        logger.info(f"Artifacts: {artifact_writer.run_path}")

        if not passed:
            logger.warning(
                f"Review {pdf_path.stem}_compaction-report.md for failure details."
            )
            if shared_writer:
                raise RuntimeError("FAIL:compaction")
            sys.exit(1)

        return tel

    finally:
        if setup_logging:
            _teardown_run_logging()


def run_generate_math_worksheet(request_path: Path) -> None:
    """
    Execute the generate_math_worksheet pipeline. (Phase 3 — not yet implemented)

    Args:
        request_path: Path to the worksheet request JSON file.
    """
    logger.info("generate_math_worksheet mode is Phase 3 — not yet implemented.")
    logger.info(f"Request file provided: {request_path}")
    sys.exit(1)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for the MTS orchestrator."""
    parser = argparse.ArgumentParser(
        description="MTS Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.orchestrator compact_source_math --pdf docs/exams/math/exam.pdf\n"
            "  python -m src.orchestrator compact_source_reading --pdf docs/exams/reading/exam.pdf\n"
            "  python -m src.orchestrator generate_math_worksheet "
            "--request requests/worksheet-request.json\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    compact_parser = subparsers.add_parser(
        "compact_source_math",
        help="Compact a source worksheet PDF into a print-efficient PDF",
    )
    compact_parser.add_argument(
        "--pdf", type=Path, required=True,
        help="Path to the input source worksheet PDF, or a folder to compact all PDFs inside it.",
    )
    compact_parser.add_argument(
        "--grade", type=int, default=0,
        help="Grade level (e.g., 8). Optional — used only as a label in reports.",
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
        "--columns",
        type=lambda v: "dual" if v == "dual" else int(v),
        default="dual",
        metavar="{1,2,dual}",
        help="Number of columns in the output layout (1, 2, or dual). Default: dual (generates both 1-col and 2-col PDFs in a single run).",
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
        "--no-question-numbers", action="store_true",
        help=(
            "Suppress automatic question number labels. "
            "By default, labels are added for image-heavy PDFs (e.g. EOG) "
            "where the question number was embedded in the footer and is removed by the crop."
        ),
    )
    compact_parser.add_argument(
        "--question-start", type=int, default=1,
        help=(
            "Starting question number for the label sequence (default: 1). "
            "Use this when the exam numbering begins at a value other than 1, "
            "or when running --problem-list on a subset and you want the labels "
            "to reflect the original exam numbers rather than the detected sequence."
        ),
    )
    compact_parser.add_argument(
        "--yes", "-y", action="store_true",
        help=(
            "Skip the human question-count confirmation gate after block detection. "
            "Use in batch or scripted runs where an operator is not present to confirm."
        ),
    )
    compact_parser.add_argument(
        "--compare", action="store_true",
        help="Run visual comparison against a golden sample after packing (requires --golden or --golden-dir).",
    )
    compact_parser.add_argument(
        "--golden", type=Path, default=None,
        help="Path to the golden sample PDF to compare the output against (single-file mode).",
    )
    compact_parser.add_argument(
        "--golden-dir", type=Path, default=None,
        help=(
            "Directory of golden sample PDFs for folder mode. "
            "Each golden file must be named <source-stem>-golden-sample.pdf."
        ),
    )

    reading_parser = subparsers.add_parser(
        "compact_source_reading",
        help="Compact an ELA / Reading source PDF into a print-efficient PDF",
    )
    reading_parser.add_argument(
        "--pdf", type=Path, required=True,
        help="Path to the ELA source PDF.",
    )
    reading_parser.add_argument(
        "--grade", type=int, required=True,
        help="Grade level (e.g. 3).",
    )
    reading_parser.add_argument(
        "--subject", type=str, default="reading",
        help="Subject label (default: reading).",
    )

    worksheet_parser = subparsers.add_parser(
        "generate_math_worksheet",
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

    if args.mode == "compact_source_math":
        pdf_input: Path = args.pdf

        if pdf_input.is_dir():
            pdf_files = sorted(pdf_input.glob("*.pdf"))
            if not pdf_files:
                logger.error(f"No PDF files found in folder: {pdf_input}")
                sys.exit(1)

            shared_writer = ArtifactWriter()
            _setup_run_logging(shared_writer.artifact_path("run.log"))
            batch_start = time.perf_counter()
            try:
                logger.info(f"Folder mode — {len(pdf_files)} PDF(s) found in '{pdf_input}'")
                logger.info(f"Run ID: {shared_writer.run_id}")
                logger.info(f"Artifacts: {shared_writer.run_path}")
                logger.info("")

                telemetry_records: list[dict] = []
                results: list[tuple[str, str, float]] = []

                for pdf_file in pdf_files:
                    # Resolve golden for this file if --golden-dir provided
                    per_file_golden: Path | None = None
                    if args.compare and args.golden_dir:
                        candidate = args.golden_dir / f"{pdf_file.stem}-golden-sample.pdf"
                        if candidate.exists():
                            per_file_golden = candidate
                        else:
                            logger.warning(
                                f"No golden found for {pdf_file.name} "
                                f"(expected: {candidate}) — skipping comparison."
                            )
                    file_start = time.perf_counter()
                    file_status = "PASS"
                    try:
                        tel = run_compact_source_math(
                            pdf_path=pdf_file,
                            grade=args.grade,
                            subject=args.subject,
                            scale_factor=args.scale_factor,
                            max_pages=args.max_pages,
                            columns=args.columns,
                            max_block_pages=args.max_block_pages,
                            problem_list=args.problem_list,
                            compare=args.compare and per_file_golden is not None,
                            golden=per_file_golden,
                            artifact_writer=shared_writer,
                            setup_logging=False,
                            add_question_numbers=False if args.no_question_numbers else None,
                            question_start=args.question_start,
                            auto_confirm=args.yes,
                        )
                        results.append((pdf_file.name, "PASS", time.perf_counter() - file_start))
                        telemetry_records.append(tel.to_dict())
                    except RuntimeError as exc:
                        msg = str(exc)
                        if msg.startswith("DEFECTS:"):
                            count = msg.split(":", 1)[1]
                            file_status = f"DEFECTS({count})"
                        else:
                            logger.error(f"ERROR processing {pdf_file.name}: {exc}")
                            file_status = "FAIL"
                        results.append((pdf_file.name, file_status, time.perf_counter() - file_start))
                        telemetry_records.append(
                            {"source_file": pdf_file.name, "verdict": file_status, "error": msg}
                        )
                    except Exception as exc:
                        logger.error(f"ERROR processing {pdf_file.name}: {exc}")
                        results.append((pdf_file.name, "FAIL", time.perf_counter() - file_start))
                        telemetry_records.append(
                            {"source_file": pdf_file.name, "verdict": "FAIL", "error": str(exc)}
                        )

                total_batch_s = time.perf_counter() - batch_start

                def _fmt_dur(s: float) -> str:
                    if s >= 60:
                        m = int(s) // 60
                        sec = s - m * 60
                        return f"{m}m {sec:.1f}s"
                    return f"{s:.1f}s"

                logger.info("")
                logger.info("Folder run summary:")
                for name, status, dur in results:
                    logger.info(f"  {status:<14}  {_fmt_dur(dur):<10}  {name}")
                logger.info("  " + "—" * 40)
                logger.info(f"  Total runtime: {_fmt_dur(total_batch_s)}")

                # ── Consolidated defect list ──────────────────────────────
                all_defects: list[tuple[str, dict]] = []
                for pdf_file in pdf_files:
                    comp_report = (
                        shared_writer.run_path
                        / "comparisons"
                        / pdf_file.stem
                        / "comparison_report.json"
                    )
                    if comp_report.exists():
                        import json as _json
                        data = _json.loads(comp_report.read_text(encoding="utf-8"))
                        for d in data.get("defects", []):
                            all_defects.append((pdf_file.stem, d))

                if all_defects:
                    logger.info("")
                    logger.info("Consolidated defect list:")
                    logger.info(
                        f"  {'ID':<10} {'Source':<36} {'Page':<6} "
                        f"{'Sev':<10} {'Pri':<5} Description"
                    )
                    logger.info("  " + "—" * 100)
                    for source_stem, d in all_defects:
                        page_str = str(d.get("page", "—"))
                        desc = d.get("description", "")
                        # Truncate description to 60 chars for console
                        if len(desc) > 60:
                            desc = desc[:57] + "..."
                        logger.info(
                            f"  {d.get('id', '?'):<10} {source_stem:<36} {page_str:<6} "
                            f"{d.get('severity', '?'):<10} {d.get('priority', '?'):<5} {desc}"
                        )
                    logger.info("  " + "—" * 100)
                    logger.info(f"  Total: {len(all_defects)} defects across {len(pdf_files)} files")

                # Write batch telemetry
                batch_payload = {
                    "run_id": shared_writer.run_id,
                    "total_files": len(pdf_files),
                    "passed": sum(1 for _, s, _ in results if s == "PASS"),
                    "defects": sum(1 for _, s, _ in results if s.startswith("DEFECTS")),
                    "failed": sum(1 for _, s, _ in results if s == "FAIL"),
                    "runs": telemetry_records,
                }
                shared_writer.write(
                    "batch-telemetry.json", json.dumps(batch_payload, indent=2)
                )
                logger.debug(f"Batch telemetry written to {shared_writer.run_path / 'batch-telemetry.json'}")

            finally:
                _teardown_run_logging()

        else:
            run_compact_source_math(
                pdf_path=pdf_input,
                grade=args.grade,
                subject=args.subject,
                scale_factor=args.scale_factor,
                max_pages=args.max_pages,
                columns=args.columns,
                max_block_pages=args.max_block_pages,
                problem_list=args.problem_list,
                compare=args.compare,
                golden=args.golden,
                add_question_numbers=False if args.no_question_numbers else None,
                question_start=args.question_start,
                auto_confirm=args.yes,
            )
    elif args.mode == "compact_source_reading":
        run_compact_source_reading(
            pdf_path=args.pdf,
            grade=args.grade,
            subject=args.subject,
        )
    elif args.mode == "generate_math_worksheet":
        run_generate_math_worksheet(request_path=args.request)


if __name__ == "__main__":
    main()
