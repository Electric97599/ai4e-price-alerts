"""Starter for issue #6: the fold runner every model reports through.

Owner: Bizima. Sheet: docs/on-ramp/bizima.md. Rules: AGENTS.md.

The mechanical parts are written for you: argument parsing, loading and validating a
score file, joining the rise labels, slicing each fold, and printing the table. The part
left to you is marked TODO(#6) below.

What this script must do, once you are done
-------------------------------------------
For each of the three folds in src/folds.py:

1. Choose a threshold on CALIBRATION cells only, with metrics.choose_threshold. Never pass
   a scored month to it.
2. Freeze that threshold and apply it to the scored cells.
3. Report: cells, rises, coverage, threshold, recall, realized false positive rate, alerts,
   precision recall area, mean absolute error against persistence and the seasonal rule on
   the cells they share, and the weighted penalty at k = 1, 3 and 5.
4. Write outputs/fold_table.csv.

The proof that it works
-----------------------
    python src/run_folds.py --scores outputs/baseline_scores.csv --column naive_score

must reproduce, to three decimals, what `python src/baseline.py` prints. The `--column`
flag exists because the reference file carries more than one score; a model file will just
have `score`.

Run:  python src/run_folds.py --scores outputs/baseline_scores.csv --column naive_score
"""

import argparse
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import contracts          # noqa: E402
import folds as folds_mod  # noqa: E402
import metrics            # noqa: E402

OUT = os.path.join(ROOT, "outputs", "fold_table.csv")


def load_scores(path, column=None):
    """Read a score file, rename the chosen score column to `score`, and validate.

    Rows with no score are dropped with a printed count, because a rule may legitimately
    cover fewer cells than the panel holds (the seasonal rule needs a year-earlier price).
    A NaN is only a failure when a model claims to cover every cell, and that check belongs
    in contracts.write_scores on the writing side.
    """
    frame = pd.read_csv(path)
    if column:
        if column not in frame.columns:
            raise SystemExit("%s has no column `%s`; it has %s"
                             % (path, column, ", ".join(frame.columns)))
        frame = frame.rename(columns={column: "score"})
    elif "score" not in frame.columns:
        candidates = [c for c in frame.columns if c not in ("series", "mi")]
        raise SystemExit("%s has no `score` column. Options: %s. Pass one with --column."
                         % (path, ", ".join(candidates)))
    missing = int(frame["score"].isna().sum())
    if missing:
        frame = frame[frame["score"].notna()]
        print("note: %d rows carry no score and were dropped, which is that rule's coverage gap"
              % missing)
    return contracts.validate_scores(frame, name=os.path.basename(path))


def reference_columns(labels):
    """The seasonal and persistence predictions, so every model is compared like for like.

    baseline_scores.csv already carries both, keyed the same way, so read it rather than
    recomputing them here.
    """
    path = os.path.join(ROOT, "outputs", "baseline_scores.csv")
    if not os.path.exists(path):
        raise SystemExit("run `python src/baseline.py` first: it writes the reference columns")
    ref = pd.read_csv(path)[["series", "mi", "naive_score", "persistence_score", "actual_change"]]
    return labels.merge(ref, on=["series", "mi"], how="left")


def score_fold(cells, fold_label, k_values=(1, 3, 5)):
    """Threshold on calibration cells, freeze it, score the scored cells.

    TODO(#6): implement this. It is the whole task. Shape of the returned dict:

        {"fold": "1", "cells": 472, "rises": 181, "coverage": 230, "threshold": 0.2417,
         "alerts": 8, "recall": 0.056, "realized_fpr": 0.021, "pr_auc": ...,
         "mae_model": ..., "mae_naive": ..., "mae_persistence": ...,
         "penalty_k1": ..., "penalty_k3": ..., "penalty_k5": ...}

    `cells` may hold two or three rows per fold once models exist; select with
    cells["part"] == "calibration" and == "scored". The part column is added by main()
    below, so use it rather than re-deriving the windows.
    """
    raise NotImplementedError("issue #6: score one fold, see the docstring in src/run_folds.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True, help="a series, mi, score CSV")
    parser.add_argument("--column", default=None,
                        help="which column holds the score, when the file has more than one")
    args = parser.parse_args()

    score_path = args.scores if os.path.isabs(args.scores) else os.path.join(ROOT, args.scores)
    scores = load_scores(score_path, args.column)
    labels = contracts.read_labels()
    joined = scores.merge(labels, on=["series", "mi"], how="inner")
    if joined.empty:
        raise SystemExit("no score row matched a rise label: check the series format and mi")

    cells = joined.merge(
        reference_columns(labels)[["series", "mi", "naive_score", "persistence_score",
                                   "actual_change"]],
        on=["series", "mi"], how="left")

    rows = []
    for fold in folds_mod.FOLDS:
        scored = folds_mod.fold_slice(cells, fold, "scored")
        calibration = folds_mod.fold_slice(cells, fold, "calibration")
        block = pd.concat([calibration.assign(part="calibration"),
                           scored.assign(part="scored")], ignore_index=True)
        if block.empty:
            print("fold %s has no cells in this score file" % fold["fold"])
            continue
        rows.append(score_fold(block, fold["fold"]))

    table = pd.DataFrame(rows)
    if table.empty:
        raise SystemExit("no fold produced a result: the score file covers none of the fold "
                         "windows, so nothing was written")
    table.to_csv(OUT, index=False)
    print(table.to_string(index=False))
    print("\nwrote %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as todo:
        print("Not built yet:", todo)
        print("See the docstring at the top of this file, and your sheet in docs/on-ramp/.")
        raise SystemExit(2)
