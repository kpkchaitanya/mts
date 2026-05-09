"""Diagnostic: scan all pages for standalone sidebar question numbers."""
import pdfplumber
import re
from pathlib import Path

pdf_path = Path("docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf")
NY_NUM = re.compile(r"^\s*(\d{1,2})\s*$")

found = {}
with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    for page_idx, page in enumerate(pdf.pages):
        words = page.extract_words()
        lines = {}
        for w in words:
            k = round(float(w["top"]))
            lines.setdefault(k, []).append(w["text"])
        sorted_lines = [(k, " ".join(v)) for k, v in sorted(lines.items())]
        for i, (y, text) in enumerate(sorted_lines):
            m = NY_NUM.match(text)
            if m:
                n = int(m.group(1))
                if 1 <= n <= 45:
                    prev = sorted_lines[i - 1][1][:50] if i > 0 else ""
                    found.setdefault(n, []).append((page_idx, y, prev))

print("Standalone sidebar question numbers found (Q1-Q45):")
for n in sorted(found):
    for page_idx, y, prev in found[n]:
        print(f"  Q{n:2d}: page {page_idx:2d}, y={y:4d}, stem above: \"{prev}\"")

missing = [n for n in range(1, 29) if n not in found]
print(f"\nMissing from Q1-Q28: {missing}")

# Also dump pages 1-8 fully to find Q1-Q4
print("\n--- Pages 1-8 full line dump ---")
with pdfplumber.open(pdf_path) as pdf:
    for page_idx in range(1, 9):
        page = pdf.pages[page_idx]
        words = page.extract_words()
        if not words:
            print(f"Page {page_idx}: (blank)")
            continue
        lines = {}
        for w in words:
            k = round(float(w["top"]))
            lines.setdefault(k, []).append(w["text"])
        print(f"\nPage {page_idx}:")
        for k, v in sorted(lines.items()):
            print(f"  y={k:4d}: {' '.join(v)}")
