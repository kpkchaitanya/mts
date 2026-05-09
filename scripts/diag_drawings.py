"""Check what drawings are on pages 11, 12, 13 and their y extents."""
import fitz
from pathlib import Path

pdf_path = Path("docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf")
doc = fitz.open(str(pdf_path))

for page_idx in [11, 12, 13]:
    page = doc[page_idx]
    drawings = page.get_drawings()
    print(f"\nPage {page_idx}: {len(drawings)} drawings")
    # Summarise by y range
    for i, d in enumerate(drawings[:30]):
        rect = d.get("rect")
        if rect:
            print(f"  [{i:2d}] y0={rect.y0:.1f} y1={rect.y1:.1f} w={rect.width:.1f} h={rect.height:.1f} fill={d.get('fill')} stroke={d.get('color')}")

doc.close()
