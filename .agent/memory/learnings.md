# learnings.md — MTS System Learnings Log

**Purpose:** Capture lessons learned from runs, design iterations, and failures. Use these to improve specs, evals, agents, and workflows.

---

## Learnings Log

| # | Date | Source | Learning | Applied To |
|---|------|--------|----------|------------|
| 6 | 2026-04-26 | Run 20260426_155629 | Answer key sections ("Answer Key" header + tabular rows matching question number regex) are detected as question blocks when no format fence is in place. Must detect and stop before answer key pages. | `block_detector.py` — `_find_answer_key_fence()` added |
| 5 | 2026-04-26 | Run 20260426_160645 | Section-break notice pages ("The first section of the test ends here.", 8 words) were included as image-heavy question blocks. `IMAGE_HEAVY_PAGE_MAX_WORDS` must be ≤ 5 to exclude them. | `block_detector.py` — threshold lowered to 5 |
| 4 | 2026-04-26 | Run 20260426_160645 | Blank pages (0 words) inside content sections (before fence) must be excluded from image-heavy blocks. Condition must be `0 < word_count <= threshold`, not `word_count <= threshold`. | `block_detector.py` — `_detect_image_heavy_blocks()` |
| 3 | 2026-04-26 | Design analysis | EOG 2014 PDFs embed one question per page as a raster image with only a page-counter footer ("N of M", 3 words). pdfplumber extracts nothing useful from question pages. The text-rich detection path is the wrong strategy for this format entirely. | `block_detector.py` — `_classify_format()` + `_detect_image_heavy_blocks()` |
| 2 | 2026-04-26 | Run 20260426_162003 | Output PDF was 73 MB at 150 DPI because raster PNG blocks are uncompressed by default in PyMuPDF. Switching to 96 DPI + `deflate=True, garbage=4` brought it to ~1 MB for 12 pages. | `config.py`, `.env`, `pdf_packer.py` |
| 1 | 2026-04-26 | Design session | `--grade` and `--subject` flags are metadata labels only — they have zero effect on pipeline processing. Making them required was a usability tax with no benefit. | `orchestrator.py`, `compact_source.prompt.md` |

---

## Learning Template

```
| # | YYYY-MM-DD | <run-id or design session> | <what was learned> | <spec / eval / agent / workflow> |
```

---

## Categories

Use these tags to classify learnings:

- `spec` — gaps or ambiguities in a spec
- `eval` — missing or weak evaluation criteria
- `agent` — agent behavior that drifted or failed
- `workflow` — sequencing or handoff issues
- `format` — output formatting problems
- `correctness` — mathematical or factual errors caught
- `pedagogy` — content quality issues
