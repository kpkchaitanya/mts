"""Check compressed image sizes and pixel stats for all 0-word raster pages."""
import fitz
from pathlib import Path

pdf_path = "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf"

import pdfplumber
doc = fitz.open(pdf_path)
with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"{'Page':>5} {'Words':>6} {'ImgSz(KB)':>10} {'PixelStd':>10}")
    print("-" * 40)
    for idx in range(total_pages):
        words = pdf.pages[idx].extract_words()
        word_count = len(words)
        fitz_page = doc[idx]
        images = fitz_page.get_image_info()
        if word_count == 0 and images:
            img_info = images[0]
            size_kb = img_info.get('size', 0) / 1024
            # Render a small thumbnail to check pixel sstd-dev
            clip = fitz.Rect(100, 100, 512, 692)  # center crop
            mat = fitz.Matrix(0.25, 0.25)  # 25% scale for speed
            pm = fitz_page.get_pixmap(matrix=mat, clip=clip)
            samples = pm.samples
            if samples:
                import statistics
                vals = list(samples)
                std = statistics.stdev(vals) if len(vals) > 1 else 0
            else:
                std = 0
            print(f"{idx+1:>5} {word_count:>6} {size_kb:>10.1f} {std:>10.1f}")
doc.close()
