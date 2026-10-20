"""Show, from your own machine, that the frozen rate file matches what CBN publishes.

Usage:
    python scripts/verify_cbn.py                 # checks the most recent date in the file
    python scripts/verify_cbn.py 2026-10-19      # checks a date you choose
    python scripts/verify_cbn.py 2002-01-02      # checks an old date

It downloads the Central Bank feed, picks the US DOLLAR record for that date, and
prints it beside the row stored in data/nigeria/cbn_nfem_usd_daily.csv.
"""

import csv
import json
import os
import sys
import urllib.request

FEED = "https://www.cbn.gov.ng/api/GetAllExchangeRates"
HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "nigeria", "cbn_nfem_usd_daily.csv")


def normalise(text):
    """Return YYYY-MM-DD from either 2026-10-19 or 10/19/2026."""
    text = text.strip()
    if "-" in text:
        return text[:10]
    month, day, year = text.split("/")
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def stored_row(day):
    with open(CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if normalise(row["date"]) == day:
                return row
    return None


def last_date():
    latest = None
    with open(CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            latest = row["date"]
    return normalise(latest)


def feed_rows(day):
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as fh:
        records = json.load(fh)
    return [r for r in records
            if str(r.get("currency", "")).strip().upper() == "US DOLLAR"
            and str(r.get("ratedate", ""))[:10] == day]


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else last_date()
    mine = stored_row(day)
    live = feed_rows(day)

    print(f"date checked: {day}")
    print(f"records the CBN feed returned for US DOLLAR on that date: {len(live)}")
    if not live:
        print("no record on the feed for that date, so nothing to compare")
        return 2

    for r in live:
        print(f"  CBN says   buying {r['buyingrate']}  central {r['centralrate']}  selling {r['sellingrate']}")

    if mine is None:
        print("that date is not in the frozen file")
        return 2

    print(f"  our file   buying {mine['buyingrate']}  central {mine['ngn_per_usd']}  selling {mine['sellingrate']}")

    agree = any(abs(float(r["centralrate"]) - float(mine["ngn_per_usd"])) < 1e-6 for r in live)
    print()
    print("MATCH" if agree else "DIFFERENT: the feed and the frozen file disagree on this date")
    return 0 if agree else 1


if __name__ == "__main__":
    sys.exit(main())
