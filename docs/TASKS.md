# Task board

Eleven tasks, one owner each, matching the timeline table in the proposal. The GitHub
issues carry the same numbers, so `Closes #3` in a commit closes the row here.

| Week | Task | Owner | Issue | Done when |
|---|---|---|---|---|
| 10 | Seasonal baseline with coverage and the balanced market check | Ogunkoya | #1 | `python src/baseline.py` prints 270 / 448 / 488 coverage and the 29 of 53 market check |
| 10 | Frozen snapshot verified by script | Ogunkoya | #2 | `python scripts/check_data.py` passes from a fresh clone |
| 11 | SARIMA pipeline, one model per series | Abodunrin | #3 | `outputs/sarima_scores.csv` exists for all three folds |
| 11 | LightGBM pipeline with the exchange rate switch | Abodunrin | #4 | `outputs/lightgbm_scores.csv` exists, both variants |
| 11 | Monthly scorer for the newest month | Abodunrin | #5 | `outputs/alerts.csv` holds one row per series and month |
| 12 | Fold runner and calibration harness | Bizima | #6 | `python src/run_folds.py` prints the fold table for any score file |
| 12 | Exchange rate feature builder | Bizima | #7 | Panel gains a rate column, and the LightGBM ablation reproduces from scratch |
| 13 | Penalty sensitivity and subgroup tables | Dufitumukiz | #8 | `python src/report_tables.py` writes k = 1, 3, 5 and state and commodity tables |
| 13 | Timing and memory of a full pass | Dufitumukiz | #9 | `python src/resources.py` prints wall clock and peak memory per fold |
| 14 | Demo app wired to the live alert file | Abodunrin | #10 | Streamlit Cloud link works from a phone, alert queue reads `alerts.csv` |
| 14 | Final report and slides | All | #11 | 8 page report and 10 slides, numbers regenerated from the scripts |

## Standing rules

- A task is done when the command in the last column runs, not when the code is written.
- Every model writes `series, mi, score`, the shape `src/run_folds.py` reads.
- The threshold is chosen on calibration cells only, through `metrics.choose_threshold`.
- The realized false alarm rate is reported beside the 10 percent target, including when
  it is worse.
