# AI4E project data: Nigerian staple food prices

## Source

World Food Programme price database, published for Nigeria on the Humanitarian Data
Exchange by WFP on behalf of FEWS NET and the FAO food price monitoring service.

- Dataset page: https://data.humdata.org/dataset/wfp-food-prices-for-nigeria
- Prices file: https://data.humdata.org/dataset/42db041f-7aaf-4ab4-961f-2a12096861e7/resource/12b51155-0cd3-4806-9924-61ede4077591/download/wfp_food_prices_nga.csv
- Markets file: https://data.humdata.org/dataset/42db041f-7aaf-4ab4-961f-2a12096861e7/resource/5329e772-0b74-4f65-8cc0-37a0915cc7e4/download/wfp_markets_nga.csv
- Licence: Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO)
- Retrieved: 19 October 2026, when the publisher's file carried a modification date of 18 October 2026

## What is here

| File | Rows | Contents |
|---|---|---|
| `wfp_food_prices_nga.csv` | 88,391 | Market prices, January 2002 to October 2026, 68 markets, 43 commodities, 14 states, naira with a USD column |
| `wfp_markets_nga.csv` | market lookup | Market identifiers with coordinates and administrative units |
| `SHA256SUMS` | | Checksums of the frozen files committed here |

`SHA256SUMS` is a local snapshot-integrity manifest, not a checksum published by WFP or
the CBN. `scripts/check_data.py` verifies that the committed data bytes have not changed
since this manifest was recorded, then checks the price file's expected profile.

The prices file is the frozen snapshot used by the proposal. It must not be replaced
in place. If WFP publishes a newer extract, download it to a dated filename instead,
so the reported counts keep reproducing.

## Columns that matter for the panel

- `pricetype`: Retail or Wholesale. The project keeps retail only.
- `unit`: mixed. KG, `100 KG`, `50 KG`, `400 G` and similar are converted to naira per
  kilogram. Litres, pieces and tubers are dropped because they are not a mass.
- `priceflag`: `actual` for a single collected quotation, `aggregate` for a computed
  monthly figure. Most rows since 2024 are aggregates, so the panel unit is a market
  month aggregate, not an individual sale.
- `usdprice`: the price converted at the prevailing rate. This is not used as the
  exchange-rate input. The proposal takes that from the Central Bank of Nigeria official
  daily naira rates, averaged by month (https://www.cbn.gov.ng/rates/exchratebycurrency.html).
  The CBN monthly average table on the same site stops in April 2021, which is why the
  daily series is used instead. The central rate column is the one averaged. The feed
  returns duplicate rows on a few dates, so daily rows must be deduplicated by date
  before averaging.

## Reproducing the panel

```
python src/panel.py
```

The script prints the counts that appear in Table 1 of the proposal and writes
`outputs/panel.csv`. If the printed counts disagree with the proposal, the proposal is
wrong. Current output, verified 19 October 2026:

| Fold | Fit through | Calibration | Scored | Eligible series | Cells | Rises | Naive lag |
|---|---|---|---|---|---|---|---|
| 1 | Jun 2022 | Jul 2022 to Jun 2023 | Jul 2023 to Jun 2024 | 46 (44 scored) | 472 | 181 | 270 |
| 2 | Jun 2023 | Jul 2023 to Jun 2024 | Jul 2024 to Jun 2025 | 46 (44 scored) | 472 | 90 | 448 |
| 3 | Jun 2024 | Jul 2024 to Jun 2025 | Jul 2025 to Jun 2026 | 46 (44 scored) | 508 | 84 | 488 |
| all | | | | | 1,452 | 355 | |

Rise rate over the scored cells: 24.4 percent. Inside the three scored windows the
unrestricted three-state panel gives the same 1,452 cells and the same 24.4 percent, so the
eligibility rule changes which series are followed into the windows, not the base rate they
are scored on. A rise counts when the month-on-month increase is at least 10 percent,
so a change of exactly ten percent counts. The last column counts the scored cells where a
price from twelve months earlier exists, which is what the seasonal naive rule needs.

## Eligibility rule

A series enters the panel only if, using data available no later than June 2022, it has
at least 48 monthly price observations. The cut-off sits before the first calibration
period opens in July 2022, so neither a calibration month nor a scored month can
influence which series take part. The count is taken on the monthly series, before the
consecutive-month filter, so a single gap does not disqualify a series. Counting
consecutive pairs instead gives 43 series, which is why that variant is printed by the
script: it shows where a different count comes from.

The rule leaves 46 series across 24 commodities in Borno, Yobe and Adamawa. A persistence
rule, repeating last month's price, is available on every cell and serves as the
full-coverage baseline.

## Balanced market check

Reporting shifts from individual quotations to market aggregates around 2024, so the
analysis is repeated on markets that report at least one quotation in each of the three
scored windows. That is 29 of the 53 markets in the three states, leaving 43 series and
1,428 scored cells with 351 rises, or 24.6 percent. The script prints these figures.

## Why the rate series starts in 2001 when the NFEM table starts in 2024

The bank publishes two different things, and the file names only mention one of them.

- The **official daily rate** (buying, central, selling) has run since 10 December 2001. That
  is what `src/fx.py` downloads and what `cbn_nfem_usd_daily.csv` holds.
- The **NFEM market table** (volume weighted average, high, low, closing, deals, turnover)
  starts on 2 December 2024, when the electronic matching system replaced the previous
  market arrangement. It is a separate table on the same page, not a continuation of the
  first.

The project needs one continuous column, because a model feature cannot be missing for the
months it is used on. Coverage was checked rather than assumed: all 52 months from June 2022
to September 2026 are present, which covers the three scored windows and the last twelve
months of data every calibration window needs.

A second check on the same price file points the same way, with one caveat. The WFP file
carries a `usdprice` column beside `currency` and `price`, so local price over usdprice gives
an implied rate for every row and, taken as a monthly median, for every month. Against the
monthly CBN series across the 52 months the folds use, the median ratio is 1.000, and the
months sit within about a tenth either side of it, including the June and July 2023
devaluation. That is corroboration rather than independent confirmation, because WFP derives
`usdprice` by converting at the prevailing official rate itself, so the two series share a
source. What it does rule out is a misaligned column, a wrong currency or a monthly average
off by a factor.

What this does and does not mean:

- It is **not** a problem for 2002 to 2021, because no result uses those years. Every rule is
  refitted at monthly origins that begin in July 2022.
- It **is** a real caveat about what the feature means. Before June 2023 the value is a pegged
  official rate; after it, a market rate. The exchange rate ablation therefore measures
  whether adding the official rate helps, and it cannot claim to isolate a free floating
  market rate across the whole span. The report must say that.
- Restricting the feature to strictly NFEM months is not possible: it would leave July 2022 to
  November 2024 empty, which is all of fold 1 and half of fold 2. That is the two folds where
  a devaluation happened, so the ablation would lose exactly the variation it exists to test.

## Exchange rate snapshot

Three different links get mixed up on this project, so they are named here once:

- **Where the numbers come from.** `src/fx.py` downloads `https://www.cbn.gov.ng/api/GetAllExchangeRates`,
  the Central Bank's JSON feed, keeps the `US DOLLAR` rows, drops dates that appear twice,
  and writes the two CSVs below. Nothing else is a source of these numbers.
- **The page the paper cites.** `https://www.cbn.gov.ng/rates/exchratebycurrency.html` is the
  human facing page that displays the same numbers in a grid headed Currency, Date, Buying,
  Central, Selling. It is the citation because a reference list cites a page rather than an
  API endpoint, and reference 8 now names the feed in its note as well.
- **A third party that describes both series.** `https://dataminal.com/nigeria/exchange-rate`
  restates the start dates in plain words. It is never downloaded from and does not appear in
  the paper; it is linked in the repository README only as something a reader can check.

The frozen file holds 6,081 rows, one for each unique date from 2001-12-10 to 2026-10-19,
and its first row is identical (2001-12-10, buying 111.85, central 112.35, selling 112.85).
The CBN feed retrieved on 26 October 2026 contains 6,087 records covering those same 6,081
unique dates. After reducing it to one row per date with the duplicate rule described below,
its daily values match the frozen file on all 6,081 dates. Six dates appear twice in the feed,
and four of those pairs carry different quotes: 2022-03-29 by 0.03 naira, 2023-12-12 by
4.50, 2024-02-22 by 48.78 and 2024-07-02 by 3.32. The other two duplicated dates,
2013-06-28 and 2020-11-18, carry identical quotes in both copies. The daily file's duplicate
retention rule is stated in its description below.

- `cbn_nfem_usd_daily.csv`: CBN official daily US dollar rates, one row per date after
  dropping duplicate dates. Where a date appears twice in the feed, the later publication is
  kept, that is the higher id, which is why the frozen file reads 848.78 for 2023-12-12
  against 853.277 in the earlier copy. Columns `date`, `ngn_per_usd` (the central rate,
  midway between the buying and selling quotes except where noted below), `buyingrate`,
  `sellingrate`. 6,081 rows from 2001-12-10 to 2026-10-19. The series is the pegged official
  rate before June 2023 and the NFEM market rate from then on, so the name NFEM is exact
  only for the later part; one continuous series is kept because the model needs one column.
- `cbn_nfem_usd_monthly.csv`: monthly mean of `ngn_per_usd` with a `days` count, 299 rows
  from 2001-12 to 2026-10. All 36 months in the three scored windows are present.
- Regenerate with `python src/fx.py`. Checksums for both files are in `SHA256SUMS`.
- Known defect in the source feed: on 2003-12-09 the central rate is 1376.80 against a
  buying rate of 136.30 and a selling rate of 137.30, a transcription error that lifts
  December 2003 from 136.72 to 195.77. Six rows in total sit outside their own quote band,
  all before 2017 and none inside a scored window, so no reported result depends on them.
  The snapshot is kept exactly as downloaded rather than edited, and `src/fx.py` now warns
  when a row falls outside the band so a refresh surfaces it.

The bank's monthly average table (`/rates/exrate.html`) stops in April 2021, which is why
the daily table is used and averaged here.

How the rate becomes a feature, in order:

1. **Source series.** The Central Bank of Nigeria daily US dollar series, the central rate
   column, stored in `cbn_nfem_usd_daily.csv`, one row per date (the duplicate date rule is
   stated once, in the file description above).
2. **Monthly average.** The daily values are averaged by calendar month into
   `cbn_nfem_usd_monthly.csv`, with a `days` count showing how many dates fed each month.
3. **No look ahead.** A scored cell for outcome month t is forecast at t-1, so it uses only
   values dated in month t-1 or earlier. `src/features_fx.py` joins the monthly average of
   t-1 to the row for t, and stops with an error if any forecast origin in a fold has no rate.

Run `python scripts/check_data.py` from a fresh clone to confirm that the committed bytes of
every file listed in `SHA256SUMS` are unchanged. The script runs the check inside this folder,
prints the row count, date range, and market and commodity counts of the price file, and exits
non zero on any mismatch.

## Price flags

Every `priceflag` value is kept: `actual`, `aggregate`, and the combined label. Among the
retail mass-unit rows the panel is built from, the aggregate flag covers 86.6 percent of
2022 rows, 73.0 percent of 2023, 100 percent of 2024 and 2025, and 96.1 percent of 2026, so
a price in the later years is usually a market aggregate rather than a single quotation.
That is a genuine limit on the comparison rather than something the balanced market check
removes.
