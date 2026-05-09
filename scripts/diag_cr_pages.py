"""Dump pdfplumber words for pages 20-26 (0-based) to debug CR trimming."""
import pdfplumber

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for pg_idx in range(20, 27):
        page = pdf.pages[pg_idx]
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        print(f"\n{'='*60}")
        print(f"PAGE {pg_idx+1} (0-based {pg_idx})  {page.width:.0f}x{page.height:.0f} pts  words={len(words)}")
        print(f"{'='*60}")
        for w in words:
            print(f"  y={w['top']:6.1f}  x0={w['x0']:5.1f}  text={w['text']!r}")
