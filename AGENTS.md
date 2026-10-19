# AGENTS.md

Instructions for any AI coding assistant working in this repository. Read this file, then
`docs/CONTEXT.md`, then your own sheet in `docs/on-ramp/`. A human written quickstart is
in `README.md`; this file exists because the project has conventions that a fresh
assistant will otherwise break silently.

## What this project is

A monthly early warning benchmark for staple food prices in north-east Nigeria. For each
commodity and state, three rules forecast next month's price change, and each rule is
turned into an alert when it expects a rise of at least ten percent. Every rule's alert
threshold is calibrated on twelve months it can see and then frozen for the twelve months
it cannot, so the comparison is honest about what a rule would have caught at the time.

The dataset is the World Food Programme Nigeria price file, frozen in
`data/nigeria/wfp_food_prices_nga.csv`, plus the Central Bank of Nigeria daily naira rate.
Both are public and both are committed, so the code must run without a download.

## Commands

```
pip install -r requirements.txt
python src/panel.py       # rebuild the panel, prints the Table 1 counts
python src/metrics.py     # self tests for every measure, must pass
python src/folds.py       # the three windows; 1,452 cells, 355 rises, 24.4 percent
python src/baseline.py    # seasonal naive and persistence reference scores
streamlit run app.py      # the demo app
```

CI runs four of those commands: the metric self tests, the panel count check, the fold
table check and the reference rules. A red check means one of them broke.

## The numbers that must not drift

Any change that moves these is a change to the project's claims, not a refactor. If you
see a different number, stop and say so rather than updating the docs to match the code.

| Quantity | Value |
|---|---|
| Eligible series | 46 across 24 commodities, 44 of which contribute scored cells |
| Scored cells per fold | 472, 472, 508 |
| Rises per fold | 181, 90, 84 |
| Total cells and rises | 1,452 and 355, a 24.4 percent base rate |
| Seasonal rule coverage | 270, 448, 488 of those cells |
| Balanced market check | 29 of 53 markets, leaving 43 series, 1,428 cells, 351 rises, 24.6 percent |
| Fold 1 calibration | 260 cells in the window, 226 of them with a year-earlier price, because 34 of the 46 series have no observation between July 2022 and January 2023 and all but two resume in February |

## Conventions

- **A scored cell is indexed by the month whose outcome it records.** The row holding the
  price at month t records whether the price rose from t-1 to t, and the forecast for that
  cell is issued at t-1. `mi` is `year * 12 + month`, so consecutive months differ by one.
- **A rise is a price ratio of at least 1.10.** Compare `price / prev_price >= 1.1 * (1 - 1e-9)`,
  never `log(price) - log(prev_price) >= log(1.1)`, because the difference of logs drops the
  cells sitting exactly on ten percent. Six scored cells sit on that line (13 across the
  eligible panel, 16 across the full file), and the tolerance is what keeps two of them.
- **Fold windows overlap on purpose.** The scored window of fold n is the calibration window
  of fold n+1. Never tag panel rows with a single fold column: the assignment overwrites
  fold n's scored rows and that fold ends up empty. Slice with `folds.window(start, end)`.
- **Thresholds are chosen on calibration cells only**, through `metrics.choose_threshold`,
  which maximises recall subject to a false positive rate of at most ten percent among
  non-rise cells, ties going to the higher threshold. Never pass a scored month to it.
- **Persistence is not a model.** Its predicted change is exactly zero, so it cannot be
  thresholded. It is the price error reference that average miss is measured against.
- **Gaps are not imputed.** A series with a gap simply contributes fewer cells.
- **Every model writes `series, mi, score`**, one row per cell, score being the predicted
  percentage change. `src/run_folds.py` consumes that shape.
- **Report the realized false alarm rate beside the ten percent target**, including when it
  is worse. That drift is a finding, not a bug to hide.

## Files nobody edits alone

`src/folds.py` and `src/metrics.py` are shared by every task. Propose a change in an issue
or pull request; do not quietly adjust a measure to make a model look better.

## Writing rules for anything that ships

The proposal and the final report are group work written in the impersonal voice: no
first person pronouns, no em dashes, no claim that the numbers came from anywhere but the
scripts. Explain a technical term the first time it appears, in plain words, and never
write a percentage without the count it corresponds to.

## Where the rest of the context lives

- `docs/CONTEXT.md` the research design, in plain terms, with the reasoning behind each rule
- `docs/TASKS.md` the twelve tasks, owners, weeks, and dependencies
- `docs/on-ramp/<surname>.md` one sheet per teammate: your task, your files, what to read first
- `CONTRIBUTING.md` the branch and pull request loop
- `Group 10_AI4E_Proposal.pdf` the proposal this repository supports: three pages, with the
  content on two and the references on the third
- `data/nigeria/DATA.md` provenance, licence, and what each source column means
