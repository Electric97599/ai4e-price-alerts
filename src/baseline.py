"""The two reference rules: seasonal naive, and persistence as a price error benchmark.

Seasonal naive forecasts next month's price as the price twelve months earlier, so its
predicted change is that price over the current price, minus one. It can only score a
cell where a year-earlier price exists, and it carries that coverage: 270, 448 and 488
of the 472, 472 and 508 scored cells.

Persistence repeats last month's price, so its predicted change is exactly zero. A
constant cannot be thresholded against a false alarm cap, so persistence is never an
alerting rule here: it is the reference the average miss is measured against.

Output: outputs/baseline_scores.csv   one row per scored cell, with both reference scores
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
OUT = os.path.join(ROOT, "outputs", "baseline_scores.csv")


def price_lookup(panel):
    """Price of every commodity and state in every month it reports, keyed by month."""
    frame = panel[["commodity", "admin1", "mi", "price_kg"]].drop_duplicates(
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

    rows, kept = [], []
    for fold in folds_mod.FOLDS:
        cal = folds_mod.fold_slice(panel, fold, "calibration")
        test = folds_mod.fold_slice(panel, fold, "scored").copy()
        test["fold"] = fold["fold"]
        kept.append(test)
        rows.append(run_fold(cal, test, fold["fold"]))

    scored = pd.concat(kept, ignore_index=True)
    scored[["series", "commodity", "admin1", "mi", "fold", "price_kg", "prev_price_kg",
            "actual_change", "rise", "naive_score", "persistence_score"]].to_csv(OUT, index=False)

    print("fold  cells  rises  covered  threshold  recall   fpr   alerts  MAE naive  MAE persist")
    for r in rows:
        thr = "never" if np.isinf(r["threshold"]) else "%.4f" % r["threshold"]
        print("%-5s %5d  %5d  %7d  %9s  %6.3f  %5.3f  %6d  %9.4f  %11.4f"
              % (r["fold"], r["cells"], r["rises"], r["covered"], thr,
                 r["recall"], r["fpr"], r["alerts"], r["mae_naive"], r["mae_persistence"]))
    print("\nwrote %s (%d scored cells)" % (os.path.relpath(OUT, ROOT), len(scored)))
    print("The seasonal rule cannot cover every cell, so it is scored on the cells where a "
          "year-earlier price exists. Report any model beside it on those same cells.")


if __name__ == "__main__":
    main()
