"""
pdf_renderer.py

Renders a markdown document to a PDF file using PyMuPDF (fitz.Story).
Converts markdown -> HTML -> PDF for clean, print-ready output.
"""

from pathlib import Path

import fitz
import markdown as md_lib


_CSS = """
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #000000;
}
h1 { font-size: 14pt; font-weight: bold; margin-top: 0; margin-bottom: 6pt; }
h2 { font-size: 12pt; font-weight: bold; margin-bottom: 4pt; }
p  { margin: 4pt 0; }
hr { margin: 8pt 0; }
strong { font-weight: bold; }
table  { border-collapse: collapse; width: 100%; margin: 6pt 0; }
td, th { border: 1px solid #888; padding: 3pt 6pt; font-size: 10pt; }
th     { font-weight: bold; background-color: #eeeeee; }
ul, ol { margin: 4pt 0; padding-left: 20pt; }
li     { margin-bottom: 2pt; }
pre, code { font-family: Courier, monospace; font-size: 10pt; }
"""

_LETTER = fitz.paper_rect("letter")   # 612 x 792 pt
_MARGIN = 54                           # 0.75 inch margins on all sides
_WHERE  = _LETTER + (_MARGIN, _MARGIN, -_MARGIN, -_MARGIN)


def render_markdown_to_pdf(markdown_content: str, output_path: Path) -> Path:
    """
    Convert a markdown string to a PDF file at output_path.

    Args:
        markdown_content: Full markdown text to render.
        output_path: Destination path for the PDF (created or overwritten).

    Returns:
        The output_path, confirmed written.
    """
    html_body = md_lib.markdown(markdown_content, extensions=["tables", "nl2br"])
    html = f"<html><body>{html_body}</body></html>"

    story = fitz.Story(html=html, user_css=_CSS)
    writer = fitz.DocumentWriter(str(output_path))

    more = True
    while more:
        device = writer.begin_page(_LETTER)
        more, _ = story.place(_WHERE)
        story.draw(device)
        writer.end_page()

    writer.close()
    return output_path
