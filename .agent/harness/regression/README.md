# harness/regression

Regression test cases that must pass before any feature release or significant change.

## Structure

```text
regression/
└── <case-id>/
    ├── case.md          ← description, feature, expected behavior
    ├── input/           ← input artifacts (source PDFs, config)
    ├── expected/        ← expected eval thresholds or golden outputs
    └── results/         ← most recent run result
        └── <YYYY-MM-DD>/
```

## Adding a Regression Case

1. Create a directory: `regression/<descriptive-case-id>/`
2. Write `case.md` describing: what the case tests, why it matters, what pass looks like
3. Deposit input artifacts in `input/`
4. Define expected thresholds or golden outputs in `expected/`
5. Run the case and store results in `results/<date>/`

## Regression Gate

No feature release without a clean regression run across all active cases.
