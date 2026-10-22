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
EXPECTED_FIRST_MONTH = "2002-01"
EXPECTED_LAST_MONTH = "2026-10"


def verify_checksums(folder=DATA):
    """Check every file listed in SHA256SUMS, from inside the folder it lives in.

    Read SHA256SUMS, hash each listed file in `folder`, and collect names that do not
    match or are missing. Hashing uses hashlib so this works on Windows and Linux.
    """
    manifest = os.path.join(folder, "SHA256SUMS")
    if not os.path.isfile(manifest):
        return ["SHA256SUMS (missing)"]
    problems = []
    with open(manifest, encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                problems.append("SHA256SUMS line %d (malformed)" % line_number)
                continue
            expected, name = parts
            name = name.lstrip("* ")
            path = os.path.abspath(os.path.join(folder, name))
            if os.path.commonpath([os.path.abspath(folder), path]) != os.path.abspath(folder):
                problems.append("%s (path escapes data folder)" % name)
                continue
            if not os.path.isfile(path):
                problems.append("%s (missing)" % name)
                continue
            digest = hashlib.sha256()
            with open(path, "rb") as source:
                for chunk in iter(lambda: source.read(1 << 20), b""):
                    digest.update(chunk)
            if digest.hexdigest().lower() != expected.lower():
                problems.append("%s (checksum mismatch)" % name)
    return problems


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
    if (profile["first"][:7], profile["last"][:7]) != (EXPECTED_FIRST_MONTH, EXPECTED_LAST_MONTH):
        print("WARNING: the file date range no longer matches the frozen snapshot profile")
        sys.exit(1)


if __name__ == "__main__":
    main()
