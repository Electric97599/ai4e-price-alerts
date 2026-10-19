"""Starter for issue #7: the exchange rate as a model ready column.

Owner: Bizima. Sheet: docs/on-ramp/bizima.md. Rules: AGENTS.md.

Input : data/nigeria/cbn_nfem_usd_monthly.csv  (columns: month, ngn_per_usd, days)
        outputs/panel.csv                      (one row per commodity, state, month pair)
Output: outputs/panel_fx.csv                   (the panel plus a rate column)

The rule that matters: the rate for a month uses only values dated IN THAT MONTH OR
EARLIER. fx.py already averages by month from the daily series, so the monthly file is
enough; do not re-read the daily file. Every scored month must have a rate; a missing one is
a failure, never a zero, because a zero silently becomes a model feature.

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
    rate = rate.assign(mi=[folds_mod.mi_of(m) for m in rate["month"].astype(str)])
    return rate[["mi", RATE_COLUMN]].drop_duplicates(subset=["mi"]).sort_values("mi")


def attach_rate(panel, rate):
    """Panel rows with the rate for their month, or a clear failure.

    TODO(#7): implement the join. Use pd.merge on mi. Then check that every month in all
    three scored windows has a rate by testing for NaN, and raise SystemExit naming the
    missing months rather than filling them. Return the panel with `nfem_rate` added.

    The column may need to be named after the source field: keep `ngn_per_usd`, the name
    fx.py writes, so the report and the data file agree.
    """
    raise NotImplementedError("issue #7: join the rate onto the panel by month")


def check_coverage(frame, rate):
    """Print the coverage of the rate series against the scored windows."""
    print("rate series covers %s to %s, %d months"
          % (folds_mod.month_label(int(rate["mi"].min())),
             folds_mod.month_label(int(rate["mi"].max())), len(rate)))
    for fold in folds_mod.FOLDS:
        start, end = fold["scored"]
        need = [m for m in range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1)]
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
    try:
        main()
    except NotImplementedError as todo:
        print("Not built yet:", todo)
        print("See the docstring at the top of this file, and your sheet in docs/on-ramp/.")
        raise SystemExit(2)
