# math-worksheet-generation-from-source-design.md

**Feature:** math_worksheet_generation_from_source
**Version:** v3
**Status:** Active

---

## 1. Design Summary

This feature operates in two modes:

| Mode | What it does |
|------|-------------|
| `compact_source` | Takes a source worksheet PDF, visually extracts each question block as a cropped region, and packs them back-to-back with zero gaps to minimize printed pages — no text re-rendering |
| `generate_worksheet` | Generates curriculum-aligned MTS worksheets from a source document using an 8-agent AI pipeline |

**Key design decisions:**
- Python is the primary language — best ecosystem for both PDF processing and AI/LLM work
- No heavy agent frameworks (AutoGen, CrewAI, LangChain) — the pipeline is precisely spec'd; a custom lightweight orchestrator is cleaner
- `compact_source` uses **visual block extraction** (not text parsing + re-rendering) — preserves math symbols, graphs, and diagrams pixel-faithfully
- `generate_worksheet` uses Markdown as the intermediate format — consistent with the existing `.agent/` system
- Claude API is used for AI reasoning in `generate_worksheet` — concept extraction, question generation, QA validation
- Claude vision (or pdfplumber coordinates) used for question block boundary detection in `compact_source`
- File-based artifact storage — consistent with `.agent/evals/runs/` pattern; no database needed at this stage
- `pdf_packer.py` supports 1- and 2-column layout; scale is recalibrated to column width
- `max_pages` drives auto-scale computation; adaptive per-column gap-fill keeps scale variance within 20–30% of base
- Image mode is current default; text mode is a future extension point

### Why visual extraction for `compact_source`

Parsing question content into Markdown and re-rendering it as PDF introduces **rendering inconsistency**: math symbols (fractions, exponents, radicals), coordinate graphs, geometric figures, and tables cannot be reliably reconstructed from raw text extraction. Any re-rendering step risks broken symbols and degraded layouts.

The correct approach: **treat each question block as a rectangular crop of the original rendered PDF page**. Crop it exactly as-is; pack crops tightly onto new pages. No content is re-interpreted, no re-rendering occurs. The output is visually identical to the source.

---

## 2. Design Visualization

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MTS System                           │
│                                                             │
│   ┌──────────────┐         ┌──────────────────────────┐    │
│   │ compact_     │         │   generate_worksheet     │    │
│   │ source mode  │         │   mode (8-agent pipeline)│    │
│   └──────┬───────┘         └────────────┬─────────────┘    │
│          │                              │                   │
│   ┌──────▼───────┐         ┌────────────▼─────────────┐    │
│   │ orchestrator │         │      orchestrator        │    │
│   └──────┬───────┘         └────────────┬─────────────┘    │
│          │                              │                   │
│   ┌──────▼───────────────────────────── ▼─────────────┐    │
│   │              Claude API (claude-sonnet-4-6)        │    │
│   │         Vision | Tool Use | Structured Output      │    │
│   └───────────────────────────────────────────────────┘    │
│                                                             │
│   ┌───────────────────┐   ┌───────────────────────────┐    │
│   │  PyMuPDF          │   │  .agent/evals/runs/        │    │
│   │  pdfplumber       │   │  (artifact storage)        │    │
│   └───────────────────┘   └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### `compact_source` Pipeline

```
Input PDF
    │
    ▼
page_renderer.py
  └── Render each page to high-res image (≥150 DPI) via PyMuPDF
    │
    ▼
block_detector.py
  ├── Extract text + y-coordinates via pdfplumber
  ├── Locate question number markers (Q1 … Qn)
    └── Compute tight bounding box per block:
                top    = question number y_top − BLOCK_TOP_PADDING
                bottom = last answer choice y_bottom + BLOCK_BOTTOM_PADDING
            (no page headers or footers included in any crop)
        - If a block spans a page boundary, any trailing empty page-space or footer rows at the bottom of a slice must be detected and trimmed so the combined block image contains no large blank regions. Trimming should remove continuous near-white rows at slice bottoms while preserving all visual content (diagrams, answer choices, symbols).
    │
    ▼
block_extractor.py
  └── Crop each question block region from rendered page images
      (tight crop: Q# top → last answer choice bottom)
      - When combining multi-slice blocks, the extractor trims trailing whitespace/footer rows from slice bottoms so the final combined image is compact and free of large blank bands.
    │
    ▼
pdf_packer.py  ← redesigned
    ├── Compute column_width (full content width if columns=1; half if columns=2)
    ├── Implements multi-block gap-fill (bounded lookahead) and uniform column shrink to eliminate large leftover gaps: try pulling in a small set of next blocks by uniformly downscaling within the allowed tolerance; if that fails, attempt a uniform shrink of the current column to fill space before advancing.
  ├── Compute base_scale from scale_factor and/or max_pages
  ├── Place blocks left-column-first, top-to-bottom, then right column, then next page
  ├── Zero gap between consecutive blocks within a column
  ├── After each column closes: run gap-fill pass (see packing algorithm below)
  └── Very tall blocks (> one column height): scale down to fit; never split
    │
    ▼
reporter.py
  └── Generate source-boundary-map.md + compaction-report.md
    │
    ▼
Artifacts: source-boundary-map.md | compacted-source.pdf | compaction-report.md
    - Optional QA: `comparison_report.json` + per-page diff images when a golden sample is supplied. The comparator component is implemented in `compact_source/comparator.py` and performs pixel-based diffs and blank-band detection to aid human review.
```

**What is intentionally absent:** no `stripper.py`, no `compactor.py`, no Markdown intermediate, no Pandoc. Text is never re-rendered.

### Packing Algorithm (pdf_packer.py)

#### 1. Scale Computation

```
column_width = (content_width - column_gap) / 2   if columns == 2
             = content_width                        if columns == 1

if max_pages is given:
    target_area = max_pages × column_height × columns
    auto_scale  = target_area / sum(block.total_height_pts for all blocks)
else:
    auto_scale  = None

base_scale = min(scale_factor/100, auto_scale)  if both given
           = scale_factor/100                    if only scale_factor
           = auto_scale                          if only max_pages
           = 1.0                                 if neither given

# Never upscale beyond natural fit (block fills column width at 1.0)
# natural_scale = column_width / block.source_width_pts  (per block)
# effective_scale = min(base_scale, natural_scale)       (per block)
```

#### 2. Placement Loop

```
For each column slot on each page:
    col_y = margin_top
    column_blocks = []

    For each block (in question order):
        effective_scale = min(base_scale, column_width / block.source_width_pts)
        scaled_h = block.total_height_pts × effective_scale

        if scaled_h > column_height:
            # Block taller than one full column — force-fit
            effective_scale = column_height / block.total_height_pts
            scaled_h = column_height

        if col_y + scaled_h > column_bottom:
            # Block won't fit — close this column, run gap-fill, advance
            run_gap_fill(column_blocks, col_y, base_scale)
            advance to next column (or new page if on last column)
            col_y = margin_top
            column_blocks = []

        place block at (col_x, col_y) with size (scaled_w, scaled_h)
        column_blocks.append(block)
        col_y += scaled_h   # zero gap between blocks
```

#### 3. Gap-Fill Pass (per column, after closing)

```
gap = column_height - sum(scaled heights of column_blocks)

GAP_THRESHOLD = 40 pts  (~5 text lines)
MAX_SCALE_REDUCTION = 0.25  (25% below base_scale; configurable 20–30%)

if gap > GAP_THRESHOLD and next_block exists:
    # Try to pull in the next block by uniformly scaling down this column
    total_h = sum(block.total_height_pts for block in column_blocks)
    next_h  = next_block.total_height_pts
    needed_scale = column_height / (total_h + next_h)

    min_allowed_scale = base_scale × (1 - MAX_SCALE_REDUCTION)

    if needed_scale >= min_allowed_scale:
        # Within tolerance — re-scale all blocks in this column and pull in next block
        rescale column_blocks to needed_scale
        place next_block at new col_y with needed_scale
        advance col_y; add next_block to column_blocks
    else:
        # Gap is too large to fill without over-shrinking — accept the gap
        pass
```

#### 4. Two-Column Layout

```
Page layout:
  ┌─────────────────────────────────┐
  │ margin                          │
  │  ┌──────────┐  gap ┌──────────┐ │
  │  │  Col 0   │      │  Col 1   │ │
  │  │  (left)  │      │ (right)  │ │
  │  └──────────┘      └──────────┘ │
  │ margin                          │
  └─────────────────────────────────┘

column_gap = 12 pts  (configurable)
column_width = (content_width - column_gap) / 2
col_x[0] = margin
col_x[1] = margin + column_width + column_gap

Advance order: Col 0 → Col 1 → new page Col 0 → Col 1 → …
```

### `generate_worksheet` Pipeline

```
request.json
    │
    ▼
[1] intake-agent        → request.json (validated)
    │
    ▼
[2] source-extractor    → source-extract.md
    │
    ▼
[3] concept-mapper      → concept-map.md
    │
    ▼
[4] worksheet-planner   → plan.md
    │
    ▼
[5] question-generator  → worksheet-draft.md
    │
    ▼
[6] answer-key-agent    → answer-key-draft.md
    │
    ▼
[7] qa-agent            → qa-report.md
    │         │
    │    FAIL └──► loop back to [5] or [3] (max 2 retries)
    │
    ▼ PASS
[8] formatter-agent     → worksheet-final.md
```

---

## 3. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Best PDF + AI ecosystem |
| PDF rendering (pages → images) | PyMuPDF (fitz) `page.get_pixmap()` | Renders PDF pages at any DPI; provides the source images for block cropping |
| Block boundary detection (text + coords) | pdfplumber | Accurate x/y coordinate extraction for locating question number markers; used only for bounding box calculation, not for content extraction |
| Block cropping | PyMuPDF `page.get_pixmap(clip=rect)` | Crops exact rectangular regions from rendered pages; output is a pixel-faithful image of the original |
| PDF assembly (pack image blocks → PDF) | PyMuPDF `Document` + `Page.insert_image()` | Inserts cropped block images into new PDF pages with precise placement; no external tool needed |
| AI / LLM | Anthropic SDK → `claude-sonnet-4-6` | Used in `generate_worksheet` mode (concept extraction, question generation, QA); optionally used in `compact_source` for ambiguous block boundary resolution |
| Agent orchestration | Custom Python (no framework) | Pipeline is precisely spec'd; lightweight custom is simpler and cleaner |
| Intermediate format | Markdown (for `generate_worksheet` only) | Consistent with existing `.agent/` system; not used in `compact_source` |
| Config management | python-dotenv | API keys and paths via `.env`; never hardcoded |
| Testing | pytest | Unit + integration tests |

**Removed from stack:**
- ~~Pandoc~~ — was needed to convert Markdown → PDF; no longer required since `compact_source` outputs PDF directly via image packing

---

## 4. File Structure

```
mts/
├── src/
│   ├── orchestrator.py                  ← entry point; routes to correct mode pipeline
│   ├── config.py                        ← loads env vars, constants (no magic numbers)
│   ├── compact_source/
│   │   ├── __init__.py
│   │   ├── page_renderer.py             ← renders PDF pages to high-res pixmaps (PyMuPDF)
│   │   ├── block_detector.py            ← locates question block bounding boxes (pdfplumber y-coords)
│   │   ├── block_extractor.py           ← crops block regions from rendered page images (PyMuPDF clip)
│   │   ├── pdf_packer.py                ← packs cropped blocks into new PDF pages (PyMuPDF insert_image)
│   │   └── reporter.py                  ← generates source-boundary-map.md + compaction-report.md
│   ├── generate_worksheet/
│   │   ├── __init__.py
│   │   ├── intake.py                    ← validates + normalizes request
│   │   ├── source_extractor.py          ← cleans source, identifies examples
│   │   ├── concept_mapper.py            ← extracts concepts (source only)
│   │   ├── planner.py                   ← maps concepts to question distribution
│   │   ├── question_generator.py        ← generates questions by type
│   │   ├── answer_key.py                ← derives answers independently
│   │   ├── qa.py                        ← validates correctness + fidelity; has veto
│   │   └── formatter.py                 ← formats approved content only
│   └── utils/
│       ├── __init__.py
│       ├── pdf_utils.py                 ← shared PDF helpers (PyMuPDF + pdfplumber)
│       ├── claude_client.py             ← shared Anthropic API client wrapper
│       ├── artifact_writer.py           ← writes run artifacts to correct folder
│       └── markdown_utils.py            ← shared markdown helpers
├── tests/
│   ├── compact_source/
│   └── generate_worksheet/
├── .env.example                         ← template for required env vars
├── requirements.txt
└── README.md
```

---

## 5. Dependencies

```
# requirements.txt
anthropic>=0.40.0        # Claude API — LLM, vision, tool_use
pymupdf>=1.24.0          # PDF image/diagram extraction, page geometry
pdfplumber>=0.11.0       # Position-aware text extraction (x/y coords)
python-dotenv>=1.0.0     # .env config loading
pytest>=8.0.0            # Testing

# System dependency (install separately)
# pandoc — markdown → print-ready PDF output
# Install: https://pandoc.org/installing.html
```

---

## 6. Tasks

### Phase 1 — Foundation
- [ ] Set up `src/` folder structure
- [ ] Create `config.py` with env var loading
- [ ] Create `utils/claude_client.py` — shared Claude API wrapper
- [ ] Create `utils/artifact_writer.py` — run folder creation and artifact writing
- [ ] Create `.env.example`
- [ ] Create `requirements.txt`

### Phase 2 — `compact_source` Mode
- [ ] `utils/pdf_utils.py` — shared PDF helpers (PyMuPDF + pdfplumber wrappers)
- [ ] `compact_source/page_renderer.py` — render PDF pages to pixmaps at target DPI
- [ ] `compact_source/block_detector.py` — extract text y-coords, compute question block bounding boxes
- [ ] `compact_source/block_extractor.py` — crop block regions from rendered page images
- [ ] `compact_source/pdf_packer.py` — pack cropped blocks into new PDF pages, zero gap, page overflow handling
- [ ] `compact_source/reporter.py` — generate source-boundary-map.md + compaction-report.md
- [ ] Integration test with a real source worksheet PDF

### Phase 3 — `generate_worksheet` Mode
- [ ] `generate_worksheet/intake.py`
- [ ] `generate_worksheet/source_extractor.py`
- [ ] `generate_worksheet/concept_mapper.py`
- [ ] `generate_worksheet/planner.py`
- [ ] `generate_worksheet/question_generator.py`
- [ ] `generate_worksheet/answer_key.py`
- [ ] `generate_worksheet/qa.py` (with loopback logic)
- [ ] `generate_worksheet/formatter.py`
- [ ] Integration test: source → all 8 artifacts → QA pass

### Phase 4 — Orchestrator + Tests
- [ ] `orchestrator.py` — routes by mode, runs full pipeline
- [ ] Unit tests for each module
- [ ] Eval run against `.agent/evals/eval.md` framework

---

## 7. Clarifications

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | No heavy agent framework | Pipeline is deterministic and precisely spec'd; custom orchestrator keeps full control |
| 2 | Visual block extraction instead of text parsing + re-render | Re-rendering math content from raw text introduces symbol and layout inconsistency; cropping the original rendered image is the only reliable way to preserve fidelity |
| 3 | PyMuPDF for rendering + cropping | `get_pixmap()` renders at any DPI; `get_pixmap(clip=rect)` crops exact regions; `insert_image()` packs them into a new PDF — all in one library, no extra tools |
| 4 | pdfplumber for boundary detection only | pdfplumber gives accurate y-coordinates for text runs; used only to locate question number markers — not for extracting content |
| 5 | Pandoc removed | Was only needed for Markdown → PDF conversion; no longer required since output PDF is assembled directly from image blocks |
| 6 | Claude vision optional in `compact_source` | Used only for ambiguous cases (e.g., question marker not detectable by text coords); pdfplumber handles the standard case |
| 7 | File-based artifacts | Consistent with existing system; simple to inspect, debug, and trace |
| 8 | Max 2 QA retries (`generate_worksheet`) | Spec mandates loopback; 2 retries before escalation balances quality and cost |
| 9 | `max_pages` = total output page target | Drives auto-scale computation; `max_block_pages` (internal safety cap per block) is kept as a separate internal constant |
| 10 | Columns=1 default, columns=2 optional | Single-column is the baseline; 2-column halves the column width and recalibrates scale accordingly |
| 11 | Gap-fill tolerance = 20–30% below base scale | Prevents unreadable output while still eliminating large whitespace gaps; gap is accepted if next block would require over-shrinking beyond the tolerance |
| 12 | Image mode is current default; text mode deferred | Text mode requires reliable math symbol extraction — not feasible until a later phase |
| 13 | Tight crop: Q# top → last answer choice bottom | Source page headers and footers must never appear in a block crop; this is enforced in block_detector boundaries |

**Resolved questions:**
- Orchestrator is CLI-driven (`python -m src.orchestrator compact_source --pdf path --grade n ...`)
- DPI: 150 DPI default (configurable via `PDF_RENDER_DPI` env var)
