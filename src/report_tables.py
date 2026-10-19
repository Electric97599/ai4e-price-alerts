"""Starter for issue #8: the penalty sensitivity and the subgroup tables.

Owner: Dufitumukiz. Sheet: docs/on-ramp/dufitumukiz.md. Rules: AGENTS.md.

Input : outputs/fold_table.csv  (written by src/run_folds.py)
Output: docs/tables/penalty.md, docs/tables/subgroups.md, outputs/report_tables.csv

Two things the report needs and nobody else builds:

1. The weighted penalty at k = 1, 3 and 5, so a reader can see the ranking survive or fail
   rather than trusting one assumed weight. Use metrics.weighted_penalty; do not reimplement
   it. Every table states that the weights are assumptions, not measured costs.
2. Subgroups: by state inside each window, and state and commodity pooled across the three
   windows. Compute the group sizes BEFORE choosing a pooling threshold: about 472 cells
   over 44 series is roughly eleven each, so a "pool groups under 30 cells" rule would
   collapse the whole table.

Run:  python src/report_tables.py
"""

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import metrics  # noqa: E402

FOLD_TABLE = os.path.join(ROOT, "outputs", "fold_table.csv")
SCORES = os.path.join(ROOT, "outputs", "baseline_scores.csv")
TABLES = os.path.join(ROOT, "docs", "tables")
OUT = os.path.join(ROOT, "outputs", "report_tables.csv")


def load_fold_table(path=FOLD_TABLE):
    if not os.path.exists(path):
        raise SystemExit("run `python src/run_folds.py --scores ...` first: it writes %s"
                         % os.path.relpath(path, ROOT))
    frame = pd.read_csv(path)
    if "coverage" not in frame.columns:
        raise SystemExit("%s has no coverage column; ask Bizima for the #6 output shape"
                         % os.path.relpath(path, ROOT))
    return frame


def penalty_table(fold_table, k_values=(1, 3, 5)):
    """One row per fold and k, from the frozen alerts.

    TODO(#8): implement. The fold table gives recall and realized_fpr, which are not
    enough to recompute a penalty, so read the per cell alerts from the score file instead:
    alert is score >= the frozen threshold for that fold. Return a frame with fold, k,
    alerts, missed_rises, false_alarms and penalty_per_1000.
    """
    raise NotImplementedError("issue #8: build the penalty table at k = 1, 3 and 5")


def subgroup_table(scores, by="state"):
    """Cell counts and error rates by state inside a window, and pooled across windows.

    TODO(#8): implement. Print the group sizes first, then choose the pooling rule from the
    sizes that exist. Never pool silently: a table whose every row says "pooled" answers
    nothing.
    """
    raise NotImplementedError("issue #8: build the subgroup tables")


def main():
    fold_table = load_fold_table()
    print(fold_table.to_string(index=False))
    penalty = penalty_table(fold_table)
    print(penalty.to_string(index=False))
    os.makedirs(TABLES, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    penalty.to_csv(OUT, index=False)
    print("wrote %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as todo:
        print("Not built yet:", todo)
        print("See the docstring at the top of this file, and your sheet in docs/on-ramp/.")
        raise SystemExit(2)
