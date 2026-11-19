"""Create penalty sensitivity and subgroup tables from frozen fold thresholds."""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import folds  # noqa: E402
import metrics  # noqa: E402

FOLD_TABLE = os.path.join(ROOT, "outputs", "fold_table.csv")
PANEL = os.path.join(ROOT, "outputs", "panel.csv")
SCORES_DIR = os.path.join(ROOT, "outputs")
TABLES = os.path.join(ROOT, "docs", "tables")
OUT = os.path.join(ROOT, "outputs", "report_tables.csv")
MODEL_FILES = {
    "seasonal": ("baseline_scores.csv", "naive_score"),
    "sarima": ("sarima_scores.csv", "score"),
    "lightgbm": ("lightgbm_scores.csv", "score"),
    "lightgbm_fx": ("lightgbm_fx_scores.csv", "score"),
}


def load_fold_table(path=FOLD_TABLE):
    if not os.path.exists(path):
        raise SystemExit("run the fold harness first: missing %s" % path)
    table = pd.read_csv(path)
    required = {"model", "fold", "threshold"}
    if not required.issubset(table.columns):
        raise SystemExit("fold table is missing %s" % ", ".join(sorted(required - set(table.columns))))
    return table


def load_cells(model, fold, threshold):
    filename, score_column = MODEL_FILES[model]
    path = os.path.join(SCORES_DIR, filename)
    if not os.path.exists(path):
        raise SystemExit("missing model score file: %s" % path)
    scores = pd.read_csv(path)
    if score_column not in scores:
        raise SystemExit("%s has no %s score column" % (path, score_column))
    if model == "seasonal":
        scores = scores[["series", "mi", score_column]].rename(columns={score_column: "score"})
    else:
        scores = scores[["series", "mi", score_column]].rename(columns={score_column: "score"})
    panel = pd.read_csv(PANEL)
    panel["series"] = panel["commodity"].astype(str) + " | " + panel["admin1"].astype(str)
    cells = panel[["series", "commodity", "admin1", "mi", "rise"]].merge(
        scores, on=["series", "mi"], how="left", validate="one_to_one")
    fold_def = next((f for f in folds.FOLDS if f["fold"] == str(fold)), None)
    if fold_def is None:
        raise SystemExit("unknown fold %s" % fold)
    cells = folds.fold_slice(cells, fold_def, "scored")
    cells["alert"] = cells["score"].notna() & (cells["score"] >= float(threshold))
    return cells


def penalty_table(fold_table, k_values=(1, 3, 5)):
    """Evaluate penalties on covered, all, and identical common scored cells.

    The common-cell comparison intersects available (series, mi) forecasts within
    each fold. Each rule keeps the threshold calibrated by the fold harness.
    An uncovered all-cell observation is treated as a missed alert, not dropped.
    """
    cached = {}
    for record in fold_table.to_dict("records"):
        model, fold = str(record["model"]), str(record["fold"])
        if model not in MODEL_FILES:
            continue
        key = (model, fold)
        if key in cached:
            raise SystemExit("duplicate model/fold in fold table: %s fold %s" % key)
        cached[key] = (record, load_cells(model, fold, record["threshold"]))

    common_keys = {}
    for fold in sorted({f for _, f in cached}):
        available = [
            set(zip(cells.loc[cells["score"].notna(), "series"],
                    cells.loc[cells["score"].notna(), "mi"]))
            for (model, f), (record, cells) in cached.items() if f == fold
        ]
        common_keys[fold] = set.intersection(*available) if available else set()

    rows = []
    for (model, fold), (record, cells) in cached.items():
        threshold = float(record["threshold"])
        covered = cells[cells["score"].notna()].copy()
        common = covered[
            pd.MultiIndex.from_frame(covered[["series", "mi"]]).isin(common_keys[fold])
        ]
        covered_alerts = covered["alert"].to_numpy(dtype=bool)
        covered_rises = covered["rise"].to_numpy(dtype=int)
        all_alerts = cells["alert"].to_numpy(dtype=bool)
        all_rises = cells["rise"].to_numpy(dtype=int)
        common_alerts = common["alert"].to_numpy(dtype=bool)
        common_rises = common["rise"].to_numpy(dtype=int)
        covered_counts = metrics.confusion(covered["score"], covered_rises, threshold) if len(covered) else {
            "tp": 0, "fp": 0, "fn": 0, "tn": 0}
        common_counts = metrics.confusion(common["score"], common_rises, threshold) if len(common) else {
            "tp": 0, "fp": 0, "fn": 0, "tn": 0}

        for k in k_values:
            rows.append({
                "table": "penalty", "model": model, "fold": fold, "k": int(k),
                "all_scored_cells": len(cells), "covered_cells": len(covered),
                "coverage_percent": 100.0 * len(covered) / len(cells) if len(cells) else np.nan,
                "common_scored_cells": len(common),
                "common_rises": int(common_rises.sum()),
                "alerts": int(covered_alerts.sum()),
                "missed_rises_covered": covered_counts["fn"],
                "missed_rises_all": int((~all_alerts & (all_rises == 1)).sum()),
                "missed_rises_common": common_counts["fn"],
                "false_alarms": covered_counts["fp"],
                "false_alarms_common": common_counts["fp"],
                "penalty_per_1000_covered": metrics.weighted_penalty(
                    covered_alerts, covered_rises, k=k) if len(covered) else np.nan,
                "penalty_per_1000_all_cells": metrics.weighted_penalty(
                    all_alerts, all_rises, k=k) if len(cells) else np.nan,
                "penalty_per_1000_common": metrics.weighted_penalty(
                    common_alerts, common_rises, k=k) if len(common) else np.nan,
                "penalty_basis": "Assumed weights; compare models on the common-cell result",
            })
    penalty = pd.DataFrame(rows)
    if not penalty.empty:
        penalty["rank_common"] = (penalty.groupby(["fold", "k"])["penalty_per_1000_common"]
                                   .rank(ascending=True, method="min").astype("Int64"))
    return penalty

def subgroup_table(fold_table):
    """State by fold and state/commodity across-fold groups; no small groups are pooled."""
    rows = []
    for record in fold_table.to_dict("records"):
        model = str(record["model"])
        if model not in MODEL_FILES:
            continue
        cells = load_cells(model, str(record["fold"]), record["threshold"])
        for by in ("admin1", "commodity"):
            for group, block in cells.groupby(by, dropna=False, sort=True):
                scored = block[block["score"].notna()]
                if len(scored):
                    alert = scored["alert"].to_numpy(dtype=bool)
                    rise = scored["rise"].to_numpy(dtype=int)
                    tp = int((alert & (rise == 1)).sum())
                    fp = int((alert & (rise == 0)).sum())
                    fn = int((~alert & (rise == 1)).sum())
                    nonrise = int((rise == 0).sum())
                    recall = tp / (tp + fn) if tp + fn else np.nan
                    fpr = fp / nonrise if nonrise else 0.0
                else:
                    tp = fp = fn = 0
                    recall = fpr = np.nan
                rows.append({
                    "table": "subgroup", "model": model, "group_by": by,
                    "window": str(record["fold"]), "group": str(group),
                    "cells": len(block), "coverage": len(scored),
                    "coverage_percent": 100 * len(scored) / len(block) if len(block) else np.nan,
                    "rises_all": int(block["rise"].sum()),
                    "rises_covered": int(scored["rise"].sum()),
                    "alerts": int(scored["alert"].sum()), "true_positives": tp,
                    "false_alarms": fp, "missed_rises_covered": fn,
                    "recall_covered": recall, "realized_fpr_covered": fpr,
                })

    # Pooled rows across folds are additive counts, not averages of fold percentages.
    base = pd.DataFrame(rows)
    pooled = []
    for (model, by, group), block in base.groupby(["model", "group_by", "group"], sort=True):
        covered = int(block["coverage"].sum())
        rises_cov = int(block["rises_covered"].sum())
        tp = int(block["true_positives"].sum())
        fp = int(block["false_alarms"].sum())
        missed = int(block["missed_rises_covered"].sum())
        nonrise = covered - rises_cov
        pooled.append({
            "table": "subgroup", "model": model, "group_by": by, "window": "pooled",
            "group": group, "cells": int(block["cells"].sum()), "coverage": covered,
            "coverage_percent": 100 * covered / block["cells"].sum() if block["cells"].sum() else np.nan,
            "rises_all": int(block["rises_all"].sum()), "rises_covered": rises_cov,
            "alerts": int(block["alerts"].sum()), "true_positives": tp,
            "false_alarms": fp, "missed_rises_covered": missed,
            "recall_covered": tp / rises_cov if rises_cov else np.nan,
            "realized_fpr_covered": fp / nonrise if nonrise else 0.0,
        })
    return pd.concat([base, pd.DataFrame(pooled)], ignore_index=True)


def markdown_table(frame, columns):
    if frame.empty:
        return "(No rows.)"
    def render(value):
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return "%.3f" % value
        return str(value).replace("|", "\\|").replace("\n", " ")
    header = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(render(value) for value in row) + " |"
            for row in frame[columns].itertuples(index=False, name=None)]
    return "\n".join([header, rule] + body)


def main():
    fold_table = load_fold_table()
    penalty = penalty_table(fold_table)
    subgroup = subgroup_table(fold_table)
    os.makedirs(TABLES, exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    all_rows = pd.concat([penalty, subgroup], ignore_index=True, sort=False)
    all_rows.to_csv(OUT, index=False)
    penalty_md = "# Weighted decision penalty\n\n"
    penalty_md += (
        "Weights at k = 1, 3 and 5 are assumptions, not measured procurement costs. "
        "Every rule uses its original threshold, frozen on calibration cells. "
        "The common-cell result uses the intersection of scored (series, month) pairs "
        "across the rules in each fold, making model rankings directly comparable. "
        "The covered-cell result describes each rule's own coverage and should not be "
        "ranked against other rules with different coverage. The all-cell result treats "
        "an uncovered cell as no alert, counting an actual rise as missed. "
        "Every row reports its denominators; lower penalty is better.\n\n"
    )
    rankings = []
    for (fold, k), group in penalty.groupby(["fold", "k"], sort=True):
        ordered = group.sort_values(["penalty_per_1000_common", "model"])
        ranking = ", ".join("%s (%.3f)" % (row.model, row.penalty_per_1000_common)
                            for row in ordered.itertuples()
                            if np.isfinite(row.penalty_per_1000_common))
        rankings.append({"fold": fold, "k": k,
                         "common_scored_cells": int(group["common_scored_cells"].iloc[0]),
                         "ranking_best_to_worst": ranking or "no common cells"})
    penalty_md += "## Model rankings on common cells\n\n"
    penalty_md += markdown_table(pd.DataFrame(rankings),
                                  ["fold", "k", "common_scored_cells", "ranking_best_to_worst"])
    penalty_md += "\n\n## All penalty calculations\n\n"
    penalty_md += markdown_table(penalty, ["model", "fold", "k", "all_scored_cells",
                                            "covered_cells", "coverage_percent",
                                            "common_scored_cells", "common_rises", "alerts",
                                            "missed_rises_covered", "missed_rises_all",
                                            "missed_rises_common", "false_alarms",
                                            "false_alarms_common", "penalty_per_1000_covered",
                                            "penalty_per_1000_all_cells",
                                            "penalty_per_1000_common", "rank_common"])
    with open(os.path.join(TABLES, "penalty.md"), "w", encoding="utf-8") as fh:
        fh.write(penalty_md + "\n")
    subgroup_md = "# Subgroup results\n\n"
    subgroup_md += "Each row shows its full cell count and forecast coverage. Rates use covered cells. No small groups are combined; pooled rows sum the same group across folds before calculating rates.\n\n"
    subgroup_md += markdown_table(subgroup, ["model", "group_by", "window", "group", "cells", "coverage",
                                              "coverage_percent", "rises_all", "rises_covered", "alerts",
                                              "recall_covered", "realized_fpr_covered"])
    with open(os.path.join(TABLES, "subgroups.md"), "w", encoding="utf-8") as fh:
        fh.write(subgroup_md + "\n")
    print("penalty rows: %d; subgroup rows: %d" % (len(penalty), len(subgroup)))
    print("wrote %s, docs/tables/penalty.md and docs/tables/subgroups.md" %
          os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
