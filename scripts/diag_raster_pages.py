"""Check pages 3, 8, 16 (0-based) to identify which are instruction pages vs question pages."""
import fitz

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"
doc = fitz.open(pdf_path)

for idx in [3, 6, 8, 15, 16]:
    page = doc[idx]
    images = page.get_image_info()
    text = page.get_text("text").strip()
    print(f"\nPage {idx} (1-based: {idx+1})")
    print(f"  Images: {len(images)}")
    for img in images:
        print(f"    bbox={img['bbox']}  size={img['width']}x{img['height']}")
    print(f"  Text (first 200 chars): {text[:200]!r}")

doc.close()
