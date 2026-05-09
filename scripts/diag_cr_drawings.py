"""Check drawings on Q36/Q37/Q38 pages to find what is blocking the gap check."""
import fitz

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"
doc = fitz.open(pdf_path)

for pg_idx in [21, 22, 23, 24, 25]:
    page = doc[pg_idx]
    drawings = page.get_drawings()
    print(f"\nPage {pg_idx+1} (0-based {pg_idx}) — {len(drawings)} drawings")
    for d in drawings:
        rect = d.get("rect")
        fill = d.get("fill")
        color = d.get("color")
        width = d.get("width", 0)
        if rect:
            h = rect.y1 - rect.y0
            w = rect.x1 - rect.x0
            white = fill is not None and all(ch >= 0.95 for ch in fill[:3])
            print(f"  y=[{rect.y0:.1f},{rect.y1:.1f}]  h={h:.1f}  w={w:.1f}  fill={fill}  color={color}  white={white}")

doc.close()
