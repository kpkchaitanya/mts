# compact_source.prompt.md

This document describes how to run the `compact_source` pipeline from the repository, how
to perform visual comparisons against golden samples, how defects are logged, and an
optional interactive runner that enables a human-in-the-loop incremental repair loop.

Purpose

- Run `compact_source` for one or more source PDFs.
- Optionally compare outputs to golden PDFs and log defects for triage.
- Provide a simple interactive loop to attempt conservative automated fixes (reduce
  `--scale-factor`, retry) until the operator stops.

Quick single-file command

Run from the project root:

```bash
python -m src.orchestrator compact_source --pdf path/to/source.pdf --grade 8 --subject Math --compare --golden path/to/golden.pdf
```

Interactive runner (recommended)

Save the helper runner as `scripts/compact_runner.py` and run it to process batches with
optional golden mappings and an interactive retry loop. The runner:

- Accepts multiple input PDFs.
- Optionally reads a CSV mapping input -> golden sample.
- Runs `compact_source` and, on defects, logs them to `bug_log.csv` and prompts the user
  to `retry`, `skip`, or `stop`.
- `retry` performs a conservative automated adjustment (reduces `--scale-factor` by 5%)
  and re-runs the pipeline.

Example runner (drop into `scripts/compact_runner.py`):

```python
"""Interactive compact_source runner

Usage example:
  python scripts/compact_runner.py --inputs docs/exams/foo.pdf docs/exams/bar.pdf --grade 8 --subject Math --golden-mapping goldmap.csv

goldmap.csv format (no header):
  docs/exams/foo.pdf,goldens/foo_golden.pdf
  docs/exams/bar.pdf,goldens/bar_golden.pdf
"""
import argparse
import csv
import shlex
import subprocess
import sys
from pathlib import Path


def run_compact(py_exe, src_pdf: Path, grade: int, subject: str, compare: bool, golden: Path | None, scale_factor: float | None, max_pages: int | None, columns: int) -> int:
    cmd = [py_exe, "-m", "src.orchestrator", "compact_source", "--pdf", str(src_pdf), "--grade", str(grade), "--subject", subject]
    if compare and golden:
        cmd += ["--compare", "--golden", str(golden)]
    if scale_factor is not None:
        cmd += ["--scale-factor", str(scale_factor)]
    if max_pages is not None:
        cmd += ["--max-pages", str(max_pages)]
    if columns is not None:
        cmd += ["--columns", str(columns)]

    print("Running:", " ".join(shlex.quote(c) for c in cmd))
    p = subprocess.run(cmd)
    return p.returncode


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


def append_bug_log(log_path: Path, src: Path, golden: Path | None, returncode: int):
    header = ["source", "golden", "returncode"]
    exists = log_path.exists()
    with log_path.open("a", newline="") as fh:
        writer = csv.writer(fh)
        if not exists:
            writer.writerow(header)
        writer.writerow([str(src), str(golden) if golden else "", str(returncode)])


def main():
    parser = argparse.ArgumentParser(description="Run compact_source on multiple inputs with interactive repair loop")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--grade", type=int, required=True)
    parser.add_argument("--subject", default="Math")
    parser.add_argument("--golden-mapping", type=str, default=None, help="CSV file mapping input -> golden")
    parser.add_argument("--scale-factor", type=float, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--columns", type=int, choices=[1,2], default=1)
    args = parser.parse_args()

    mapping = load_golden_map(Path(args.golden_mapping)) if args.golden_mapping else {}
    py_exe = sys.executable
    log = Path("bug_log.csv")

    for inp in args.inputs:
        src = Path(inp)
        if not src.exists():
            print(f"Source not found: {src}")
            continue
        golden = mapping.get(str(src)) if mapping else None

        current_scale = args.scale_factor
        while True:
            rc = run_compact(py_exe, src, args.grade, args.subject, golden is not None, golden, current_scale, args.max_pages, args.columns)
            if rc == 0:
                print(f"{src} -> PASS")
                break
            append_bug_log(log, src, golden, rc)
            print(f"Detected issue with {src} (return code {rc}). Logged to {log}.")
            choice = input("Action? [retry/skip/stop]: ").strip().lower()
            if choice == "retry":
                if current_scale is None:
                    current_scale = 95.0
                else:
                    current_scale = max(50.0, current_scale - 5.0)
                print(f"Retrying with scale-factor={current_scale}")
                continue
            elif choice == "skip":
                break
            elif choice == "stop":
                print("Stopping run by user request.")
                return
            else:
                print("Unknown choice. Please type 'retry', 'skip' or 'stop'.")
                continue


if __name__ == "__main__":
    main()
```

Operational notes

- The orchestrator already supports `--compare` and `--golden` flags; the runner leverages them.
- Comparison artifacts are written to the run's `comparisons` directory — inspect those for visual diffs.
- The runner logs defects into `bug_log.csv` so you can triage and track recurring issues.

Next steps

- Optionally add unit tests with mocked subprocesses for the runner.
- Extend automated repair policies (adjust columns, max-pages) if conservative scale-only retries are insufficient.
