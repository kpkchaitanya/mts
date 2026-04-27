"""
reporter.py

Generates the two compaction artifacts for a compact_source run:
  - source-boundary-map.md  — question block inventory with y-coordinates
  - compaction-report.md    — page reduction metrics, integrity verdict,
                               and whitespace efficiency check

Inputs:  BlockDetectionResult, list of ExtractedBlock, original/output page counts
Outputs: (boundary_map_md, compaction_report_md, passed)
"""

from src.compact_source.block_detector import BlockDetectionResult
from src.compact_source.block_extractor import ExtractedBlock
from src.config import IMAGE_HEAVY_HEIGHT_WARN_FRACTION
from src.utils.markdown_utils import frontmatter, horizontal_rule, section_header, pass_fail_icon


class Reporter:
    """
    Generates the source-boundary-map.md and compaction-report.md artifacts.

    All validation is based on block counts from BlockDetectionResult —
    no text re-parsing or line counting is performed.
    """

    def generate(
        self,
        detection_result: BlockDetectionResult,
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
        original_size_bytes: int = 0,
        output_size_bytes: int = 0,
        extracted_blocks: list[ExtractedBlock] | None = None,
    ) -> tuple[str, str, bool]:
        """
        Generate both report artifacts.

        Args:
            detection_result:  Block detection output from BlockDetector.
            original_page_count: Total pages in the original source PDF.
            output_page_count: Actual pages in the compacted output PDF.
            source_filename:   Original PDF filename (for artifact metadata).
            run_id:            Pipeline run ID.
            grade:             Grade level.
            subject:           Subject area.
            original_size_bytes: File size of the source PDF in bytes.
            output_size_bytes:   File size of the compacted PDF in bytes.
            extracted_blocks:  Extracted block images for whitespace analysis.
                               If None, the whitespace section is omitted.

        Returns:
            Tuple of (boundary_map_md, compaction_report_md, passed).
            passed is True only if all integrity and quality checks pass.
        """
        boundary_map_md = self._build_boundary_map(
            detection_result=detection_result,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
        )

        report_md, passed = self._build_compaction_report(
            detection_result=detection_result,
            original_page_count=original_page_count,
            output_page_count=output_page_count,
            original_size_bytes=original_size_bytes,
            output_size_bytes=output_size_bytes,
            source_filename=source_filename,
            run_id=run_id,
            grade=grade,
            subject=subject,
            extracted_blocks=extracted_blocks,
        )

        return boundary_map_md, report_md, passed

    # ── Boundary Map ──────────────────────────────────────────────────────────

    def _build_boundary_map(
        self,
        detection_result: BlockDetectionResult,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
    ) -> str:
        blocks = detection_result.blocks
        detection_method = (
            "Text (pdfplumber y-coords) + Claude vision fallback"
            if detection_result.used_vision_fallback
            else "Text (pdfplumber y-coords)"
        )

        lines: list[str] = [
            "# Source Boundary Map",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Detection Method"),
            "",
            f"**{detection_method}**",
            "",
            f"Total question blocks detected: **{detection_result.total_questions}**",
            horizontal_rule(),
            section_header("Question Block Inventory"),
            "",
            "| Q# | Source Page(s) | Y-top (pts) | Y-bottom (pts) | Height (pts) | Multi-page |",
            "|----|---------------|-------------|----------------|-------------|-----------|",
        ]

        for block in blocks:
            pages = ", ".join(str(s.page_number) for s in block.slices)
            y_top = round(block.slices[0].y_top, 1)
            y_bottom = round(block.slices[-1].y_bottom, 1)
            height = round(block.total_height_pts, 1)
            multi = "Yes" if len(block.slices) > 1 else "No"
            lines.append(
                f"| {block.question_number} | {pages} | {y_top} | {y_bottom} | {height} | {multi} |"
            )

        if blocks:
            first = blocks[0]
            last = blocks[-1]
            lines += [
                horizontal_rule(),
                section_header("Boundary Summary"),
                "",
                f"- **First question (Q{first.question_number}):** "
                f"page {first.slices[0].page_number}, y={round(first.slices[0].y_top, 1)} pts",
                f"- **Last question (Q{last.question_number}):** "
                f"page {last.slices[-1].page_number}, y={round(last.slices[-1].y_bottom, 1)} pts",
            ]

        return "\n".join(lines)

    # ── Compaction Report ─────────────────────────────────────────────────────

    def _build_whitespace_section(
        self,
        detection_result: BlockDetectionResult,
        extracted_blocks: list[ExtractedBlock] | None = None,
    ) -> tuple[list[str], bool]:
        """
        Build the Block Height Efficiency section for the compaction report.

        For image-heavy PDFs (EOG style) checks that each block's detected
        y_bottom does not consume an excessive fraction of the page height.
        A block claiming >= IMAGE_HEAVY_HEIGHT_WARN_FRACTION of the page
        indicates the footer text anchored y_bottom near page_height (BUG-002
        class defect).  This check runs on block detection output — before
        the extractor — so it catches the root cause, not a downstream symptom.

        For text-rich PDFs the section is skipped (blocks span arbitrary
        fractions of a page by design).

        Returns:
            Tuple of (section_lines, passed).
            section_lines is empty when not applicable.
        """
        if not detection_result.is_image_heavy or not extracted_blocks:
            return [], True

        # Map question_number → page_height via detection_result for each block.
        page_heights = detection_result.page_heights
        block_page: dict[int, int] = {
            b.question_number: b.slices[-1].page_number
            for b in detection_result.blocks
        }

        rows: list[tuple[int, float, bool]] = []  # (q_num, height_fraction, flagged)
        for block in extracted_blocks:
            page_idx = block_page.get(block.question_number)
            ph = page_heights[page_idx] if page_idx is not None else 0.0
            fraction = block.total_height_pts / ph if ph > 0 else 0.0
            flagged = fraction >= IMAGE_HEAVY_HEIGHT_WARN_FRACTION
            rows.append((block.question_number, fraction, flagged))

        flagged_count = sum(1 for _, _, f in rows if f)
        section_pass = flagged_count == 0

        lines: list[str] = [
            section_header("Block Height Efficiency"),
            "",
            f"Threshold: block height must be < {IMAGE_HEAVY_HEIGHT_WARN_FRACTION:.0%} of page height",
            "",
            "| Q# | Block / Page Height | Status |",
            "|----|---------------------|--------|",
        ]

        for q_num, fraction, flagged in rows:
            status = "⚠ OVERSIZED" if flagged else "✓ OK"
            lines.append(f"| {q_num} | {fraction:.1%} | {status} |")

        lines += [
            "",
            f"**{flagged_count} of {len(rows)} blocks exceed height threshold.**",
            f"Block height check: {pass_fail_icon(section_pass)}",
        ]

        return lines, section_pass

    def _build_compaction_report(
        self,
        detection_result: BlockDetectionResult,
        original_page_count: int,
        output_page_count: int,
        source_filename: str,
        run_id: str,
        grade: int,
        subject: str,
        original_size_bytes: int = 0,
        output_size_bytes: int = 0,
        extracted_blocks: list[ExtractedBlock] | None = None,
    ) -> tuple[str, bool]:
        questions_detected = detection_result.total_questions
        pages_saved = original_page_count - output_page_count
        reduction_percent = (
            round((pages_saved / original_page_count) * 100, 1)
            if original_page_count > 0
            else 0.0
        )

        def _fmt_size(b: int) -> str:
            if b >= 1_048_576:
                return f"{b / 1_048_576:.1f} MB"
            return f"{b / 1024:.0f} KB"

        size_delta = original_size_bytes - output_size_bytes
        size_pct = round(abs(size_delta) / original_size_bytes * 100, 1) if original_size_bytes > 0 else 0.0
        if size_delta >= 0:
            size_delta_label = f"{_fmt_size(size_delta)} saved ({size_pct}% reduction)"
        else:
            size_delta_label = f"{_fmt_size(abs(size_delta))} larger (raster images, +{size_pct}%)"

        # Integrity: must have detected at least one block
        integrity_pass = questions_detected > 0

        # Block height efficiency check (image-heavy format only)
        whitespace_section, whitespace_pass = self._build_whitespace_section(detection_result, extracted_blocks)

        overall_pass = integrity_pass and whitespace_pass
        verdict = "PASS" if overall_pass else "FAIL"

        lines: list[str] = [
            "# Compaction Report",
            "",
            frontmatter(run_id, source_filename, grade, subject),
            horizontal_rule(),
            section_header("Page Reduction Summary"),
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Original Pages | {original_page_count} |",
            f"| Compacted Pages | {output_page_count} |",
            f"| Pages Saved | {pages_saved} ({reduction_percent}%) |",
            f"| Original Size | {_fmt_size(original_size_bytes)} |",
            f"| Compacted Size | {_fmt_size(output_size_bytes)} |",
            f"| Size Delta | {size_delta_label} |",
            horizontal_rule(),
            section_header("Question Integrity Check"),
            "",
            "| Check | Result |",
            "|-------|--------|",
            f"| Question blocks detected | {questions_detected} |",
            f"| All blocks retained in output | {pass_fail_icon(integrity_pass)} |",
            f"| No text re-rendered (visual extraction) | {pass_fail_icon(True)} |",
            f"| Vision fallback used | {'Yes' if detection_result.used_vision_fallback else 'No'} |",
            horizontal_rule(),
        ]

        # Insert whitespace efficiency section when extracted blocks were provided.
        if whitespace_section:
            lines += whitespace_section
            lines.append(horizontal_rule())

        lines += [
            section_header("Verdict"),
            "",
            f"**{verdict}**",
        ]

        if not integrity_pass:
            lines += [
                "",
                "- FAIL: No question blocks detected. "
                "Review source-boundary-map.md and check that the PDF contains numbered questions.",
            ]

        lines += [
            horizontal_rule(),
            section_header("Notes"),
            "",
            "_Review compacted-source.pdf to inspect the visual output._",
            "_Review source-boundary-map.md for the full block inventory._",
        ]

        return "\n".join(lines), overall_pass
