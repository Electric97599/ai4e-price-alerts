# On ramp: Joshua Bizima (Andrew ID jbizima, GitHub jbizima)

## Your three tasks

- **#15 Exchange rate ablation**, week 12: the LightGBM variant with the rate, the half the proposal gives that week to you.
- **#6 Fold runner and calibration harness**, week 10 to 12. This is the path every model's
  score goes through, so it is the most load bearing file in the repository.
- **#7 Exchange rate feature builder**, week 10, because the week 12 ablation in #4 cannot
  start until the rate exists as a model ready column.

Both implementations are available: `src/run_folds.py` validates and scores each rule,
and `src/features_fx.py` joins the rate available at each forecast origin. A score file must
include both calibration and scored months so the threshold is calibrated without using
scored outcomes.

## Read in this order

1. `AGENTS.md`: the rules and the numbers that must not drift.
2. `docs/CONTEXT.md`: the folds, the measures, and why the threshold is frozen.
3. `src/folds.py`: the windows and the `series, mi, score` convention you are enforcing.
4. `src/metrics.py`: do not reimplement a measure, call it.
5. `src/baseline.py`: your harness must reproduce these numbers exactly before anyone
   trusts it with a model.

## Task #6, what to build

`src/run_folds.py`, taking any score file shaped `series, mi, score`:

- Join the rise labels from `outputs/panel.csv`.
- Per fold, choose the threshold on calibration cells only, using
  `metrics.choose_threshold`, then freeze it and apply it to the scored cells.
- Report cells, rises, coverage, threshold, recall, realized false alarm rate, alerts,
  precision recall area, mean absolute error against persistence and the seasonal rule on
  the cells they share, and the weighted penalty at k = 1, 3 and 5.
- Write `outputs/fold_table.csv`, and refuse a score file containing a NaN score or a month
  outside the folds rather than silently dropping rows.

Done when `python src/run_folds.py --scores outputs/baseline_scores.csv --column naive_score`
reproduces what `src/baseline.py` prints. The `--column` flag is needed because the reference
file carries more than one score; a model file will simply have `score`.

## Task #7, what to build

`src/features_fx.py`:

- Read `data/nigeria/cbn_nfem_usd_monthly.csv`, join by forecast origin. A score for target
  month t is issued at t-1, so the rate feature uses the monthly average through t-1.
- Write `outputs/panel_fx.csv` with the rate column added.
- Assert that every month in all three scored windows has a rate, and print the coverage
  range. A missing rate must fail the script, not become a zero.

## Watch for

- Fold windows overlap: the scored window of fold n is the calibration window of fold n+1.
  Never build a single `fold` column across the panel; slice per fold.
- The seasonal rule covers fewer cells than the other rules, so a precision recall area
  computed on different cell sets is not comparable. Compute common cell results too.
- The realized false alarm rate can exceed ten percent. Print it; never retune.

## Paste this into your AI assistant

> Read AGENTS.md, docs/CONTEXT.md and docs/on-ramp/bizima.md before touching anything. My
> tasks are issues #6 and #7. Build the harness against outputs/baseline_scores.csv and
> prove it reproduces src/baseline.py. Do not edit src/metrics.py, src/folds.py or
> src/panel.py without asking me, and show me the command output behind every number.
