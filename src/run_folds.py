"""Calibrate each rule on its 12-month calibration window and score the next 12 months.

Score files must contain one row per predicted cell in *both* calibration and scored
windows. A missing score is retained as a coverage gap. Threshold selection uses only
available calibration scores; thresholds are frozen before scored months are evaluated.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import contracts  # noqa: E402
import folds as folds_mod  # noqa: E402
import metrics  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "fold_table.csv")
PANEL = os.path.join(ROOT, "outputs", "panel.csv")
REFERENCE = os.path.join(ROOT, "outputs", "baseline_scores.csv")


def load_scores(path, column=None):
    """Load and validate forecast scores. Missing rows represent uncovered cells."""
    frame = pd.read_csv(path)
    if column:
        if column not in frame.columns:
            raise SystemExit("%s has no `%s` column; available: %s" %
                             (path, column, ", ".join(frame.columns)))
        frame = frame.rename(columns={column: "score"})
        # The seasonal reference intentionally has NaN where a year-earlier price is
        # absent. Turn those into omitted rows so contracts can enforce the standard
        # finite-score format and the merge below still reports the coverage gap.
        if column == "naive_score" and frame["score"].isna().any():
            missing = int(frame["score"].isna().sum())
            print("note: dropped %d seasonal rows without a year-earlier price" % missing)
            frame = frame[frame["score"].notna()].copy()
    return contracts.validate_scores(frame, name=os.path.basename(path))


def all_cells():
    """Full label universe plus actual changes and common reference predictions."""
    panel = pd.read_csv(PANEL)
    panel["series"] = folds_mod.series_key(panel)
    panel["actual_change"] = panel["price_kg"] / panel["prev_price_kg"] - 1.0
    keep = ["series", "commodity", "admin1", "mi", "rise", "actual_change"]
    cells = panel[keep].copy()
    if not os.path.exists(REFERENCE):
        raise SystemExit("run `python src/baseline.py` first: reference scores are missing")
    ref = pd.read_csv(REFERENCE)
    required = {"series", "mi", "naive_score", "persistence_score"}
    if not required.issubset(ref.columns):
        raise SystemExit("%s is missing reference columns: %s" %
                         (REFERENCE, ", ".join(sorted(required - set(ref.columns)))))
    return cells.merge(ref[["series", "mi", "naive_score", "persistence_score"]],
                       on=["series", "mi"], how="left", validate="one_to_one")


def score_fold(cells, fold, model):
    """Return fold results, retaining full denominator and reporting model coverage."""
    print("scoring %s fold %s" % (model, fold["fold"]), flush=True)
    cal = folds_mod.fold_slice(cells, fold, "calibration")
    test = folds_mod.fold_slice(cells, fold, "scored")
    cal = cal[cal["score"].notna()]
    test_covered = test[test["score"].notna()].copy()
    if cal.empty:
        raise SystemExit("%s fold %s has no calibration scores" % (model, fold["fold"]))
    if test.empty:
        raise SystemExit("fold %s has no scored labels" % fold["fold"])

    threshold = metrics.choose_threshold(cal["score"], cal["rise"])
    print("  calibrated on %d covered rows" % len(cal), flush=True)
    alert = (test_covered["score"].to_numpy(dtype=float) >= threshold)
    covered_rises = test_covered["rise"].to_numpy(dtype=int)
    confusion = metrics.confusion(test_covered["score"], covered_rises, threshold)
    scored_rises = test["rise"].to_numpy(dtype=int)

    # The headline rates use the cells the rule actually scored. Full cell and rise
    # counts remain beside them so coverage differences cannot be mistaken for success.
    mae_model = metrics.mean_absolute_error(test_covered["actual_change"],
                                            test_covered["score"]) if len(test_covered) else np.nan
    naive_common = test_covered.dropna(subset=["naive_score"])
    mae_naive = metrics.mean_absolute_error(naive_common["actual_change"],
                                            naive_common["naive_score"]) if len(naive_common) else np.nan
    mae_persistence = metrics.mean_absolute_error(test_covered["actual_change"],
                                                 test_covered["persistence_score"]) if len(test_covered) else np.nan
    pr_auc = (metrics.precision_recall_area(test_covered["score"], covered_rises)
              if len(test_covered) and covered_rises.sum() else np.nan)
    print("  scored %d/%d rows" % (len(test_covered), len(test)), flush=True)
    result = {
        "model": model,
        "fold": str(fold["fold"]),
        "calibration_cells": len(folds_mod.fold_slice(cells, fold, "calibration")),
        "calibration_coverage": len(cal),
        "cells": len(test),
        "rises": int(test["rise"].sum()),
        "coverage": len(test_covered),
        "rises_covered": int(covered_rises.sum()),
        "threshold": threshold,
        "alerts": int(alert.sum()),
        "recall": metrics.recall(test_covered["score"], covered_rises, threshold)
                  if len(test_covered) else np.nan,
        "realized_fpr": metrics.false_positive_rate(test_covered["score"], covered_rises,
                                                    threshold) if len(test_covered) else np.nan,
        "precision_recall_area": pr_auc,
        "mae_model": mae_model,
        "mae_naive_common": mae_naive,
        "mae_persistence_common": mae_persistence,
        # Persistence covers every outcome cell. Keep this all-cell value so the
        # reference output still matches baseline.py, and show the common-cell value too.
        "mae_persistence": metrics.mean_absolute_error(
            test["actual_change"], test["persistence_score"]),
        "mae_naive_cells": len(naive_common),
        "penalty_covered_cells": len(test_covered),
    }
    for k in (1, 3, 5):
        result["penalty_k%d" % k] = (metrics.weighted_penalty(alert, covered_rises, k=k)
                                     if len(test_covered) else np.nan)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True, help="score CSV covering calibration and scored months")
    parser.add_argument("--column", default=None, help="score column name when the file has several")
    parser.add_argument("--model", default=None, help="display name; defaults to score filename")
    parser.add_argument("--output", default=OUT, help="fold table CSV path")
    args = parser.parse_args()

    score_path = args.scores if os.path.isabs(args.scores) else os.path.join(ROOT, args.scores)
    out_path = args.output if os.path.isabs(args.output) else os.path.join(ROOT, args.output)
    score_frame = load_scores(score_path, args.column)
    print("loaded %d validated forecasts" % len(score_frame), flush=True)
    model = args.model or os.path.splitext(os.path.basename(score_path))[0].replace("_scores", "")
    cells = all_cells().merge(score_frame, on=["series", "mi"], how="left", validate="one_to_one")
    print("joined forecasts to %d label cells" % len(cells), flush=True)

    rows = []
    for fold in folds_mod.FOLDS:
        rows.append(score_fold(cells, fold, model))
    table = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    table.to_csv(out_path, index=False)
    print(table.to_string(index=False))
    print("\nwrote %s" % os.path.relpath(out_path, ROOT))


if __name__ == "__main__":
    main()
