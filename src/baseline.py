"""The two reference rules: seasonal naive, and persistence as a price error benchmark.

Seasonal naive forecasts next month's price as the price twelve months earlier, so its
predicted change is that price over the current price, minus one. It can only score a
cell where a year-earlier price exists, and it carries that coverage: 270, 448 and 488
of the 472, 472 and 508 scored cells.

Persistence repeats last month's price, so its predicted change is exactly zero. A
constant cannot be thresholded against a false alarm cap, so persistence is never an
alerting rule here: it is the reference the average miss is measured against.

Output: outputs/baseline_scores.csv   calibration and scored cells, with both reference scores
        console report               per fold: coverage, threshold, recall and the miss

Run:  python src/baseline.py     (after python src/panel.py)
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import folds as folds_mod          # noqa: E402
import metrics as metrics_mod      # noqa: E402

PANEL = os.path.join(ROOT, "outputs", "panel.csv")
MONTHLY = os.path.join(ROOT, "outputs", "monthly.csv")
OUT = os.path.join(ROOT, "outputs", "baseline_scores.csv")


def price_lookup(panel):
    """The price of every commodity and state in every month it reports.

    Read from outputs/monthly.csv, which panel.py writes for every observed month of every
    eligible series. Reading the pair-only panel.csv instead loses a year-earlier price
    whenever that month's own previous month is missing, which understates the seasonal
    rule's coverage: 230/404/466 cells against the correct 270/448/488.
    """
    if os.path.exists(MONTHLY):
        frame = pd.read_csv(MONTHLY)
    else:
        print("warning: %s is missing, falling back to the pair-only panel, which "
              "understates seasonal coverage. Run python src/panel.py first."
              % os.path.relpath(MONTHLY, ROOT))
        frame = panel
    frame = frame[["commodity", "admin1", "mi", "price_kg"]].drop_duplicates(
        subset=["commodity", "admin1", "mi"])
    return {(c, s, m): p for c, s, m, p in frame.itertuples(index=False, name=None)}


def seasonal_score(price, commodity, admin1, mi):
    """Predicted change from twelve-months-earlier price. NaN when that price is absent."""
    year_before = price.get((commodity, admin1, mi - 12))
    current = price.get((commodity, admin1, mi - 1))
    if year_before is None or current is None or current == 0:
        return np.nan
    return year_before / current - 1.0


def add_scores(panel):
    price = price_lookup(panel)
    out = panel.copy()
    out["actual_change"] = out["price_kg"] / out["prev_price_kg"] - 1.0
    out["naive_score"] = [seasonal_score(price, c, s, m) for c, s, m in
                          zip(out["commodity"], out["admin1"], out["mi"])]
    out["persistence_score"] = 0.0
    out["series"] = folds_mod.series_key(out)
    return out


def run_fold(cal, test, fold_label):
    """Threshold on calibration cells, then score that frozen threshold on scored cells."""
    cal_naive = cal.dropna(subset=["naive_score"])
    test_naive = test.dropna(subset=["naive_score"])
    if cal_naive.empty or test_naive.empty:
        raise SystemExit("fold %s has no cells with a year-earlier price" % fold_label)

    threshold = metrics_mod.choose_threshold(cal_naive["naive_score"], cal_naive["rise"])
    alert = (test_naive["naive_score"] >= threshold).to_numpy()
    return {
        "fold": fold_label, "threshold": threshold, "cells": len(test),
        "rises": int(test["rise"].sum()), "covered": len(test_naive),
        "alerts": int(alert.sum()),
        "recall": metrics_mod.recall(test_naive["naive_score"], test_naive["rise"], threshold),
        "fpr": metrics_mod.false_positive_rate(test_naive["naive_score"], test_naive["rise"], threshold),
        "mae_naive": metrics_mod.mean_absolute_error(
            test_naive["actual_change"], test_naive["naive_score"]),
        "mae_persistence": metrics_mod.mean_absolute_error(
            test["actual_change"], test["persistence_score"]),
        "penalty_k3": metrics_mod.weighted_penalty(alert, test_naive["rise"].to_numpy(), k=3),
    }


def main():
    panel = add_scores(pd.read_csv(PANEL))

    # The common harness needs score rows for calibration months as well as scored
    # months. Keep the observed-month score file broad enough for every fold while the
    # published fold table below still evaluates only each fold's scored window.
    months = set()
    for fold in folds_mod.FOLDS:
        for part in ("calibration", "scored"):
            start, end = fold[part]
            months.update(range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1))
    harness = panel[panel["mi"].isin(months)].copy()
    # Keep the historical fold field in the reference CSV. For months that are both
    # a prior fold's scored window and the next fold's calibration window, use the
    # scored-window fold label; the first calibration window belongs to fold 1.
    fold_by_month = {}
    for fold in folds_mod.FOLDS:
        start, end = fold["scored"]
        for mi in range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1):
            fold_by_month[mi] = fold["fold"]
    for fold in folds_mod.FOLDS:
        start, end = fold["calibration"]
        for mi in range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1):
            fold_by_month.setdefault(mi, fold["fold"])
    harness["fold"] = harness["mi"].map(fold_by_month)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    harness[["series", "commodity", "admin1", "mi", "fold", "price_kg", "prev_price_kg",
             "actual_change", "rise", "naive_score", "persistence_score"]].to_csv(
                 OUT, index=False, lineterminator="\n")

    rows, kept = [], []
    for fold in folds_mod.FOLDS:
        cal = folds_mod.fold_slice(panel, fold, "calibration")
        test = folds_mod.fold_slice(panel, fold, "scored").copy()
        test["fold"] = fold["fold"]
        kept.append(test)
        rows.append(run_fold(cal, test, fold["fold"]))

    scored = pd.concat(kept, ignore_index=True)
    # The fold table is written as well, because the frozen threshold lives here and the
    # demo app must not recompute it: a threshold chosen off the scored cells would be the
    # exact mistake the calibration rule exists to prevent.
    fold_out = os.path.join(ROOT, "outputs", "baseline_folds.csv")
    pd.DataFrame(rows).to_csv(fold_out, index=False)

    print("fold  cells  rises  covered  threshold  recall   fpr   alerts  MAE naive  MAE persist")
    for r in rows:
        thr = "never" if np.isinf(r["threshold"]) else "%.4f" % r["threshold"]
        print("%-5s %5d  %5d  %7d  %9s  %6.3f  %5.3f  %6d  %9.4f  %11.4f"
              % (r["fold"], r["cells"], r["rises"], r["covered"], thr,
                 r["recall"], r["fpr"], r["alerts"], r["mae_naive"], r["mae_persistence"]))
    print("\nwrote %s (%d calibration/scored-window cells)" %
          (os.path.relpath(OUT, ROOT), len(harness)))
    print("wrote %s (frozen thresholds and the reference results)" % os.path.relpath(fold_out, ROOT))
    print("The seasonal rule cannot cover every cell, so it is scored on the cells where a "
          "year-earlier price exists. Report any model beside it on those same cells.")
    print("The balanced market check (full panel beside the balanced markets) is printed "
          "at the end of python src/panel.py.")


if __name__ == "__main__":
    main()
