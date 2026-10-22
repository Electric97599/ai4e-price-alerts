# On ramp: Bukunmi Ogunkoya (Andrew ID bogunkoy, GitHub Kunmi1999)

## Your two tasks

- **#1 Seasonal baseline: coverage and the balanced market check.**
- **#2 Data provenance: checksum script and DATA.md refresh.**

Both are week 10 and neither waits on anybody. They are also what everyone else compares
against, so finishing #1 early unblocks the modelling tasks.

`scripts/check_data.py` verifies the committed snapshot against `SHA256SUMS` and checks the
price-file row count, date range, market count and commodity count. `src/baseline.py` builds
the reference scores for both calibration and scored windows and writes the three fold
reference results.

## Read in this order

1. `AGENTS.md`: the rules, the numbers that must not drift, and the conventions.
2. `docs/CONTEXT.md`: the panel and the folds, in plain terms.
3. `src/baseline.py`: it already scores the seasonal rule and persistence. Your work is
   what it still does not print.
4. `src/metrics.py`: the measures. You should not need to change it.
5. `data/nigeria/DATA.md`: provenance, and what you are extending in #2.

## Task #1, what to add

- Coverage of the seasonal rule beside each fold's cells: 270, 448 and 488 of the 472, 472
  and 508 scored cells. The rule needs a price twelve months back, so it cannot score them
  all, and the report has to say so wherever it quotes a seasonal number.
- The balanced market check: markets with at least one quotation in every scored window.
  29 of the 53 markets in the three states qualify, leaving 43 series, 1,428 cells, 351
  rises, a 24.6 percent base rate. Compute it, do not hardcode it.
- Keep persistence out of the alert comparison. Its predicted change is zero, so it cannot
  be thresholded to a false alarm cap.

Done when `python src/baseline.py` prints all of that and the totals agree with
`python src/panel.py`.

## Task #2, what to add

- `scripts/check_data.py`: change into `data/nigeria/`, verify the checksums in place,
  print the row count, the date range and the market and commodity counts of the price
  file, and exit non zero on any mismatch. A checksum list written from the project root
  fails in place, so the check has to run inside the folder.
- Extend `data/nigeria/DATA.md` with the exchange rate provenance: the CBN daily NFEM
  series, the central rate column, duplicate dates removed, the monthly average, and the
  rule that a month uses only values dated in that month or earlier.

Done when a fresh clone runs `python scripts/check_data.py` and it passes.

## Before you open a pull request

```
python src/metrics.py
python src/folds.py
python src/baseline.py
python scripts/check_data.py
```

## Paste this into your AI assistant

> Read AGENTS.md, docs/CONTEXT.md and docs/on-ramp/ogunkoya.md in this repository before
> touching anything. My tasks are issues #1 and #2. Do not edit src/folds.py,
> src/metrics.py, or src/panel.py without asking me first. Every number you put in a
> document must come from a script you ran, and you must show me the command output.
