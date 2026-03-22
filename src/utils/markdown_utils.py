"""
markdown_utils.py

Shared utilities for generating consistent markdown content across MTS artifacts.
Used by both the compact_source and generate_worksheet pipelines.
"""

import datetime


def frontmatter(run_id: str, source_filename: str, grade: int, subject: str) -> str:
    """
    Generate a standard metadata block for MTS run artifacts.

    Every artifact in a run shares this block for traceability.

    Args:
        run_id: Unique identifier for this pipeline run.
        source_filename: Name of the source PDF or document file.
        grade: Grade level being processed.
        subject: Subject area (e.g., "Math").

    Returns:
        Formatted markdown string with metadata fields.
    """
    return (
        f"**Run ID:** {run_id}  \n"
        f"**Source File:** {source_filename}  \n"
        f"**Grade:** {grade}  \n"
        f"**Subject:** {subject}  \n"
        f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
    )


def horizontal_rule() -> str:
    """Return a markdown horizontal rule with surrounding newlines."""
    return "\n---\n"


def section_header(title: str, level: int = 2) -> str:
    """
    Generate a markdown section header at the specified level.

    Args:
        title: The section heading text.
        level: Header level between 1 and 6 (default: 2).

    Returns:
        Formatted markdown header string.
    """
    prefix = "#" * level
    return f"\n{prefix} {title}\n"


def pass_fail_icon(passed: bool) -> str:
    """
    Return a markdown icon string for a pass/fail check result.

    Args:
        passed: True if the check passed, False if it failed.

    Returns:
        "✅ Pass" or "❌ FAIL"
    """
    return "✅ Pass" if passed else "❌ FAIL"
