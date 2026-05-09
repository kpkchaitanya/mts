"""Diagnostic: inspect page 7 (0-based idx 6) with PyMuPDF to see why pdfplumber extracts 0 words."""
import fitz

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"

doc = fitz.open(pdf_path)
page = doc[6]  # page 7 (1-based)

print(f"Page size: {page.rect}")
print()

# Text blocks
print("--- fitz get_text('blocks') ---")
for b in page.get_text("blocks"):
    print(f"  bbox={b[:4]}  type={b[6]}  text={b[4][:80]!r}")

print()
print("--- fitz get_text('words') ---")
for w in page.get_text("words"):
    print(f"  y={w[1]:6.1f}  x0={w[0]:6.1f}  text={w[4]!r}")

print()
print("--- Images ---")
for img in page.get_images(full=True):
    print(f"  {img}")

print()
print("--- Image info ---")
for info in page.get_image_info():
    print(f"  {info}")

print()
print("--- Drawings count ---")
drawings = page.get_drawings()
print(f"  {len(drawings)} drawings")
for d in drawings[:5]:
    print(f"  rect={d.get('rect')}  fill={d.get('fill')}  color={d.get('color')}")

doc.close()
