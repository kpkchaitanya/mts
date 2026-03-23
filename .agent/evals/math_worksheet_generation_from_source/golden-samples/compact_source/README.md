# Golden Samples — compact_source

This folder contains reference outputs that define what a correct `compact_source` run looks like.

Use these files when verifying a `fix-applied` bug or evaluating a new run.

---

## What belongs here

| File type | Purpose |
|-----------|---------|
| `*.pdf` | Expected compacted output PDF — the visual ground truth |
| `*.md` | Notes describing what to look for in the PDF (optional) |

## Naming convention

```
<source-filename>-expected.pdf
<source-filename>-notes.md
```

Example:
```
2022-staar-3-math-test-expected.pdf
2022-staar-3-math-test-notes.md
```

## How to use

When verifying a `fix-applied` bug or running a new eval:

1. Run `compact_source` on the same source PDF
2. Open the new output PDF side-by-side with the golden sample
3. Confirm: no intro content before Q1, no excessive whitespace between blocks, consistent block sizes
4. If the output matches the golden sample → mark the bug `resolved`
