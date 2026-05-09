# qa-scenarios.md — Functional QA Scenarios: compact_source_math

**Feature:** `compact_source_math`  
**Version:** v1  
**Date:** 2026-05-08  
**Status:** Active  
**Authority:** Enforced by IMP-022 and `agent.md` §8. **Must be run automatically after every generation run.** The agent must triage all failures by priority and iterate fixes until all P1 and P2 scenarios pass before reporting the run complete. See `agent.md` §8 for the full post-generation QA loop, priority assignment, and escalation rules.

---

## How to Use This Document

Run the scenarios in order after any code change. For each scenario:
- Execute the listed command or code check
- Compare actual output to the Expected Result
- Mark **PASS** or **FAIL**
- A single FAIL blocks the change from being closed

**Reference inputs** (today's folder):
- `docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade3_2023_Released_Test_Questions.pdf` — 29 pages, 22 blocks
- `docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf` — 32 pages, 27 blocks
- `docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade5_2023_Released_Test_Questions.pdf` — 32 pages, 20 blocks

---

## Stage 1 — Block Detection

### QA-DET-01: Correct block count, Grade 3

**Command:**
```powershell
python scripts/compact_runner.py --inputs "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade3_2023_Released_Test_Questions.pdf" --grade 3 --subject Math --columns 2
```

**Check:** `[MTS] N question blocks detected` line in output.

**Expected:** `22 question blocks detected`  
**Pass criterion:** Exact match ± 0. Any count below 18 or above 26 is a FAIL.

---

### QA-DET-02: Correct block count, Grade 4

**Command:** Same as QA-DET-01 but Grade 4 PDF, `--grade 4`.

**Expected:** `27 question blocks detected`  
**Pass criterion:** Exact match ± 0. Any count below 22 or above 32 is a FAIL.

---

### QA-DET-03: Correct block count, Grade 5

**Command:** Same as QA-DET-01 but Grade 5 PDF, `--grade 5`.

**Expected:** `20 question blocks detected`  
**Pass criterion:** Exact match ± 0. Any count below 16 or above 24 is a FAIL.

---

### QA-DET-04: No vision fallback used

**Check:** Confirm `vision fallback used` does NOT appear in the output for any of the 3 grade files.

**Expected:** No vision fallback line.  
**Pass criterion:** Zero occurrences of `vision fallback` in run.log.

---

### QA-DET-05: No cover or session heading pages in output (BUG-011 regression)

Verifies that no test cover page or session heading page was included as a block. These pages have Q#=0 in the boundary map and appear as the first block in the output PDF. This is a regression test for BUG-011.

**Code check (run after a batch):**
```python
from pathlib import Path
import re

run_folder = sorted(
    p for p in Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir()
    if p.is_dir()
)[-1]
log = (run_folder / "run.log").read_text(encoding="utf-8", errors="replace")

# Find all rows in boundary map tables that have Q#=0
# Table row format: | 0 | <page> | ...
zero_q_pattern = re.compile(r"\|\s*0\s*\|\s*(\d+)\s*\|")
matches = zero_q_pattern.findall(log)

if matches:
    print(f"FAIL  {len(matches)} Q#=0 block(s) found on pages: {matches}")
    print("      These are likely cover/session heading pages included in error (BUG-011).")
else:
    print("PASS  No Q#=0 blocks in boundary map (no cover pages in output)")
```

**Expected:** Zero Q#=0 entries in any grade's boundary map.  
**Pass criterion:** Output is `PASS`. Any Q#=0 block is a FAIL — it means a non-question page was included.  
**Priority:** P2 until BUG-011 is resolved, then confirms the fix holds.

---

## Stage 2 — Block Extraction

### QA-EXT-01: Extracted block count matches detected count

**Check:** `N block images extracted` equals `N question blocks detected` for each file.

**Expected:** Numbers are equal for all 3 grades.  
**Pass criterion:** No mismatch between detected and extracted counts.

---

### QA-EXT-02: Image resolution confirms DPI setting

**Code check (run after a batch):**
```python
import fitz
from pathlib import Path

run_folder = sorted(Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir())[-1]
pdf = next(run_folder.glob("*Grade5*2col*.pdf"))
doc = fitz.open(str(pdf))
img = doc[0].get_images(full=True)[0]
pix = fitz.Pixmap(doc, img[0])
print(f"Width: {pix.width} px")
assert pix.width >= 1200, f"FAIL: image too narrow ({pix.width}px) — DPI setting not applied"
print("PASS")
```

**Expected:** Width ≥ 1200 px (at 200 DPI on letter page = 1700 px).  
**Pass criterion:** Assertion does not raise. If width is ~816px the DPI setting is not being applied (check `.env`).

---

### QA-EXT-03: No text cut off at block bottom boundary

Verify that the bottom rows of each extracted block image are background (white / near-white), not text. A text-colored bottom edge means the block boundary was drawn too tight and content is clipped.

**Code check (run after a batch):**
```python
import fitz
import numpy as np
from pathlib import Path

run_folder = sorted(
    p for p in Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir()
    if p.is_dir()
)[-1]

fail_count = 0
for pdf_path in sorted(run_folder.glob("*.pdf")):
    doc = fitz.open(str(pdf_path))
    for page_num in range(len(doc)):
        for img_info in doc[page_num].get_images(full=True):
            xref = img_info[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            # Check bottom 5 rows: mean pixel brightness should be > 230 (near-white)
            bottom_rows = arr[-5:, :, :]
            mean_brightness = bottom_rows.mean()
            if mean_brightness < 230:
                print(f"FAIL  {pdf_path.name} page {page_num} xref {xref}: "
                      f"bottom rows brightness {mean_brightness:.1f} (threshold 230) — possible text cut-off")
                fail_count += 1
    doc.close()

if fail_count == 0:
    print("PASS  all block bottom edges are background (no text cut-off detected)")
else:
    print(f"FAIL  {fail_count} block(s) have suspicious bottom edges — inspect visually")
```

**Expected:** All bottom-row brightness values ≥ 230 (white background).  
**Pass criterion:** Zero FAIL lines. If any block fails, open the PDF and inspect that page visually to confirm whether text is actually clipped.

> **Note:** This check is heuristic. A dark border or shading on the block bottom can produce a false positive. Always confirm visually before filing a bug.

---

### QA-EXT-04: Answer choice bottom boundary regression (BUG-010)

Direct regression test for the two root causes fixed in BUG-010:
- **Bug A:** Detector fence excluded answer choices at exactly `end_y` — fixed by changing `>=` to `>`  
- **Bug B:** Extractor float-rounding trimmed one content row — fixed by keeping 1 safety blank row

Verifies that Q13 (Grade 4) — the worst-case block with 56px of answer choices cut before the fix — now has a correctly extended `y_bottom`, and that the extracted image's last rendered row is blank (not clipped content).

**Code check (requires no Claude API call — detector is called with the source PDF directly):**
```python
import sys, fitz
sys.path.insert(0, ".")
from pathlib import Path
from src.compact_source_math.block_detector import BlockDetector
from src.utils.claude_client import ClaudeClient

client = ClaudeClient()
detector = BlockDetector(client)
pdf_path = Path("docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf")
result = detector.detect(pdf_path)
q13 = next((b for b in result.blocks if b.question_number == 13), None)

# --- Bug A regression: y_bottom must include answer choices ---
# Before fix, y_bottom = 304.2 (exactly where 'A' started — all choices cut)
# After fix, y_bottom must be > 350 to clear the last answer choice row
assert q13 is not None, "FAIL: Q13 not found in detector output"
sl = q13.slices[0]
assert sl.y_bottom > 350, (
    f"FAIL (BUG-010 Bug A regression): Q13 y_bottom={sl.y_bottom:.1f} "
    f"is too low — answer choices likely excluded from boundary"
)
print(f"PASS  Bug A: Q13 y_bottom={sl.y_bottom:.1f} (need >350)")

# --- Bug B regression: last rendered row must be blank after extraction ---
DPI = 200
BLANK_THRESHOLD = 245
zoom = DPI / 72.0
matrix = fitz.Matrix(zoom, zoom)
doc = fitz.open(str(pdf_path))
page = doc[sl.page_number]
clip = fitz.Rect(0, sl.y_top, page.rect.width, sl.y_bottom)
pm = page.get_pixmap(matrix=matrix, clip=clip)
doc.close()

n, w, h = pm.n, pm.width, pm.height
row_stride = w * n
samples = pm.samples
# Check the last row of the rendered image — must be blank after safe_blank_rows trim
# Simulate safe_blank_rows: find blank_rows then subtract 1
blank_rows = 0
for row in range(h-1, max(h-1-int(h*0.5), -1), -1):
    start = row * row_stride
    row_bytes = samples[start:start+row_stride]
    is_blank = all(
        row_bytes[px] >= BLANK_THRESHOLD and row_bytes[px+1] >= BLANK_THRESHOLD and row_bytes[px+2] >= BLANK_THRESHOLD
        for px in range(0, len(row_bytes), n) if n >= 3
    )
    if is_blank:
        blank_rows += 1
    else:
        break
safe = max(0, blank_rows - 1)
trim_pts = safe * 72.0 / DPI
new_bottom_row = int((sl.y_bottom - trim_pts) * zoom)
clamped = min(new_bottom_row, h - 1)
# The row at clamped must be blank (we stopped at first content row, keeping 1 safety blank)
start = clamped * row_stride
row_bytes = samples[start:start+row_stride]
final_row_blank = all(
    row_bytes[px] >= BLANK_THRESHOLD and row_bytes[px+1] >= BLANK_THRESHOLD and row_bytes[px+2] >= BLANK_THRESHOLD
    for px in range(0, len(row_bytes), n) if n >= 3
)
assert final_row_blank, (
    f"FAIL (BUG-010 Bug B regression): last row after safe trim is NOT blank — "
    f"content row being cut off (blank_rows={blank_rows}, safe={safe})"
)
print(f"PASS  Bug B: last row after safe trim is blank (blank_rows={blank_rows}, safe={safe})")
print("PASS  QA-EXT-04 BUG-010 regression")
```

**Expected:** Both assertions pass.  
**Pass criterion:**
- `Q13 y_bottom > 350` — confirms answer choice boundary is inclusive
- Last row after safe trim is blank — confirms no content row is clipped by float-rounding

> If `y_bottom` regresses to ~304, Bug A is back. If the last row assertion fails, Bug B is back. Both must pass on every run.

---

## Stage 3 — PDF Packing

### QA-PACK-01: No infinite loop — all files complete within 60 seconds each

**Check:** Each file's `Runtime: Xs` line in the output.

**Expected:** Runtime ≤ 60s per file.  
**Pass criterion:** All 3 files complete. A hanging process (no output after 60s) is an immediate FAIL — kill and investigate.

---

### QA-PACK-02: 2-col page count is roughly half of 1-col

**Run both:**
```powershell
python scripts/compact_runner.py --inputs "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade5_2023_Released_Test_Questions.pdf" --grade 5 --subject Math --columns 1
python scripts/compact_runner.py --inputs "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade5_2023_Released_Test_Questions.pdf" --grade 5 --subject Math --columns 2
```

**Expected:** 2-col page count ≤ 1-col page count. Typically 2-col is 40–60% of 1-col.  
**Pass criterion:** 2-col pages < 1-col pages. Equal or greater is a FAIL (packing logic broken).

---

### QA-PACK-03: Output PDF is not blank

**Code check:**
```python
import fitz
from pathlib import Path

run_folder = sorted(Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir())[-1]
for pdf in run_folder.glob("*.pdf"):
    doc = fitz.open(str(pdf))
    imgs = doc[0].get_images(full=True)
    assert len(imgs) > 0, f"FAIL: {pdf.name} page 0 has no images"
    print(f"PASS  {pdf.name}: {len(imgs)} images on page 0")
```

**Expected:** Every output PDF has at least 1 image on page 0.  
**Pass criterion:** All assertions pass.

---

### QA-PACK-04: Run folder contains only PDFs and run.log

**Code check:**
```python
from pathlib import Path

run_folder = sorted(Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir())[-1]
files = list(run_folder.iterdir())
unexpected = [f for f in files if f.suffix not in (".pdf", ".log")]
assert not unexpected, f"FAIL: unexpected files in run folder: {[f.name for f in unexpected]}"
print(f"PASS  {len(files)} files: {[f.name for f in files]}")
```

**Expected:** Only `.pdf` files and `run.log`.  
**Pass criterion:** `unexpected` list is empty.

---

### QA-PACK-05: No block split across page boundaries

Blocks are placed as whole images. No block should be partially on one page and continue on the next. Verify by checking that every image in the output PDF has a height-to-width ratio consistent with a complete question block (not a sliver).

**Code check (run after a batch):**
```python
import fitz
from pathlib import Path

run_folder = sorted(
    p for p in Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir()
    if p.is_dir()
)[-1]

fail_count = 0
for pdf_path in sorted(run_folder.glob("*.pdf")):
    doc = fitz.open(str(pdf_path))
    for page_num in range(len(doc)):
        for img_info in doc[page_num].get_images(full=True):
            xref = img_info[0]
            pix = fitz.Pixmap(doc, xref)
            ratio = pix.height / pix.width if pix.width > 0 else 0
            # A valid question block image is taller than it is wide, but not a thin sliver.
            # A ratio < 0.05 means height is < 5% of width — almost certainly a clipped fragment.
            if ratio < 0.05:
                print(f"FAIL  {pdf_path.name} page {page_num} xref {xref}: "
                      f"suspicious aspect ratio {ratio:.3f} (h={pix.height} w={pix.width}) — possible split block")
                fail_count += 1
    doc.close()

if fail_count == 0:
    print("PASS  all block images have plausible aspect ratios (no split blocks detected)")
else:
    print(f"FAIL  {fail_count} image(s) have suspicious aspect ratios")
```

**Expected:** No image has a height-to-width ratio below 0.05.  
**Pass criterion:** Zero FAIL lines. Investigate any flagged image to confirm it is not a partial block.

---

## Stage 4 — Reporting

### QA-REP-01: Result is PASS for all 3 grades

**Check:** `[MTS] Result: PASS` appears for each file in the batch output.

**Expected:** 3× `Result: PASS` in run output.  
**Pass criterion:** Zero `Result: FAIL` lines.

---

### QA-REP-02: Page reduction is plausible

**Check:** `N pages -> M pages` summary line.

**Expected ranges:**
| Grade | Source pages | Max compacted pages |
|-------|-------------|---------------------|
| 3 | 29 | 6 (1-col) / 3 (2-col) |
| 4 | 32 | 8 (1-col) / 4 (2-col) |
| 5 | 32 | 10 (1-col) / 5 (2-col) |

**Pass criterion:** Compacted page count is within the expected range. A compacted count equal to or greater than the source count is a FAIL (no compaction occurred).

---

### QA-REP-03: run.log is non-empty and contains all 3 file sections

**Code check:**
```python
from pathlib import Path

run_folder = sorted(Path(".agent/evals/runs/math_worksheet_generation_from_source").iterdir())[-1]
log = (run_folder / "run.log").read_text(encoding="utf-8")
for grade in ["Grade3", "Grade4", "Grade5"]:
    assert grade in log, f"FAIL: {grade} section missing from run.log"
assert len(log) > 5000, f"FAIL: run.log suspiciously short ({len(log)} chars)"
print(f"PASS  run.log: {len(log):,} chars, all grade sections present")
```

**Expected:** All 3 grade names present, log > 5000 chars.  
**Pass criterion:** All assertions pass.

---

## End-to-End

### QA-E2E-01: Full batch run, all 3 grades, 2-col

**Command:**
```powershell
python scripts/compact_runner.py `
  --inputs `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade3_2023_Released_Test_Questions.pdf" `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade4_2023_Released_Test_Questions.pdf" `
    "docs/exams/2026-EOGs/math/05_08_2026/NY_Math_Grade5_2023_Released_Test_Questions.pdf" `
  --grade 5 --subject Math --columns 2
```

**Expected:**
- Single run folder created
- 3 PDF files + 1 `run.log` in the folder, nothing else
- All 3 files report `PASS`
- Total runtime < 3 minutes
- `Batch complete` summary line printed with all 3 files as PASS

**Pass criterion:** All of the above are true simultaneously.

---

## QA Sign-Off Template

Copy this block into the bug or feature detail in `bugs.md` or `backlog.md` when closing an item:

```
### QA Sign-Off

**Date:** YYYY-MM-DD  
**Run folder:** .agent/evals/runs/math_worksheet_generation_from_source/<run_id>

| Scenario | Result |
|----------|--------|
| QA-DET-01 (G3 block count) | PASS / FAIL |
| QA-DET-02 (G4 block count) | PASS / FAIL |
| QA-DET-03 (G5 block count) | PASS / FAIL |
| QA-DET-04 (no vision fallback) | PASS / FAIL |
| QA-DET-05 (no cover/heading pages, BUG-011) | PASS / FAIL |
| QA-EXT-01 (extracted = detected) | PASS / FAIL |
| QA-EXT-02 (image resolution ≥ 1200px) | PASS / FAIL |
| QA-EXT-03 (no text cut off at block bottom) | PASS / FAIL || QA-EXT-04 (BUG-010 regression: answer boundary + float trim) | PASS / FAIL || QA-PACK-01 (no infinite loop, < 60s) | PASS / FAIL |
| QA-PACK-02 (2-col < 1-col pages) | PASS / FAIL |
| QA-PACK-03 (no blank output) | PASS / FAIL |
| QA-PACK-04 (only PDFs + run.log in folder) | PASS / FAIL |
| QA-PACK-05 (no split blocks) | PASS / FAIL |
| QA-REP-01 (Result: PASS all files) | PASS / FAIL |
| QA-REP-02 (page reduction plausible) | PASS / FAIL |
| QA-REP-03 (run.log complete) | PASS / FAIL |
| QA-E2E-01 (full batch, 3 grades, 2-col) | PASS / FAIL |
```
