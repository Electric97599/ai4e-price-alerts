# Project context

The reasoning behind the repository, written so a new reader or a new AI assistant can
work on it without reading the proposal PDF first. Read `AGENTS.md` for the rules and
`docs/TASKS.md` for who is doing what.

## The decision being supported

A firm buying staple foods in Borno, Yobe or Adamawa commits to a quantity every month.
Two mistakes are possible and they cost different things. Buying before a flat month ties
up cash that could have waited. Waiting through a rise costs margin on every kilogram
bought later. A forecast that is accurate on average can still be useless here, because a
rule that alerts every month catches every rise and warns of nothing.

So the question is not how accurate a forecast is. It is how many real rises a rule catches
while raising few false alarms, and what each kind of mistake costs.

## The data

- `data/nigeria/wfp_food_prices_nga.csv`: World Food Programme harmonised food prices for
  Nigeria, published on HDX under CC BY-IGO. 88,391 rows, January 2002 to October 2026, 68
  markets, 43 commodities, 14 states. Monthly retail prices, with a unit column that mixes
  kilograms, 100 kilogram bags and grams.
- `data/nigeria/wfp_markets_nga.csv`: the market list, including coordinates.
- `data/nigeria/cbn_nfem_usd_daily.csv` and `cbn_nfem_usd_monthly.csv`: the Central Bank of
  Nigeria official daily NFEM naira per dollar rate, taken from the central rate column,
  duplicate dates removed, averaged by month. Built by `src/fx.py`. The bank's monthly
  average table stops in April 2021, which is why the daily feed is the source.
- `data/nigeria/DATA.md` records the URLs, the retrieval date, the licence and the meaning
  of every column used. `SHA256SUMS` freezes the bytes.

## The panel

`src/panel.py` turns the raw file into one row per commodity, state and consecutive month
pair, with the price in naira per kilogram.

- Retail rows only, mass units only, converted to naira per kilogram. Litres, pieces and
  tubers cannot be compared and are dropped.
- One price per commodity, state and month: the median across that month's market quotes.
- Only consecutive months are kept. Missing months are not filled in.
- Every price flag in the source is retained (actual, aggregate, and the combined label).
  Since 2024 most rows are monthly market aggregates rather than single quotations; that
  shift is a disclosed limit, not something the panel corrects.
- The eligible universe is fixed once, before the first calibration period opens in July
  2022: north-east states only, and a series needs at least 48 monthly observations by June
  2022. Counting that on monthly observations gives 46 series and 24 commodities; counting
  it on consecutive pairs gives 43 and 23, and the script prints both so the difference is
  never an argument.

## The folds

| Fold | Fit at start | Calibration | Scored |
|---|---|---|---|
| 1 | June 2022 | Jul 2022 to Jun 2023 | Jul 2023 to Jun 2024 |
| 2 | June 2023 | Jul 2023 to Jun 2024 | Jul 2024 to Jun 2025 |
| 3 | June 2024 | Jul 2024 to Jun 2025 | Jul 2025 to Jun 2026 |

Every rule is refitted at each monthly origin using only data up to that month, and its
score is the predicted one month percentage change. So a scored outcome month is forecast
from the month before it, and the calibration errors and the scored errors are the same
one step kind.

## The rules compared

- **Seasonal naive**: the price twelve months earlier, expressed as a predicted change. It
  can only alert where a year-earlier price exists, which is why it covers 270, 448 and 488
  of the 472, 472 and 508 cells and carries that coverage wherever it is reported.
- **SARIMA**: one model per series, orders chosen by information criterion at each origin,
  skipped and reported when a series has too little history to fit.
- **Pooled LightGBM**: one model across all series on price lags of one to three months,
  trailing three and twelve month averages, calendar month, state and commodity. It is the
  only model run twice, with and without the exchange rate, because the exchange rate is
  the project's single ablation.
- **Persistence**: repeats last month's price, so its predicted change is exactly zero. It
  is the reference for average miss, never an alerting rule.

## The measures

- **Primary**: how many true rises were caught at the frozen threshold, with the realized
  false alarm rate reported beside the ten percent target.
- **Precision recall area** on the cells each rule covers, a single summary of the trade
  between catching rises and raising false alarms.
- **Mean absolute error** in monthly price change, against persistence and the seasonal rule.
- **An assumed weighted decision penalty per 1,000 scored cells**: a missed rise counts k, a
  false alarm counts one, evaluated at k = 1, 3 and 5. The weights are assumptions, never
  measured procurement costs, and the report says so.

## What the reference rules already show

Run `python src/baseline.py`. The seasonal rule catches 5.6, 27.4 and 71.4 percent of rises
across the three folds, but its realized false alarm rate is 2.1, 23.3 and 56.6 percent
against a target of ten, because a threshold set a year earlier does not survive a market
that moves. Its average miss in monthly change is 0.55, 0.40 and 0.39 against 0.14, 0.13 and
0.13 for persistence.

That drift is the difficulty the project exists to measure. It is also the floor: a learned
model that cannot beat these numbers at the same cap has not earned a place in the report.

## The demo

`app.py` reads files the scripts write and never fits a model, so a visitor cannot make it
forecast something the group has not produced. Three screens: price history for one series,
the alert queue with accept and dismiss (the record of an analyst supervising the system),
and the fold results. The accept and dismiss entries are the evidence for the project's
autonomy claim.

## Limits to keep stating

- Coverage is regional: the recent data is north-east only, so results are not Nigeria wide.
- The panel has no personal attributes, so performance is reported by state and commodity
  rather than as a fairness claim.
- The recent price flags shift toward market aggregates, which changes what a price means.
- Fold 1 calibrates on a thinner panel than it scores, for the reason in the table above.
