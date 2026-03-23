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

# DPI for rendering PDF pages as images when using Claude vision
# 150 DPI balances legibility with file size for API calls
PDF_RENDER_DPI: int = int(os.getenv("PDF_RENDER_DPI", "150"))

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

# ─── Pipeline Control ─────────────────────────────────────────────────────────

# Maximum QA retry loops before escalating to a human reviewer
MAX_QA_RETRIES: int = int(os.getenv("MAX_QA_RETRIES", "2"))

# Minimum confidence for text-based boundary detection (0.0–1.0).
# Below this threshold, Claude vision is used as a fallback.
BOUNDARY_DETECTION_MIN_CONFIDENCE: float = 0.7

# ─── Startup Validation ───────────────────────────────────────────────────────

if not ANTHROPIC_API_KEY:
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your Anthropic API key."
    )
