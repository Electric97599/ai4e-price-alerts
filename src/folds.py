"""Fold definitions shared by every model in this repository.

A scored cell is indexed by the month whose outcome it records. The row holding the
price at month t records whether the price rose from t-1 to t, and the forecast for
that cell is issued at month t-1, so no scored month is ever visible to the model that
scores it.

Three expanding folds, each with twelve calibration months and twelve scored months.
The eligibility rule that fixes the universe is frozen before the FIRST calibration
period opens (see src/panel.py), not before the first scored period.

Run:  python src/folds.py    (prints every fold and its cell and rise counts)
"""

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PANEL = os.path.join(ROOT, "outputs", "panel.csv")

FOLDS = [
    {"fold": "1", "fit_at": "2022-06",
     "calibration": ("2022-07", "2023-06"), "scored": ("2023-07", "2024-06")},
    {"fold": "2", "fit_at": "2023-06",
     "calibration": ("2023-07", "2024-06"), "scored": ("2024-07", "2025-06")},
    {"fold": "3", "fit_at": "2024-06",
     "calibration": ("2024-07", "2025-06"), "scored": ("2025-07", "2026-06")},
]


def mi_of(text):
    """Year times twelve plus month, so consecutive months differ by one."""
    year, month = text.split("-")
    return int(year) * 12 + int(month)


def month_label(mi):
    """Inverse of mi_of, for readable tables."""
    return "%04d-%02d" % ((mi - 1) // 12, (mi - 1) % 12 + 1)


def window(panel, start, end):
    """Rows whose outcome month falls inside the window, inclusive."""
    return panel[(panel["mi"] >= mi_of(start)) & (panel["mi"] <= mi_of(end))]


def fold_slice(panel, fold, part):
    """Rows of one fold: part is 'calibration' or 'scored'."""
    if part not in ("calibration", "scored"):
        raise ValueError("part must be 'calibration' or 'scored'")
    start, end = fold[part]
    return window(panel, start, end).copy()


def series_key(frame):
    """One series is a commodity inside one state."""
    return frame["commodity"].astype(str) + " | " + frame["admin1"].astype(str)


def main():
    panel = pd.read_csv(PANEL)
    print("fold  fit at   calibration        scored             cells  rises  series")
    for fold in FOLDS:
        scored = fold_slice(panel, fold, "scored")
        cal = fold_slice(panel, fold, "calibration")
        print("%-5s %-8s %-18s %-18s %5d  %5d  %6d"
              % (fold["fold"], fold["fit_at"],
                 "%s..%s" % fold["calibration"], "%s..%s" % fold["scored"],
                 len(scored), int(scored["rise"].sum()), scored["commodity"].count()
                 and series_key(scored).nunique()))
        if cal.empty:
            print("      calibration window holds no cell: check panel.csv")
    total = sum(len(fold_slice(panel, f, "scored")) for f in FOLDS)
    rises = sum(int(fold_slice(panel, f, "scored")["rise"].sum()) for f in FOLDS)
    print("\nTotal scored cells %d, rises %d, base rate %.1f percent"
          % (total, rises, 100.0 * rises / total))


if __name__ == "__main__":
    main()
