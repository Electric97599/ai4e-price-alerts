# On ramp: Olufunke Abodunrin (oabodunr)

## Your four tasks

- **#3 SARIMA pipeline**, week 11.
- **#4 LightGBM pipeline**, week 11 without the rate, week 12 with it once #7 lands.
- **#5 Monthly scorer**, week 12, because it needs the models above.
- **#10 Demo app and deployment**, week 14.

You also own the repository itself, so you merge the pull requests.

## Read in this order

1. `AGENTS.md`: the rules and the numbers that must not drift.
2. `docs/CONTEXT.md`: the model list, the folds and the measures.
3. `src/folds.py`: the windows and the `series, mi, score` shape every model writes.
4. `src/metrics.py`: `choose_threshold` is the only place a threshold may come from.
5. `src/baseline.py`: the reference numbers your models must beat at the same cap.
6. `README.md`, section "Modelling rules the proposal leaves to the repository", for the
   SARIMA order rule, the LightGBM feature list and the gap rule you agreed to.

## What each task produces

- **#3**: `outputs/sarima_scores.csv`, one model per series, orders by information
  criterion at each origin, refitted at every monthly origin, series with too little
  history skipped and counted.
- **#4**: `outputs/lightgbm_scores.csv`, then `outputs/lightgbm_fx_scores.csv` for the
  ablation. Same columns, one column of difference.
- **#5**: `outputs/alerts.csv` for the newest scored month, written by a scheduled script
  from saved models, never fitted inside the app.
- **#10**: the app pointed at `alerts.csv` and `fold_table.csv`, deployed on Streamlit
  Community Cloud, URL at the top of the README, screenshots for the report.

## Watch for

- The realized false alarm rate will exceed ten percent in the later folds. That is the
  finding the proposal already states, so report it; do not retune to hide it.
- Fold 1 calibrates on 260 cells rather than 472, because 34 of the 46 series stop
  reporting between July 2022 and January 2023. Say so beside any fold 1 result.
- The seasonal rule covers fewer cells than your models. Compare on common cells, or state
  the coverage gap loudly.

## Paste this into your AI assistant

> Read AGENTS.md, docs/CONTEXT.md and docs/on-ramp/abodunrin.md before touching anything.
> My tasks are issues #3, #4, #5 and #10. Never choose a threshold using scored months, and
> never change src/metrics.py or src/folds.py to make a model look better. Show me the
> command output behind every number you report.
