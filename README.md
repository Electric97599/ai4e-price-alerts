# Monthly Staple Price Alerts for North-East Nigeria

04-655 A: AI for Engineers, Fall 2026. Group 10.

The project forecasts next month's retail price for each state and commodity in the
WFP Nigerian price database and turns that forecast into an alert when a rise of 10
percent or more is expected. Alerts are calibrated to a target of at most one quiet
series month in ten, fixed before each scored period with the realized rate reported,
and every rule is scored on the same cells on months it never saw, except the seasonal
rule, which needs a year-earlier price and carries its coverage.

## Team

| Member | Andrew ID | Owns |
|---|---|---|
| Olufunke Abodunrin | oabodunr | SARIMA and LightGBM pipelines, monthly scorer, demo app |
| Bukunmi Ogunkoya | bogunkoy | Panel, seasonal baseline, data provenance |
| Jean Chrisostome Dufitumukiz | jeanchrd | Penalty sensitivity, subgroup tables, timing |
| Joshua Bizima | jbizima | Fold runner, exchange rate features |

Task board: `docs/TASKS.md`, mirrored as GitHub issues with one owner each. Working
rules, including the branch and pull request loop, are in `CONTRIBUTING.md`.

## Quickstart

```
git clone https://github.com/Electric97599/ai4e-price-alerts.git
cd ai4e-price-alerts
pip install -r requirements.txt
python src/panel.py        # rebuild the panel, print the Table 1 counts
python src/baseline.py     # reference rules, writes outputs/baseline_scores.csv
streamlit run app.py       # the demo app
```

## Layout

```
Proposal_LaTeX/     main.tex and references.bib, the proposal source
Group 10_AI4E_Proposal.pdf   the submitted proposal
AI4E_Proposal_overleaf.zip                the same source for Overleaf
data/nigeria/       frozen WFP extract, frozen CBN rate series, checksums, provenance
src/panel.py        builds the evaluation panel and prints the Table 1 counts
src/fx.py           downloads the CBN daily rates, freezes them, builds monthly averages
src/folds.py        the three fold windows and the scored cell convention
src/metrics.py      every measure in the proposal, with self tests
src/baseline.py     seasonal naive and persistence reference rules
app.py              Streamlit demo: price history, alert queue, fold results
docs/TASKS.md       who does what, and when it counts as done
outputs/panel.csv   the panel itself, one row per commodity, state and month pair
outputs/baseline_scores.csv   scored cells with both reference scores
```

## Reproduce

```
pip install -r requirements.txt
python src/panel.py
python src/fx.py        # only needed to refresh the frozen rate series
python src/baseline.py
```

`src/panel.py` ends by printing the three scored windows and their counts, which must
match Table 1 of the proposal, plus the balanced market check. Read
`data/nigeria/DATA.md` first for what the raw file contains and why the panel is built
the way it is.

## Modelling rules the proposal leaves to the repository

The proposal states the target, the folds, the calibration rule and the metrics. The
choices below are the ones a reader needs to reproduce the comparison exactly. They are
fixed here rather than in the two page proposal because they are implementation detail.

- **Rise label**: a month is a rise when the month-on-month price change is at least
  10 percent, so a change of exactly ten percent counts. Compare the price ratio, not
  the difference of logs, or exact boundary cases get dropped by rounding.
- **Refitting**: every rule is refitted at each monthly origin on data up to that month.
  Each score is one month ahead of its refit. A scored outcome month is therefore
  forecast from the month before it.
- **Seasonal naive**: predict the price twelve months earlier. It can only alert on cells
  where that price exists, which is 270, 448 and 488 of the 472, 472 and 508 scored cells.
- **SARIMA**: one model per series, orders selected by information criterion (AIC) over a
  small grid of non-seasonal orders up to (2,1,2) and one seasonal difference of order 12.
  Selection uses only data up to each origin. Series with fewer than 24 observations in
  the fitting window are skipped and reported.
- **LightGBM**: pooled model predicting the log one month change; features are price lags
  of one to three months, trailing three and twelve month averages, calendar month,
  state, commodity and the exchange rate when that variant is switched on. Settings are
  fixed in one config file and reported in the final report.
- **Gaps**: missing months are not imputed. Consecutive month pairs only enter the panel,
  and model inputs are built from the months that exist, so a series with a gap simply
  contributes fewer cells.
- **Persistence**: repeats last month's price. Its forecast change is identically zero, so
  it cannot be thresholded to a false positive rate. It is a price error benchmark only
  and is excluded from the alert comparison.
- **Precision recall area**: computed on the cells each rule covers. Because the seasonal
  rule covers fewer cells, area values are not directly comparable across rules; the
  report also gives common cell results and states coverage next to every score.
- **Exchange rate**: monthly average of the CBN official daily NFEM naira per dollar rate,
  taking the central rate column of the daily table, averaged over the days present in
  each month after removing duplicate dates. The rate for a scored month uses only values
  dated in that month or earlier.
- **Price flags**: every flag in the source file is retained (actual, aggregate, and the
  combined label). The balanced market check controls which markets report; it does not
  remove the shift from quotations to aggregates, so that shift is stated as a limit.

## Build the proposal

```
cd Proposal_LaTeX
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Needs a TeX installation with `IEEEtran.bst`, which ships with TeX Live.
