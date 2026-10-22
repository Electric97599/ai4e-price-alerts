# Monthly Staple Price Alerts for North-East Nigeria

04-655 A: AI for Engineers, Fall 2026. Group 10.

The project forecasts next month's retail price for each state and commodity in the
WFP Nigerian price database and turns that forecast into an alert when a rise of 10
percent or more is expected. Alerts are calibrated to a target false-alarm rate of at most
ten percent, fixed before each scored period with the realized rate and coverage reported.
Each rule is evaluated on the cells it can score; comparisons that require matched cells
use the common subset.

## Team

| Member | Andrew ID | Owns |
|---|---|---|
| Olufunke Abodunrin | oabodunr | SARIMA and LightGBM pipelines, monthly scorer, demo app |
| Bukunmi Ogunkoya | bogunkoy | Panel, seasonal baseline, data provenance |
| Jean Chrisostome Dufitumukiz | jeanchrd | Penalty sensitivity, subgroup tables, timing |
| Joshua Bizima | jbizima | Fold runner, exchange rate features |

Task board: `docs/TASKS.md`, mirrored as GitHub issues with one owner each. Working
rules, including the branch and pull request loop, are in `CONTRIBUTING.md`.

**Working with an AI assistant, or new to the project?** Read `AGENTS.md` first, then
`docs/CONTEXT.md` for the design in plain words, then your own sheet in `docs/on-ramp/`.
Those three files exist so a teammate's assistant does not have to guess the conventions
or invent a number.

## Quickstart

```
git clone https://github.com/Electric97599/ai4e-price-alerts.git
cd ai4e-price-alerts
python -m venv .venv       # Python 3.11 to 3.13; 3.14 has no wheel for the pinned pins
pip install -r requirements.txt
python src/run_all.py      # full data, model, scoring, alert and report pipeline
streamlit run app.py       # the demo app
```

`python src/run_all.py --skip-resources` runs the same project pipeline without the
additional per-model, per-fold timing and memory reruns. The full command also writes
`docs/RESOURCES.md` and `outputs/resources.csv`.

## Data sources

The repository ships a frozen snapshot; these are the pages it came from, so a reader can
check the data without trusting the copy.

| Source | Link | Terms |
|---|---|---|
| WFP Nigeria food prices, dataset page | https://data.humdata.org/dataset/wfp-food-prices-for-nigeria | CC BY-IGO |
| the prices file itself | https://data.humdata.org/dataset/42db041f-7aaf-4ab4-961f-2a12096861e7/resource/12b51155-0cd3-4806-9924-61ede4077591/download/wfp_food_prices_nga.csv | CC BY-IGO |
| the markets file | https://data.humdata.org/dataset/42db041f-7aaf-4ab4-961f-2a12096861e7/resource/5329e772-0b74-4f65-8cc0-37a0915cc7e4/download/wfp_markets_nga.csv | CC BY-IGO |
| CBN official daily exchange rates, page | https://www.cbn.gov.ng/rates/exchratebycurrency.html | public data |
| the feed behind that page | https://www.cbn.gov.ng/api/GetAllExchangeRates | public data |
| a second description of both series, for checking the dates | https://dataminal.com/nigeria/exchange-rate | third party, not a data source |

Both were retrieved on 19 October 2026 and frozen, with checksums in
`data/nigeria/SHA256SUMS` and provenance in `data/nigeria/DATA.md`. The CBN page carries two
different tables: the official daily rate since December 2001, and the NFEM market rates since
December 2024. This project uses the first, and `docs/evidence/rate-series.md` explains why.

To cite them in a report, these are the two entries the proposal uses:

```
@misc{wfp2026nigeria,
  author       = {{World Food Programme}},
  title        = {{Nigeria} - Food Prices},
  howpublished = {WFP Price Database, Humanitarian Data Exchange,
                  \url{https://data.humdata.org/dataset/wfp-food-prices-for-nigeria}},
  year         = {2026},
  note         = {Licence {CC} {BY-IGO}, accessed: Oct. 19, 2026}
}

@misc{cbn2026rates,
  author       = {{Central Bank of Nigeria}},
  title        = {Exchange Rates: Official Daily Naira Rates},
  howpublished = {Central Bank of Nigeria,
                  \url{https://www.cbn.gov.ng/rates/exchratebycurrency.html}},
  year         = {2026},
  note         = {Daily rates averaged by month; accessed: Oct. 19, 2026}
}
```

## Layout

```
Proposal_LaTeX/     main.tex and references.bib, the proposal source
Group 10_AI4E_Proposal.pdf   the submitted proposal
data/nigeria/       frozen WFP extract, frozen CBN rate series, checksums, provenance
src/panel.py        builds the evaluation panel and prints the Table 1 counts
src/fx.py           downloads the CBN daily rates, freezes them, builds monthly averages
src/folds.py        the three fold windows and the scored cell convention
src/metrics.py      every measure in the proposal, with self tests
src/run_all.py      one command to rebuild and connect the coded deliverables
src/baseline.py     seasonal naive and persistence reference rules
src/contracts.py    the series, mi, score file every model writes, with validation
src/run_folds.py    #6: calibration harness and per-rule fold results (Bizima)
src/features_fx.py  #7: forecast-origin CBN rate join (Bizima)
src/sarima.py       #3: per-series SARIMA forecasts (Abodunrin)
src/lightgbm_pipeline.py #4: pooled LightGBM with/without lagged rate (Abodunrin)
src/model_config.py fixed model settings for both learned models
src/score_alerts.py #5: latest scored-month alerts (Abodunrin)
src/report_tables.py #8: weighted penalties and subgroup tables (Dufitumukiz)
src/resources.py    #9: per-model/per-fold time and sampled peak memory (Dufitumukiz)
scripts/check_data.py #2: checksums and price-file profile (Ogunkoya)
app.py              #10: Streamlit demo reading saved alerts and fold results
docs/TASKS.md       who does what, and when it counts as done
docs/CONTEXT.md     the research design in plain words, for people and their assistants
docs/on-ramp/       one sheet per teammate: your task, your files, what to read first
AGENTS.md           what an AI assistant must read before editing anything
outputs/panel.csv   the panel itself, one row per commodity, state and month pair
outputs/monthly.csv every observed month of the eligible series, so gaps stay visible
outputs/baseline_scores.csv   calibration and scored cells with both reference scores
outputs/baseline_folds.csv    the frozen thresholds and the reference results per fold
outputs/fold_table.csv        calibration/scored metrics for all four forecast rules
outputs/alerts.csv            latest scored month, with outcomes withheld from the app
```

## Reproduce

```
pip install -r requirements.txt
python src/run_all.py --skip-resources
```

The networked `src/fx.py` command is only for deliberately refreshing the frozen rate
snapshot. The normal pipeline uses the committed data and needs no network access.

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
  Each origin uses at most the previous 60 calendar months; selection uses only data through
  that origin. Gaps stay missing. Series with fewer than 24 observed values in the window are
  skipped and reported. Candidate fits reuse the prior month's parameter estimates only as
  optimizer starting values, then refit and compare AIC again.
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
- **Exchange rate**: monthly average of the CBN official daily naira per dollar rate, taking
  the central rate column of the daily table, averaged over the days present in each month
  after removing duplicate dates. A forecast for outcome month t is issued at t-1, so its
  feature uses the monthly average through t-1 and does not use the outcome month's rate.
  The series is one continuous column spanning 2001 to the snapshot, but the rate
  it records changes regime in June 2023, from the pegged official rate to a market rate, so
  the ablation measures whether adding the official rate helps and not whether a free
  floating rate helps. All 52 months the folds use are present.
- **Price flags**: every flag in the source file is retained (actual, aggregate, and the
  combined label). The balanced market check controls which markets report; it does not
  remove the shift from quotations to aggregates, so that shift is stated as a limit.

## Licence

The code is MIT licensed; see `LICENSE`. The data is not: the World Food Programme price
files are published under CC BY-IGO and the Central Bank of Nigeria rate series is public
data. `data/nigeria/DATA.md` records the source, the retrieval date and the attribution
each one requires.

## Build the proposal

```
cd Proposal_LaTeX
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Needs a TeX installation with `IEEEtran.bst`, which ships with TeX Live.
