# math-worksheet-generation-from-source-design.md

**Feature:** math_worksheet_generation_from_source
**Version:** v2
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
  └── Compute bounding box (y-top, y-bottom) for each question block
      (block = stem + diagram/graph + answer choices, indivisible)
    │
    ▼
block_extractor.py
  └── Crop each question block region from rendered page images
      (tight crop, zero padding added)
    │
    ▼
pdf_packer.py
  ├── Place blocks sequentially, top-to-bottom, zero gap between blocks
  ├── Start new page when block would overflow
  └── Blocks that exceed full page height → placed alone on their own page
    │
    ▼
reporter.py
  └── Generate source-boundary-map.md + compaction-report.md
    │
    ▼
Artifacts: source-boundary-map.md | compacted-source.pdf | compaction-report.md
```

**What is intentionally absent:** no `stripper.py`, no `compactor.py`, no Markdown intermediate, no Pandoc. Text is never re-rendered.

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

**Open questions:**
- Should the orchestrator be CLI-driven (`python orchestrator.py --mode compact_source --pdf path`) or API-driven?
- What DPI should be used for page rendering? 150 DPI is the minimum for readability; 200–300 DPI gives sharper output at the cost of file size.
