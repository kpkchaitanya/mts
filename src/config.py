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

# ─── Pipeline Control ─────────────────────────────────────────────────────────

# Maximum QA retry loops before escalating to a human reviewer
MAX_QA_RETRIES: int = int(os.getenv("MAX_QA_RETRIES", "2"))

# Minimum confidence for text-based boundary detection (0.0–1.0).
# Below this threshold, Claude vision is used as a fallback.
BOUNDARY_DETECTION_MIN_CONFIDENCE: float = 0.7

# Estimated lines of question content that fit on one printed page.
# Used by the reporter to estimate compacted page count.
LINES_PER_PAGE_ESTIMATE: int = 40

# ─── Startup Validation ───────────────────────────────────────────────────────

if not ANTHROPIC_API_KEY:
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your Anthropic API key."
    )
