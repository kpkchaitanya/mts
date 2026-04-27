"""
config.py

Central configuration for the MTS system.
Loads environment variables and defines named constants used across all modules.
All magic numbers and external settings belong here — never in business logic.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file: src/ → mts/)
load_dotenv(Path(__file__).parent.parent / ".env")

# ─── API Configuration ────────────────────────────────────────────────────────

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# ─── Artifact Storage ─────────────────────────────────────────────────────────

# Root of the mts project (parent of src/)
PROJECT_ROOT: Path = Path(__file__).parent.parent

# Base directory for all run artifacts
ARTIFACTS_BASE_PATH: Path = PROJECT_ROOT / os.getenv("ARTIFACTS_BASE_PATH", ".agent/evals/runs")

# Feature name used as the folder name under ARTIFACTS_BASE_PATH
FEATURE_NAME: str = "math_worksheet_generation_from_source"

# ─── PDF Processing ───────────────────────────────────────────────────────────

# DPI for rendering PDF pages as images for block extraction and Claude vision.
# 96 DPI produces 817×1057 px on a letter page — crisp enough for classroom
# printing while keeping output PDF file sizes reasonable (~35% smaller than 150 DPI).
# Override with PDF_RENDER_DPI env var if higher fidelity is needed.
PDF_RENDER_DPI: int = int(os.getenv("PDF_RENDER_DPI", "96"))

# Pages before this zero-based index are skipped during boundary search.
# State exams always have at least one cover/instruction page before Q1.
MIN_CONTENT_PAGE: int = int(os.getenv("MIN_CONTENT_PAGE", "1"))

# Maximum number of pages to scan with Claude vision when text detection fails.
# Q1 is rarely beyond page 5 in standard state exam formats.
MAX_VISION_SCAN_PAGES: int = 5

# Maximum number of source pages a single question block may span.
# Markers spanning more pages than this with no detectable answer choices are
# treated as non-question content (formula charts, instructions, etc.) and filtered out.
MAX_QUESTION_SPAN_PAGES: int = int(os.getenv("MAX_QUESTION_SPAN_PAGES", "2"))

# ─── Output PDF Layout ────────────────────────────────────────────────────────

# Letter page dimensions in PDF points (1 pt = 1/72 inch).
OUTPUT_PAGE_WIDTH_PTS: float = float(os.getenv("OUTPUT_PAGE_WIDTH_PTS", "612"))   # 8.5 in
OUTPUT_PAGE_HEIGHT_PTS: float = float(os.getenv("OUTPUT_PAGE_HEIGHT_PTS", "792")) # 11 in

# Margin applied to all four sides of each output page (0.25 inch).
OUTPUT_PAGE_MARGIN_PTS: float = float(os.getenv("OUTPUT_PAGE_MARGIN_PTS", "18"))

# Block scaling factor as a percentage of the source block's natural fit width.
# 100 = original size (block fills the content width).
# Values < 100 shrink blocks (e.g., 85 = 85%) to fit more per output page.
# Values > 100 enlarge blocks beyond their natural fit width (rarely useful).
# Override per-run with --scale-factor on the command line.
BLOCK_SCALE_FACTOR: float = float(os.getenv("BLOCK_SCALE_FACTOR", "100"))

# Default maximum number of output pages a single block may occupy before
# being scaled down. Setting to 2 allows a block to span up to 2 output pages
# (useful for very tall multi-page questions). This can be overridden via
# CLI `--max-block-pages` for a single run or by setting DEFAULT_MAX_BLOCK_PAGES
# in the environment.
DEFAULT_MAX_BLOCK_PAGES: int = int(os.getenv("DEFAULT_MAX_BLOCK_PAGES", "2"))

# Gap (in PDF points) between the two columns in a 2-column layout.
# 12 pts ≈ 1/6 inch, enough visual separation without wasting page width.
COLUMN_GAP_PTS: float = float(os.getenv("COLUMN_GAP_PTS", "12.0"))

# Fraction of a block image's height that may consist of blank (near-white)
# rows at the bottom before the block is flagged in the compaction report.
# 0.15 = 15% — allows for small natural padding below content; flags anything
# beyond that as excess whitespace. Override with WHITESPACE_WARN_THRESHOLD env var.
WHITESPACE_WARN_THRESHOLD: float = float(os.getenv("WHITESPACE_WARN_THRESHOLD", "0.15"))

# Maximum fraction of page height a single image-heavy question block may
# occupy before being flagged in the compaction report.
# EOG question content typically fills 30–93 % of the page (large diagrams
# can fill most of the crop above the footer).  A block at ≥ 95 % indicates
# the footer-exclusion fix regressed: y_bottom reverted to page_height and
# the pixel-trimmer is blocked by the footer at the very bottom.
IMAGE_HEAVY_HEIGHT_WARN_FRACTION: float = float(os.getenv("IMAGE_HEAVY_HEIGHT_WARN_FRACTION", "0.95"))

# Font size (in PDF points) for the question number label overlaid on each block
# in the output PDF when question numbers are not visible in the cropped image.
# Auto-applied for image-heavy (EOG-style) PDFs where the number was in the footer.
# Override per-run with --question-start and suppressed with --no-question-numbers.
QUESTION_LABEL_FONT_SIZE: float = float(os.getenv("QUESTION_LABEL_FONT_SIZE", "10"))

# Remaining space in a column (in PDF points) that triggers a gap-fill attempt.
# ~40 pts ≈ 5 text lines — worth pulling in the next block to avoid wasting space.
GAP_THRESHOLD_PTS: float = float(os.getenv("GAP_THRESHOLD_PTS", "40.0"))

# Maximum fractional downscale from base_scale allowed during gap-fill.
# 0.25 means the packer will shrink blocks by at most 25% to pull in a next block.
MAX_SCALE_REDUCTION: float = float(os.getenv("MAX_SCALE_REDUCTION", "0.25"))

# ─── Pipeline Control ─────────────────────────────────────────────────────────

# Maximum QA retry loops before escalating to a human reviewer
MAX_QA_RETRIES: int = int(os.getenv("MAX_QA_RETRIES", "2"))

# Minimum confidence for text-based boundary detection (0.0–1.0).
# Below this threshold, Claude vision is used as a fallback.
BOUNDARY_DETECTION_MIN_CONFIDENCE: float = 0.7

# ─── Comparator / Golden Sample Comparison ───────────────────────────────────
# DPI used when rendering PDFs for visual comparison (may be higher for
# more sensitive pixel diffs). Keep equal or higher than PDF_RENDER_DPI.
COMPARATOR_RENDER_DPI: int = int(os.getenv("COMPARATOR_RENDER_DPI", str(PDF_RENDER_DPI)))

# Per-pixel grayscale difference threshold (0-255) when computing diffs.
# A pixel difference above this value counts as a changed pixel.
DIFF_PIXEL_THRESHOLD: int = int(os.getenv("DIFF_PIXEL_THRESHOLD", "30"))

# Fraction of pixels that must differ on a page to mark it as a defect
# (e.g., 0.02 = 2%).
DIFF_PAGE_RATIO_THRESHOLD: float = float(os.getenv("DIFF_PAGE_RATIO_THRESHOLD", "0.02"))

# Largest allowed contiguous blank-band fraction on a page before flagging.
# e.g., 0.20 means a continuous near-white vertical band >20% of page height
# is considered a defect (helps catch large empty/black areas introduced by packing).
BLANK_BAND_FRACTION_THRESHOLD: float = float(os.getenv("BLANK_BAND_FRACTION_THRESHOLD", "0.2"))

# ─── Startup Validation ───────────────────────────────────────────────────────

if not ANTHROPIC_API_KEY:
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your Anthropic API key."
    )
