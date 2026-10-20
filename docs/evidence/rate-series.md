# Evidence: the exchange rate series and where it comes from

One page, so the claim can be checked without reading the code. Written for a reader who has
been told the NFEM table starts in December 2024 and wonders whether the project is using a
series that does not exist for its early years.

## The claim

The project's exchange rate column is the Central Bank of Nigeria **official daily naira per
dollar rate**, which the bank has published since 10 December 2001. It is not the NFEM market
table, which is a second and newer series. The two are different tables on the same page.

## Where to check it

| What | Link | What you should see |
|---|---|---|
| CBN exchange rates page, both tables | https://www.cbn.gov.ng/rates/exchratebycurrency.html | the official buying, central and selling rates, and below them the NFEM rates table |
| CBN data feed behind that page | https://www.cbn.gov.ng/api/GetAllExchangeRates | JSON, one row per date and currency, US DOLLAR rows back to 2001 |
| WFP Nigeria food prices, the food data | https://data.humdata.org/dataset/wfp-food-prices-for-nigeria | HDX page, licence CC BY-IGO, download links for the two CSVs in `data/nigeria/` |
| A third party describing both series | https://dataminal.com/nigeria/exchange-rate | states the official rate runs from 10 December 2001 and the NFEM series from 2 December 2024 |

The NFEM table begins when the electronic matching system went live on 1 December 2024, and
the CBN began publishing its rates on 2 December 2024. That is the date the team heard, and it
is correct, for that table.

## What the frozen files in this repository contain

Measured from the committed files, not from a listing page:

- `data/nigeria/cbn_nfem_usd_daily.csv`: 6,081 rows, 10 December 2001 to 19 October 2026, one
  row per date after dropping six duplicate dates, columns `date`, `ngn_per_usd`,
  `buyingrate`, `sellingrate`.
- `data/nigeria/cbn_nfem_usd_monthly.csv`: 299 rows, December 2001 to October 2026, the
  monthly mean of `ngn_per_usd` with a `days` count.
- Every month the three folds use is present: 52 of 52 months from June 2022 to September
  2026, and 36 of 36 scored months.
- Checksums for both files are in `data/nigeria/SHA256SUMS` and verify in place.

## Why the early years do not matter

No result uses them. Every rule is refitted at monthly origins that begin in July 2022, and
the earliest month any feature reads is June 2021. The 2002 to 2021 span exists in the raw
files because the source publishes it, not because the model touches it.

## What the team should know

The rate changes regime in June 2023. Before that date the column records a pegged official
rate, after it a market rate. The exchange rate ablation therefore measures whether adding the
official rate helps, and it cannot claim to isolate a free floating market rate across the
whole span. Restricting the feature to strictly NFEM months would leave July 2022 to November
2024 empty, which is all of fold 1 and half of fold 2, the two folds that contain the
devaluation.
