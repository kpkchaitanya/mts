"""
tests/test_pdf_packer.py

Unit tests for the question-number overlay feature in PdfPacker.

Covers IMP-018 (question number overlay for image-heavy PDFs).

Failure evidence without the feature:
  PdfPacker._render() only called page.insert_image() — no text was written.
  Opening the output PDF with fitz.Page.get_text() returned an empty string.
  The question_number field on ExtractedBlock was computed and stored correctly
  but never rendered into the output.

Test IDs: TC-PP-01 … TC-PP-05
"""

import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from src.compact_source.block_extractor import ExtractedBlock
from src.compact_source.pdf_packer import PdfPacker


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_png_bytes(width: int = 200, height: int = 150) -> bytes:
    """
    Produce a minimal white PNG image for use as a mock block.

    Creates a blank white page at the requested dimensions using PyMuPDF,
    renders it to a pixmap, and encodes it as PNG.  No external image
    library is required.
    """
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    pix = page.get_pixmap()
    doc.close()
    return pix.tobytes("png")


def _make_block(question_number: int, width: int = 200, height: int = 150) -> ExtractedBlock:
    """Build an ExtractedBlock with the given question number and a white PNG."""
    return ExtractedBlock(
        question_number=question_number,
        png_bytes=_make_png_bytes(width, height),
        source_width_pts=float(width),
        total_height_pts=float(height),
    )


def _extract_all_text(pdf_path: Path) -> str:
    """Open a PDF and return the concatenated text from all pages."""
    doc = fitz.open(str(pdf_path))
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestQuestionNumberOverlay:
    """TC-PP-01 … TC-PP-05: question number label overlay in PdfPacker."""

    def test_label_present_when_enabled(self, tmp_path: Path) -> None:
        """
        TC-PP-01: PdfPacker with add_question_numbers=True writes a "1." text
        label into the output PDF.

        Failure mode before IMP-018: _render() never called insert_text();
        get_text() returned '' for every block; assertion fails.
        """
        output = tmp_path / "out.pdf"
        packer = PdfPacker(add_question_numbers=True, question_start=1)
        packer.pack([_make_block(question_number=1)], output)

        all_text = _extract_all_text(output)
        assert "1." in all_text, (
            "Expected label '1.' in PDF text but found none. "
            "PdfPacker must overlay the question number when add_question_numbers=True."
        )

    def test_label_absent_when_disabled(self, tmp_path: Path) -> None:
        """
        TC-PP-02: PdfPacker with add_question_numbers=False writes NO text label.

        Ensures the feature does not inject numbers into text-rich PDFs where the
        question number is already embedded in the block image.
        """
        output = tmp_path / "out.pdf"
        packer = PdfPacker(add_question_numbers=False)
        packer.pack([_make_block(question_number=1)], output)

        all_text = _extract_all_text(output)
        assert "1." not in all_text, (
            "Label '1.' should not appear when add_question_numbers=False."
        )

    def test_question_start_offset_applied(self, tmp_path: Path) -> None:
        """
        TC-PP-03: question_start=5 shifts the label so that question_number=1
        is rendered as "5.", not "1.".

        Use case: user provides --question-start to align the compacted subset
        with the original exam numbering.
        """
        output = tmp_path / "out.pdf"
        packer = PdfPacker(add_question_numbers=True, question_start=5)
        packer.pack([_make_block(question_number=1)], output)

        all_text = _extract_all_text(output)
        assert "5." in all_text, (
            "Expected label '5.' (question_start=5, question_number=1) "
            "but it was not found in the PDF text."
        )
        assert "1." not in all_text, (
            "Label '1.' must not appear when question_start=5 and question_number=1 "
            "— the shift should fully replace the default numbering."
        )

    def test_each_block_gets_its_own_label(self, tmp_path: Path) -> None:
        """
        TC-PP-04: Each block in a multi-block pack receives its own label.

        Verifies that the label loop iterates over all placed blocks, not just
        the first, and that the label reflects each block's own question_number.
        """
        output = tmp_path / "out.pdf"
        packer = PdfPacker(add_question_numbers=True, question_start=1)
        blocks = [_make_block(question_number=n) for n in (1, 2, 3)]
        packer.pack(blocks, output)

        all_text = _extract_all_text(output)
        for expected in ("1.", "2.", "3."):
            assert expected in all_text, (
                f"Expected label '{expected}' in PDF text but it was not found. "
                "Every block must receive its own number label."
            )

    def test_default_constructor_does_not_add_labels(self, tmp_path: Path) -> None:
        """
        TC-PP-05: PdfPacker() with no arguments (all defaults) produces no labels.

        The default is add_question_numbers=False so that text-rich PDFs are
        unaffected unless the caller (orchestrator) explicitly enables labeling.
        The orchestrator auto-enables for is_image_heavy; text-rich defaults to off.
        """
        output = tmp_path / "out.pdf"
        packer = PdfPacker()  # default constructor — no add_question_numbers arg
        packer.pack([_make_block(question_number=7)], output)

        all_text = _extract_all_text(output)
        assert "7." not in all_text, (
            "PdfPacker() default constructor must NOT add question number labels. "
            "Labels are only injected when the orchestrator explicitly enables them."
        )
