Documentation follow-up for #1 and PR #18.

## What changed

- `src/panel.py` prints one comparison table for the full panel and the balanced market check, using `comparison_table` and `print_comparison`. The table combines the market counts with eligible series, contributing series, scored cells, rises and rise rate.
- `src/baseline.py` calls those same functions to print the computed comparison itself. The calculation is shared and the counts are not hardcoded.
- Persistence remains the price error reference only. Its predicted change is zero, so it is excluded from the alert comparison.

Eligible series pass the coverage rule fixed before calibration. Contributing series are eligible series with at least one scored cell. The balanced market check keeps markets with at least one quotation in every scored window.

## Output from both scripts

```text
Full panel against balanced market check (scored windows)
                  markets  eligible contributing  cells  rises  rise rate
full panel             53        46           44   1452    355      24.4%
balanced check         29        43           42   1428    351      24.6%
```

The full-panel rise rate is 355 rises in 1,452 scored cells (24.4 percent); the balanced-check rate is 351 rises in 1,428 scored cells (24.6 percent).

The seasonal rule covers 270 of 472, 448 of 472 and 488 of 508 scored cells across the three folds because it needs a year-earlier price. The corresponding rise counts are 181, 90 and 84.

## Validation

- `python src/panel.py` and `python src/baseline.py` were rerun for this documentation update. Both completed successfully and printed the comparison above, matching the protected counts in `AGENTS.md`.
- The review of commit `964210a` confirmed that CI passed, including `python src/run_all.py --skip-resources`. That full pipeline was not rerun for this documentation update.

## Documentation follow-up

`docs/TASKS.md` now describes both scripts printing the same computed comparison and retains the seasonal coverage counts beside the scored-cell counts.
