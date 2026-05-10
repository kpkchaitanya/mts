# harness/benchmarks

Performance and quality benchmarks tracked over time.

## Active Benchmarks

| Benchmark | Metric | Baseline | Last Measured |
|-----------|--------|---------|--------------|
| Block detection accuracy | % questions detected | TBD | — |
| QA pass rate | % runs passing QA | TBD | — |
| Page reduction ratio | (source pages - output pages) / source pages | TBD | — |
| Processing time | seconds per source page | TBD | — |
| Eval: Functional Correctness | Average score | TBD | — |
| Eval: Spec Compliance | Average score | TBD | — |

## Benchmark Run Protocol

1. Run against a standardized set of source PDFs (defined in `benchmarks/fixtures/`)
2. Record metrics in a dated results file: `benchmarks/results/YYYY-MM-DD.md`
3. Compare against baseline — flag regressions
4. Update baseline only after deliberate quality improvement (not drift)

## Establishing Baselines

Baselines are established at feature release.
They represent the quality floor — not the ceiling.
