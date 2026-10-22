"""Write analyst-facing alerts for the last scored month without exposing outcomes."""

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS = os.path.join(ROOT, "outputs")
FOLD_TABLE = os.path.join(OUTPUTS, "fold_table.csv")
PANEL = os.path.join(OUTPUTS, "panel.csv")
OUT = os.path.join(OUTPUTS, "alerts.csv")
MODEL_FILES = {
    "seasonal": ("baseline_scores.csv", "naive_score"),
    "sarima": ("sarima_scores.csv", "score"),
    "lightgbm": ("lightgbm_scores.csv", "score"),
    "lightgbm_fx": ("lightgbm_fx_scores.csv", "score"),
}


def build_alerts(fold_table=None, scored_month=None):
    table = pd.read_csv(fold_table or FOLD_TABLE)
    fold = "3"
    if scored_month is None:
        import folds
        scored_month = folds.mi_of(folds.FOLDS[-1]["scored"][1])
    panel = pd.read_csv(PANEL)
    panel["series"] = panel["commodity"].astype(str) + " | " + panel["admin1"].astype(str)
    meta = panel.loc[panel["mi"].astype(int) == int(scored_month),
                     ["series", "commodity", "admin1", "mi"]].drop_duplicates()
    pieces = []
    for model, (filename, score_column) in MODEL_FILES.items():
        model_threshold = table[(table["model"].astype(str) == model) &
                                (table["fold"].astype(str) == fold)]
        if model_threshold.empty:
            raise SystemExit("no frozen threshold for %s in fold %s" % (model, fold))
        threshold = float(model_threshold.iloc[0]["threshold"])
        path = os.path.join(OUTPUTS, filename)
        if not os.path.exists(path):
            raise SystemExit("missing %s scores at %s" % (model, path))
        scores = pd.read_csv(path)
        if score_column not in scores:
            raise SystemExit("%s lacks score column %s" % (path, score_column))
        selected = scores[scores["mi"].astype(int) == int(scored_month)][
            ["series", "mi", score_column]].rename(columns={score_column: "score"})
        block = meta.merge(selected, on=["series", "mi"], how="inner", validate="one_to_one")
        block["model"] = model
        block["fold"] = fold
        block["threshold"] = threshold
        block["alert"] = block["score"] >= threshold
        pieces.append(block[["model", "fold", "series", "commodity", "admin1", "mi",
                             "score", "threshold", "alert"]])
    if not pieces:
        raise SystemExit("no alerts data was produced")
    result = pd.concat(pieces, ignore_index=True)
    return result.sort_values(["model", "alert", "score"], ascending=[True, False, False])


def main():
    result = build_alerts()
    result.to_csv(OUT, index=False)
    print("wrote %s for outcome month %d: %d forecast rows, %d flags" %
          (os.path.relpath(OUT, ROOT), int(result["mi"].iloc[0]), len(result),
           int(result["alert"].sum())))


if __name__ == "__main__":
    main()
