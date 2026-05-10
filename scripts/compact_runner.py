"""Interactive compact_source runner

Runs compact_source_math for one or more input PDFs in a single shared run
folder. All output PDFs and a consolidated run.log land in one place.

Usage example:
  python scripts/compact_runner.py --inputs docs/exams/g3.pdf docs/exams/g4.pdf --grade 5 --subject Math --columns 2

When multiple inputs share the same grade use --grade once.
"""
import argparse
import csv
import re
import sys
import time
from pathlib import Path

# ── Post-generation QA ──────────────────────────────────────────────────────

def run_post_generation_qa(run_path: Path) -> list[tuple[str, str, str]]:
    """Run the programmatic QA scenarios against the completed run folder.

    Returns a list of (scenario_id, status, detail) tuples where status is
    'PASS' or 'FAIL'. Heuristic-only scenarios (QA-EXT-03, QA-PACK-05) are
    flagged as 'WARN' and require manual visual confirmation.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return [("QA", "SKIP", "PyMuPDF not installed — QA checks skipped")]

    results: list[tuple[str, str, str]] = []
    pdfs = sorted(run_path.glob("*.pdf"))

    # QA-PACK-03: no blank output (every PDF has images on page 0)
    for pdf in pdfs:
        doc = fitz.open(str(pdf))
        imgs = doc[0].get_images(full=True)
        status = "PASS" if imgs else "FAIL"
        results.append(("QA-PACK-03", status,
                        f"{pdf.name}: {len(imgs)} images on page 0"))
        doc.close()

    # QA-PACK-04: only PDFs and run.log in the run folder
    files = list(run_path.iterdir())
    unexpected = [f.name for f in files if f.suffix not in (".pdf", ".log")]
    results.append(("QA-PACK-04",
                    "PASS" if not unexpected else "FAIL",
                    f"unexpected files: {unexpected or 'none'}"))

    # QA-EXT-02: image width >= 1200px (confirms DPI setting)
    for pdf in pdfs:
        doc = fitz.open(str(pdf))
        imgs = doc[0].get_images(full=True)
        if imgs:
            pix = fitz.Pixmap(doc, imgs[0][0])
            status = "PASS" if pix.width >= 1200 else "FAIL"
            results.append(("QA-EXT-02", status,
                            f"{pdf.name}: image width {pix.width}px (need >=1200)"))
        doc.close()

    # QA-EXT-03: bottom-edge brightness heuristic (WARN = visual check needed)
    try:
        import numpy as np
        for pdf in pdfs:
            doc = fitz.open(str(pdf))
            flagged = 0
            checked = 0
            for page_num in range(len(doc)):
                for img_info in doc[page_num].get_images(full=True):
                    pix = fitz.Pixmap(doc, img_info[0])
                    if pix.n > 3:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    arr = np.frombuffer(
                        pix.samples, dtype=np.uint8
                    ).reshape(pix.height, pix.width, pix.n)
                    if arr[-5:, :, :].mean() < 230:
                        flagged += 1
                    checked += 1
            doc.close()
            status = "PASS" if flagged == 0 else "WARN"
            results.append(("QA-EXT-03", status,
                            f"{pdf.name}: {flagged}/{checked} blocks flagged "
                            f"(WARN = inspect visually)"))
    except ImportError:
        results.append(("QA-EXT-03", "SKIP", "numpy not installed"))

    # QA-PACK-05: no split blocks (aspect ratio heuristic)
    for pdf in pdfs:
        doc = fitz.open(str(pdf))
        flagged = 0
        checked = 0
        for page_num in range(len(doc)):
            for img_info in doc[page_num].get_images(full=True):
                pix = fitz.Pixmap(doc, img_info[0])
                ratio = pix.height / pix.width if pix.width > 0 else 1
                if ratio < 0.05:
                    flagged += 1
                checked += 1
        doc.close()
        status = "PASS" if flagged == 0 else "WARN"
        results.append(("QA-PACK-05", status,
                        f"{pdf.name}: {flagged}/{checked} images below ratio 0.05"
                        f" (WARN = inspect visually)"))

    # QA-REP-01/02/03: run.log completeness
    log_path = run_path / "run.log"
    if log_path.exists():
        log = log_path.read_text(encoding="utf-8", errors="replace")
        missing = [g for g in ["Grade3", "Grade4", "Grade5"] if g not in log]
        results.append(("QA-REP-03",
                        "PASS" if not missing and len(log) > 5000 else "FAIL",
                        f"run.log {len(log):,} chars, missing grades: {missing or 'none'}"))
        for tag, section in [("QA-REP-01", "Compaction Report"),
                             ("QA-REP-02", "Pack Layouts")]:
            results.append((tag,
                            "PASS" if section in log else "FAIL",
                            f"'{section}' present: {section in log}"))

        # QA-DET-05: no cover/session heading pages (Q#=0 blocks) in boundary map (BUG-011)
        import re as _re
        zero_q_matches = _re.findall(r"\|\s*0\s*\|\s*(\d+)\s*\|", log)
        status = "FAIL" if zero_q_matches else "PASS"
        results.append(("QA-DET-05", status,
                        f"Q#=0 blocks on pages {zero_q_matches} (BUG-011 — cover pages in output)"
                        if zero_q_matches else "no Q#=0 blocks detected"))
    else:
        for tag in ("QA-REP-01", "QA-REP-02", "QA-REP-03", "QA-DET-05"):
            results.append((tag, "FAIL", "run.log not found"))

    return results


def _print_qa_table(results: list[tuple[str, str, str]]) -> bool:
    """Print the QA results table and return True if all P1/P2-mapped checks pass."""
    # Scenarios that are P1/P2 blockers (WARN is not a hard blocker — needs visual confirm)
    blockers = {"QA-PACK-03", "QA-EXT-02", "QA-REP-01", "QA-REP-02", "QA-REP-03", "QA-DET-05"}
    print("\n" + "=" * 72)
    print("POST-GENERATION QA RESULTS")
    print("=" * 72)
    print(f"  {'Scenario':<14} {'Status':<6}  Detail")
    print("  " + "-" * 68)
    all_blocking_pass = True
    for scenario_id, status, detail in results:
        marker = "  " if status in ("PASS", "SKIP") else ("! " if status == "WARN" else "* ")
        print(f"{marker}{scenario_id:<14} {status:<6}  {detail}")
        if status == "FAIL" and scenario_id in blockers:
            all_blocking_pass = False
    print("=" * 72)
    warn_count = sum(1 for _, s, _ in results if s == "WARN")
    fail_count = sum(1 for _, s, _ in results if s == "FAIL")
    if all_blocking_pass and fail_count == 0:
        verdict = "DELIVERABLE"
        note = "All P1/P2 checks pass."
    elif not all_blocking_pass:
        verdict = "BLOCKED"
        note = f"{fail_count} blocking failure(s) — fix before delivery."
    else:
        verdict = "DELIVERABLE (with notes)"
        note = f"{warn_count} WARN item(s) require visual inspection."
    print(f"Verdict: {verdict}  --  {note}")
    print("=" * 72 + "\n")
    return all_blocking_pass and fail_count == 0

# Ensure workspace root is on the path for in-process src imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _infer_grade(path: Path) -> int | None:
    """Extract grade number from a filename like …Grade3… or …grade_4…"""
    m = re.search(r'[Gg]rade[_\s-]?(\d+)', path.name)
    return int(m.group(1)) if m else None


def load_golden_map(path: Path) -> dict[str, Path]:
    mapping = {}
    if not path or not path.exists():
        return mapping
    with path.open("r", newline="") as fh:
        rdr = csv.reader(fh)
        for row in rdr:
            if not row:
                continue
            src = row[0].strip()
            golden = row[1].strip() if len(row) > 1 else ""
            if src:
                mapping[src] = Path(golden) if golden else None
    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="Run compact_source on multiple inputs with a shared run folder"
    )
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--grade", type=int, default=None,
                        help="Grade number (applied to all inputs). Omit to auto-detect from each filename.")
    parser.add_argument("--subject", default="Math")
    parser.add_argument("--golden-mapping", type=str, default=None)
    parser.add_argument("--scale-factor", type=float, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--columns", type=int, choices=[1, 2], nargs="+", default=[1, 2])
    args = parser.parse_args()

    # Inline imports so dotenv is loaded before config constants are read
    from src.utils.artifact_writer import ArtifactWriter
    from src.orchestrator import (
        run_compact_source_math,
        _setup_run_logging,
        _teardown_run_logging,
    )

    mapping = load_golden_map(Path(args.golden_mapping)) if args.golden_mapping else {}

    # ── One shared run folder for the entire batch ─────────────────────────
    shared_writer = ArtifactWriter()
    _setup_run_logging(shared_writer.artifact_path("run.log"))

    batch_start = time.perf_counter()
    results: list[tuple[str, str]] = []

    for inp in args.inputs:
        src = Path(inp)
        if not src.exists():
            print(f"Source not found: {src}")
            results.append((src.name, "NOT FOUND"))
            continue

        golden = mapping.get(str(src)) if mapping else None
        current_scale = args.scale_factor

        grade = args.grade if args.grade is not None else _infer_grade(src)
        if grade is None:
            print(f"Cannot determine grade for {src.name} — pass --grade or rename the file to include 'GradeN'.")
            results.append((src.name, "SKIP (no grade)"))
            continue

        for col_count in args.columns:
            while True:
                try:
                    run_compact_source_math(
                        pdf_path=src,
                        grade=grade,
                        subject=args.subject,
                        columns=col_count,
                        scale_factor=current_scale,
                        max_pages=args.max_pages,
                        artifact_writer=shared_writer,
                        setup_logging=False,
                        auto_confirm=True,
                    )
                    results.append((src.name, f"PASS ({col_count}-col)"))
                    print(f"{src} ({col_count}-col) -> PASS")
                    break
                except Exception as exc:
                    msg = str(exc)
                    print(f"Detected issue with {src}: {msg}")
                    try:
                        choice = input("Action? [retry/skip/stop]: ").strip().lower()
                    except EOFError:
                        choice = "skip"
                    if choice == "retry":
                        current_scale = max(50.0, (current_scale or 100.0) - 5.0)
                        print(f"Retrying with scale-factor={current_scale}")
                        continue
                    elif choice == "stop":
                        print("Stopping run by user request.")
                        _teardown_run_logging()
                        return
                    else:
                        results.append((src.name, f"FAIL ({col_count}-col)"))
                        break

    total_s = time.perf_counter() - batch_start
    print(f"\nBatch complete in {total_s:.1f}s  —  Run folder: {shared_writer.run_path}")
    for name, status in results:
        print(f"  {status:<10} {name}")

    _teardown_run_logging()

    # ── Post-generation QA loop (agent.md §8 / bug-fix-workflow.md §9) ──────
    qa_results = run_post_generation_qa(shared_writer.run_path)
    _print_qa_table(qa_results)


if __name__ == "__main__":
    main()

