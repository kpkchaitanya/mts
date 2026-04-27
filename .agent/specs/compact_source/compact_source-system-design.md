# compact_source — System Design

> **Superseded.** Content merged into [compact_source-design.md](compact_source-design.md) §1–§5.

---

## 1. End-to-End Pipeline

Five stages. Stages 1 and 2 both live in `block_detector.py` — format detection feeds directly into block detection within the same `detect()` call.

```mermaid
flowchart TD
    IN([Source PDF\n.pdf file]) --> V

    subgraph ORCH["orchestrator.py — run_compact_source()"]
        V[Validate input\nfile exists, readable]
    end

    V --> S1

    subgraph S1BOX["Stage 1 — block_detector.py  _classify_format()"]
        S1A[Sample first 10 non-blank pages\ncount words per page]
        S1A --> S1B{avg words/page\n< 10?}
        S1B -->|Yes| S1C[format: image_heavy\nEOG-style]
        S1B -->|No| S1D[format: text_rich\nSTAAR-style]
        S1C --> S1OUT([format detected])
        S1D --> S1OUT
    end

    S1OUT --> S2

    subgraph S2BOX["Stage 2 — block_detector.py  detect()  →  BlockDetectionResult"]
        S2{image_heavy\nor text_rich?}
        S2 -->|image_heavy| S2A[_find_answer_key_fence\n_detect_image_heavy_blocks\none block per content page]
        S2 -->|text_rich| S2B[Regex scan\nQUESTION_LINE_PATTERN\nANSWER_CHOICE_PATTERN]
        S2B -->|< 3 blocks| S2C[Claude Vision Fallback]
        S2A --> S2OUT
        S2B --> S2OUT
        S2C --> S2OUT
        S2OUT[BlockDetectionResult\nlist of QuestionBlock\neach with PageSlice list]
    end

    S2OUT --> S3

    subgraph S3BOX["Stage 3 — block_extractor.py  BlockExtractor.extract()  →  list of ExtractedBlock"]
        S3A[Open PDF once\nfitz.open]
        S3A --> S3B[Render each page\nat PDF_RENDER_DPI = 96]
        S3B --> S3C[Crop PageSlice rect\nfitz clip rect]
        S3C --> S3D[Combine slices\nfor cross-page blocks]
        S3D --> S3OUT[list of ExtractedBlock\npng_bytes + dimensions]
    end

    S3OUT --> S4

    subgraph S4BOX["Stage 4 — pdf_packer.py  PdfPacker.pack()  →  output PDF"]
        S4A[Phase 1 — compute_layout\nassign blocks to columns/pages\nscale to column width]
        S4A --> S4B[Gap-fill attempt\npull next block by downscaling column]
        S4B --> S4C[Phase 2 — render\ninsert PNG images\ninto fitz.Document]
        S4C --> S4D[Save\ndeflate=True, garbage=4]
        S4D --> S4OUT["{stem}_Compacted_Ncol_{run_id}.pdf"]
    end

    S4OUT --> S5

    subgraph S5BOX["Stage 5 — reporter.py  Reporter.generate()  →  PASS / FAIL"]
        S5A[Compute stats\npage delta, size delta]
        S5A --> S5B["{stem}_source-boundary-map.md\nper-block table"]
        S5A --> S5C["{stem}_compaction-report.md\nrun summary + file sizes"]
        S5B --> S5OUT
        S5C --> S5OUT
        S5OUT[PASS / FAIL verdict]
    end

    S5OUT --> ARTS

    subgraph ARTS["Artifacts — .agent/evals/runs/.../bin/"]
        A1["{stem}_Compacted_Ncol_{run_id}.pdf"]
        A2["{stem}_compaction-report.md"]
        A3["{stem}_source-boundary-map.md"]
    end

    style S1BOX fill:#dbeafe,stroke:#3b82f6
    style S2BOX fill:#e0f2fe,stroke:#0ea5e9
    style S3BOX fill:#fef9e7,stroke:#f0c040
    style S4BOX fill:#f4ecf7,stroke:#8e44ad
    style S5BOX fill:#eafaf1,stroke:#2ecc71
    style ARTS fill:#fdfefe,stroke:#aab
    style ORCH fill:#fdfefe,stroke:#aab
```

---

## 2. Stage 1 — Format Detection & Block Detection Logic

```mermaid
flowchart TD
    A([PDF opened with pdfplumber]) --> B

    B[Sample first 10 non-blank pages\ncount words per page\nIMAGE_HEAVY_SAMPLE_PAGES = 10]

    B --> C{avg words/page\n< 10?\nIMAGE_HEAVY_AVG_WORDS_THRESHOLD}

    C -->|Yes — EOG-style| IH[Format: image_heavy]
    C -->|No — STAAR-style| TR[Format: text_rich]

    IH --> IH1[_find_answer_key_fence\nscan pages for 'answer' + 'key'\nreturn first matching page index]
    IH1 --> IH2[_detect_image_heavy_blocks\niterate pages 0 → fence-1]
    IH2 --> IH3{0 < word_count\n<= 5?\nIMAGE_HEAVY_PAGE_MAX_WORDS}
    IH3 -->|Yes| IH4[Include as block\none full-page QuestionBlock]
    IH3 -->|No — blank or section break| IH5[Skip page]
    IH4 --> IH6([BlockDetectionResult])
    IH5 --> IH2

    TR --> TR1[Scan every page with pdfplumber\nextract word bounding boxes]
    TR1 --> TR2{QUESTION_LINE_PATTERN\nmatch on line start?}
    TR2 -->|Yes| TR3[Start new QuestionBlock\nrecord y_top with BLOCK_TOP_PADDING]
    TR2 -->|No| TR4{ANSWER_CHOICE_PATTERN\nA/B/C/D or F/G/H/J?}
    TR4 -->|Yes| TR5[Track y_bottom of last\nanswer choice line]
    TR4 -->|No| TR1
    TR3 --> TR1
    TR5 --> TR1
    TR1 -->|all pages done| TR6{blocks found\n>= 3?}
    TR6 -->|Yes| TR7[Finalize blocks\napply BLOCK_BOTTOM_PADDING]
    TR6 -->|No — fallback| TR8[Claude Vision\nrender pages as images\nsend to API for Q1 location]
    TR8 --> TR7
    TR7 --> IH6

    style IH fill:#e8f4f8,stroke:#4a9eca
    style TR fill:#fef9e7,stroke:#f0c040
```

---

## 3. Stage 3 — PdfPacker Layout Algorithm

```mermaid
flowchart TD
    A([list of ExtractedBlock\npng_bytes + source dimensions]) --> P1

    subgraph PHASE1["Phase 1 — compute_layout()"]
        P1[For each block\ncompute base_scale\nto fill column width] --> P2
        P2[Will block fit\nin remaining column space?]
        P2 -->|Yes| P3[Place block\nadvance y cursor]
        P2 -->|No| P4[Gap-fill attempt\nleftover > GAP_THRESHOLD_PTS?]
        P4 -->|Yes — try to pull next block| P5[Can all column blocks\ndownscale ≤ MAX_SCALE_REDUCTION\nto fit next block?]
        P5 -->|Yes| P6[Re-layout column\nwith extra block]
        P5 -->|No| P7[Advance column\nor start new page]
        P4 -->|No gap worth filling| P7
        P3 --> P8{More blocks?}
        P6 --> P8
        P7 --> P8
        P8 -->|Yes| P2
        P8 -->|No| P9[list of _PlacedBlock\npage_index, x, y, w, h\neffective_scale per block]
    end

    P9 --> R1

    subgraph PHASE2["Phase 2 — render()"]
        R1[Create fitz.Document\nadd blank pages] --> R2
        R2[For each _PlacedBlock\ninsert PNG at computed rect] --> R3
        R3[doc.save\ndeflate=True\ngarbage=4]
    end

    R3 --> OUT([Output PDF\noutput_page_count])

    subgraph LAYOUT["Layout Parameters"]
        L1["Page: 8.5 × 11 in · 612 × 792 pts\nMargin: OUTPUT_PAGE_MARGIN_PTS\nColumn gap: COLUMN_GAP_PTS\nColumns: 1 or 2"]
    end

    style PHASE1 fill:#f4ecf7,stroke:#8e44ad
    style PHASE2 fill:#eafaf1,stroke:#2ecc71
    style LAYOUT fill:#fdfefe,stroke:#aab
```

---

## 4. Data Model & Stage Handoffs

```mermaid
classDiagram
    direction LR

    class PageSlice {
        +int page_number
        +float y_top
        +float y_bottom
        +float height
    }

    class QuestionBlock {
        +int question_number
        +list~PageSlice~ slices
        +str text_preview
        +float total_height_pts
    }

    class BlockDetectionResult {
        +list~QuestionBlock~ blocks
        +int total_questions
        +list~float~ page_heights
        +list~float~ page_widths
        +bool used_vision_fallback
    }

    class ExtractedBlock {
        +int question_number
        +bytes png_bytes
        +float source_width_pts
        +float total_height_pts
    }

    class _PlacedBlock {
        +ExtractedBlock block
        +int page_index
        +float x
        +float y
        +float w
        +float h
        +float effective_scale
    }

    note for BlockDetectionResult "Output of BlockDetector.detect()\nStage 1 → Stage 2 handoff"
    note for ExtractedBlock "Output of BlockExtractor.extract()\nStage 2 → Stage 3 handoff"
    note for _PlacedBlock "Internal to PdfPacker\nPhase 1 → Phase 2 handoff"

    BlockDetectionResult "1" --> "0..*" QuestionBlock : blocks
    QuestionBlock "1" --> "1..*" PageSlice : slices
    ExtractedBlock ..> QuestionBlock : derived from
    _PlacedBlock "1" --> "1" ExtractedBlock : wraps
```

---

## 5. Module Dependency Map

```mermaid
flowchart TD
    subgraph CLI["Entry Point"]
        ORC[orchestrator.py]
    end

    subgraph PIPELINE["compact_source Pipeline"]
        BD[block_detector.py\nBlockDetector]
        BE[block_extractor.py\nBlockExtractor]
        PP[pdf_packer.py\nPdfPacker]
        RP[reporter.py\nReporter]
        CM[comparator.py\ncompare_pdfs]
    end

    subgraph UTILS["Utilities"]
        AW[artifact_writer.py\nArtifactWriter]
        CC[claude_client.py\nClaudeClient]
        PU[pdf_utils.py\nget_page_count\nrender_page_as_image]
        MU[markdown_utils.py]
    end

    subgraph EXTLIBS["External Libraries"]
        PLB[pdfplumber\ntext + coordinates]
        FTZ[PyMuPDF fitz\nrender + insert images]
        PIL[Pillow\nimage processing]
        ANT[anthropic SDK\nClaude API]
    end

    subgraph CONFIG["Config"]
        CFG[config.py + .env\nDPI, margins, thresholds]
    end

    ORC --> BD
    ORC --> BE
    ORC --> PP
    ORC --> RP
    ORC --> CM
    ORC --> AW
    ORC --> CC
    ORC --> PU

    BD --> CC
    BD --> PU
    BD --> CFG
    BD --> PLB

    BE --> CFG
    BE --> FTZ

    PP --> FTZ
    PP --> CFG

    RP --> MU

    CC --> ANT

    PU --> FTZ
    PU --> PIL

    style CLI fill:#fdfefe,stroke:#aab
    style PIPELINE fill:#e8f4f8,stroke:#4a9eca
    style UTILS fill:#fef9e7,stroke:#f0c040
    style EXTLIBS fill:#f4ecf7,stroke:#8e44ad
    style CONFIG fill:#eafaf1,stroke:#2ecc71
```
