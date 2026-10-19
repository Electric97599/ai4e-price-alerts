"""Starter for issue #2: prove the frozen snapshot is intact, from a fresh clone.

Owner: Ogunkoya. Sheet: docs/on-ramp/ogunkoya.md. Rules: AGENTS.md.

Two checks, in this order:

1. The checksums verify. They must be checked from INSIDE data/nigeria/, because the list
   holds bare filenames; a check run from the project root fails and tells you nothing.
2. The price file is the one the proposal describes: row count, date range, and the number
   of markets and commodities. Those counts are quoted in the report, so a silent data
   refresh would otherwise go unnoticed.

Run:  python scripts/check_data.py
Exit code 0 means the snapshot is intact.
"""

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "nigeria")

EXPECTED_ROWS = 88391
EXPECTED_MARKETS = 68
EXPECTED_COMMODITIES = 43


def verify_checksums(folder=DATA):
    """Check every file listed in SHA256SUMS, from inside the folder it lives in.

    TODO(#2): implement. Read SHA256SUMS, hash each listed file in `folder`, and collect
    the names that do not match or are missing. Return the list of problems, empty when the
    snapshot is intact. Do not shell out to sha256sum: it does not exist on every machine
    the group uses, and hashlib does.
    """
    raise NotImplementedError("issue #2: verify the checksums in place")


def profile_prices(path=None):
    """Row count, date range and the market and commodity counts of the price file."""
    import pandas as pd
    path = path or os.path.join(DATA, "wfp_food_prices_nga.csv")
    frame = pd.read_csv(path, usecols=["date", "market", "commodity"], parse_dates=["date"])
    return {"rows": len(frame), "first": frame["date"].min().date().isoformat(),
            "last": frame["date"].max().date().isoformat(),
            "markets": frame["market"].nunique(),
            "commodities": frame["commodity"].nunique()}


def main():
    problems = verify_checksums()
    if problems:
        print("checksum failures:")
        for name in problems:
            print("  " + name)
        sys.exit(1)
    print("checksums verified in place")

    profile = profile_prices()
    print("price file: %(rows)d rows, %(first)s to %(last)s, %(markets)d markets, "
          "%(commodities)d commodities" % profile)
    if (profile["rows"], profile["markets"], profile["commodities"]) != (
            EXPECTED_ROWS, EXPECTED_MARKETS, EXPECTED_COMMODITIES):
        print("WARNING: the file no longer matches the profile the report quotes")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as todo:
        print("Not built yet:", todo)
        print("See the docstring at the top of this file, and your sheet in docs/on-ramp/.")
        raise SystemExit(2)
