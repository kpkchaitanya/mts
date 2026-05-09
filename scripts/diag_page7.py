"""Diagnostic: dump all words on pages 6-8 (0-based 5-7) of NY 2023 Grade 4."""
import pdfplumber

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for pg_idx in range(5, 9):  # pages 6-9 (1-based)
        page = pdf.pages[pg_idx]
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        print(f"\n{'='*60}")
        print(f"PAGE {pg_idx+1} (0-based idx {pg_idx})  {page.width:.0f}x{page.height:.0f} pts")
        print(f"{'='*60}")
        for w in words:
            print(f"  y={w['top']:6.1f}  x0={w['x0']:6.1f}  text={w['text']!r}")
