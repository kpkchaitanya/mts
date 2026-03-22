"""
pdf_utils.py

Shared PDF processing helpers for the MTS pipeline.
Wraps PyMuPDF (fitz) for image rendering and page geometry,
and pdfplumber for position-aware text extraction.

All PDF access in MTS should go through this module.
"""

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from src.config import PDF_RENDER_DPI


@dataclass
class PageText:
    """
    Text content extracted from a single PDF page.

    Attributes:
        page_number: Zero-based page index.
        text: Full raw text of the page as a single string.
        lines: Individual non-empty lines, stripped of leading/trailing whitespace.
    """
    page_number: int
    text: str
    lines: list[str] = field(default_factory=list)


def extract_text_by_page(pdf_path: Path) -> list[PageText]:
    """
    Extract text content from every page of a PDF.

    Uses pdfplumber for reliable layout-aware text extraction.

    Args:
        pdf_path: Path to the PDF file to read.

    Returns:
        List of PageText objects in document order (one per page).

    Raises:
        FileNotFoundError: If the PDF does not exist at pdf_path.
        ValueError: If the PDF has no pages or cannot be parsed.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: '{pdf_path}'. "
            "Verify the file path before calling extract_text_by_page."
        )

    pages: list[PageText] = []

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError(
                f"PDF '{pdf_path.name}' contains no pages. "
                "Confirm the file is a valid, non-empty PDF."
            )

        # Iterate each page and extract text, splitting into non-empty lines
        for page in pdf.pages:
            raw_text = page.extract_text() or ""
            non_empty_lines = [
                line.strip()
                for line in raw_text.splitlines()
                if line.strip()
            ]
            pages.append(PageText(
                page_number=page.page_number - 1,  # pdfplumber is 1-based; convert to 0-based
                text=raw_text,
                lines=non_empty_lines,
            ))

    return pages


def get_page_count(pdf_path: Path) -> int:
    """
    Return the total number of pages in a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Total page count as an integer.

    Raises:
        FileNotFoundError: If the PDF does not exist at pdf_path.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: '{pdf_path}'.")

    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


def render_page_as_image(pdf_path: Path, page_number: int, output_path: Path) -> Path:
    """
    Render a single PDF page as a PNG image file.

    Used to give Claude visual context when text extraction alone is
    insufficient (complex layouts, tables, or embedded diagrams).

    Args:
        pdf_path: Path to the PDF file.
        page_number: Zero-based page index to render.
        output_path: Destination path for the rendered PNG file.

    Returns:
        The path where the PNG was saved.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        IndexError: If page_number exceeds the document's page count.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: '{pdf_path}'.")

    doc = fitz.open(str(pdf_path))

    if page_number >= len(doc):
        raise IndexError(
            f"Page {page_number} does not exist in '{pdf_path.name}' "
            f"(document has {len(doc)} pages, zero-indexed)."
        )

    page = doc[page_number]

    # Scale from PDF's native 72 DPI to the configured render DPI
    zoom = PDF_RENDER_DPI / 72
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(output_path))

    doc.close()
    return output_path


def extract_images_from_page(pdf_path: Path, page_number: int) -> list[bytes]:
    """
    Extract all embedded images from a single PDF page.

    Used to preserve diagrams and figures during compaction so they
    can be referenced in the compacted markdown output.

    Args:
        pdf_path: Path to the PDF file.
        page_number: Zero-based page index.

    Returns:
        List of raw image byte sequences found on the page.
        Returns an empty list if the page contains no embedded images.

    Raises:
        FileNotFoundError: If the PDF does not exist.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: '{pdf_path}'.")

    doc = fitz.open(str(pdf_path))
    page = doc[page_number]
    extracted: list[bytes] = []

    # get_images(full=True) returns a list of image reference tuples.
    # The first element of each tuple (xref) is the image's cross-reference ID.
    for image_ref in page.get_images(full=True):
        xref = image_ref[0]
        base_image = doc.extract_image(xref)
        extracted.append(base_image["image"])

    doc.close()
    return extracted
