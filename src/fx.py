"""Download and freeze the Central Bank of Nigeria naira per dollar rate series.

Source : CBN daily official exchange rates, JSON feed behind
         https://www.cbn.gov.ng/rates/exchratebycurrency.html
Output : data/nigeria/cbn_nfem_usd_daily.csv     one row per date, duplicates removed
         data/nigeria/cbn_nfem_usd_monthly.csv   monthly average, ready as a model feature

The bank's monthly average table stops in April 2021, so the daily feed is used and
averaged by month. The central rate column is taken, which sits midway between the
buying and selling quotes.

Run:  python src/fx.py
"""

import hashlib
import json
import os
import sys
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "data", "nigeria")
DAILY = os.path.join(OUT_DIR, "cbn_nfem_usd_daily.csv")
MONTHLY = os.path.join(OUT_DIR, "cbn_nfem_usd_monthly.csv")
URL = "https://www.cbn.gov.ng/api/GetAllExchangeRates"
CURRENCY = "US DOLLAR"


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        return json.load(fh)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    try:
        raw = fetch()
    except Exception as exc:  # network unavailable; keep the frozen snapshot
        if os.path.exists(DAILY):
            print("network failed (%s); keeping the existing snapshot at %s" % (exc, DAILY))
            raw = None
        else:
            sys.exit("network failed and no local snapshot exists: %s" % exc)

    os.makedirs(OUT_DIR, exist_ok=True)
    if raw is not None:
        rows = [r for r in raw if r.get("currency") == CURRENCY]
        df = pd.DataFrame(rows)
        df["ratedate"] = pd.to_datetime(df["ratedate"])
        for col in ("buyingrate", "centralrate", "sellingrate"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        # The feed repeats a few dates; one row per date, keeping the last publication.
        df = (df.sort_values(["ratedate", "id"])
                .drop_duplicates("ratedate", keep="last")
                .rename(columns={"ratedate": "date", "centralrate": "ngn_per_usd"})
                .loc[:, ["date", "ngn_per_usd", "buyingrate", "sellingrate"]])
        df.to_csv(DAILY, index=False)
        print("daily rows written : %d" % len(df))

    daily = pd.read_csv(DAILY, parse_dates=["date"])
    monthly = (daily.assign(month=daily["date"].dt.to_period("M").astype(str))
                    .groupby("month")
                    .agg(ngn_per_usd=("ngn_per_usd", "mean"), days=("ngn_per_usd", "size"))
                    .reset_index())
    monthly.to_csv(MONTHLY, index=False)

    print("daily span         : %s to %s" % (daily["date"].min().date(), daily["date"].max().date()))
    print("monthly rows       : %d (%s to %s)" % (len(monthly), monthly["month"].iloc[0], monthly["month"].iloc[-1]))
    print("sha256 daily       : %s" % sha256(DAILY))
    print("sha256 monthly     : %s" % sha256(MONTHLY))
    print("written            : %s, %s" % (DAILY, MONTHLY))


if __name__ == "__main__":
    main()
