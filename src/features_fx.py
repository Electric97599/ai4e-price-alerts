"""Build the exchange-rate feature available at each forecast origin.

Owner: Bizima. Sheet: docs/on-ramp/bizima.md. Rules: AGENTS.md.

Input : data/nigeria/cbn_nfem_usd_monthly.csv  (columns: month, ngn_per_usd, days)
        outputs/panel.csv                      (one row per commodity, state, month pair)
Output: outputs/panel_fx.csv                   (the panel plus a rate column)

The score for outcome month t is issued at t-1. This builder therefore joins the rate
through t-1, not the rate during t. fx.py already averages the daily series by month.
Every forecast origin used by a fold must have a rate; missing values are errors.

Run:  python src/features_fx.py
"""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import folds as folds_mod  # noqa: E402

MONTHLY = os.path.join(ROOT, "data", "nigeria", "cbn_nfem_usd_monthly.csv")
PANEL = os.path.join(ROOT, "outputs", "panel.csv")
OUT = os.path.join(ROOT, "outputs", "panel_fx.csv")

RATE_COLUMN = "ngn_per_usd"


def load_rate(path=MONTHLY):
    """Monthly average naira per dollar, keyed by the same month index the panel uses."""
    rate = pd.read_csv(path)
    if "month" not in rate.columns or RATE_COLUMN not in rate.columns:
        raise SystemExit("%s needs `month` and `%s` columns; rebuild it with src/fx.py"
                         % (path, RATE_COLUMN))
    rate[RATE_COLUMN] = pd.to_numeric(rate[RATE_COLUMN], errors="coerce")
    rate = rate.assign(mi=[folds_mod.mi_of(m) for m in rate["month"].astype(str)])
    if rate["mi"].duplicated().any():
        raise SystemExit("%s contains duplicate monthly exchange-rate entries" % path)
    if rate[RATE_COLUMN].isna().any() or (~(rate[RATE_COLUMN] > 0)).any():
        raise SystemExit("%s contains a missing or nonpositive monthly exchange rate" % path)
    return rate[["mi", RATE_COLUMN]].sort_values("mi")


def attach_rate(panel, rate):
    """Join the rate known at the forecast origin (one month before outcome)."""
    if rate["mi"].duplicated().any():
        raise SystemExit("monthly exchange-rate file has duplicate months")
    origin = rate.rename(columns={"mi": "rate_mi"}).copy()
    origin["mi"] = origin["rate_mi"] + 1
    out = panel.merge(origin[["mi", RATE_COLUMN]], on="mi", how="left", validate="many_to_one")
    need = set()
    for fold in folds_mod.FOLDS:
        for part in ("calibration", "scored"):
            start, end = fold[part]
            need.update(range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1))
    missing = sorted(m for m in need if m - 1 not in set(rate["mi"]))
    if missing:
        labels = ", ".join(folds_mod.month_label(m - 1) for m in missing)
        raise SystemExit("exchange-rate coverage missing forecast-origin month(s): " + labels)
    if out.loc[out["mi"].isin(need), RATE_COLUMN].isna().any():
        raise SystemExit("exchange-rate join left missing values in a fold month")
    return out


def check_coverage(frame, rate):
    """Print rate coverage at each fold's forecast origins."""
    print("rate series covers %s to %s, %d months"
          % (folds_mod.month_label(int(rate["mi"].min())),
             folds_mod.month_label(int(rate["mi"].max())), len(rate)))
    for fold in folds_mod.FOLDS:
        start, end = fold["scored"]
        need = [m - 1 for m in range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1)]
        have = [m for m in need if m in set(rate["mi"])]
        print("fold %s scored window needs %d months, rate series has %d"
              % (fold["fold"], len(need), len(have)))


def main():
    rate = load_rate()
    check_coverage(pd.read_csv(PANEL), rate)
    frame = attach_rate(pd.read_csv(PANEL), rate)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    frame.to_csv(OUT, index=False)
    print("wrote %s (%d rows)" % (os.path.relpath(OUT, ROOT), len(frame)))


if __name__ == "__main__":
    main()
