"""Write analyst-facing alerts for the newest month, from saved models only.

Nothing in this script fits a model. It loads the bundle that `src/fit_final.py` wrote and
forecasts one month ahead for every series that quotes at the origin, so the queue in
`app.py` is produced the way the proposal describes a monthly scorer: fits once outside the
app, scores on demand, never retunes.

Two rules of the project are enforced here rather than left to the caller.

* The threshold is the fold 3 value frozen in `outputs/fold_table.csv`. It is read, never
  recomputed, so the month being scored cannot influence it.
* The file carries no outcome column. There is no rise label and no realized price in it,
  so neither the app nor a reviewer can read the answer off the queue.

A scored month here sits outside the six fold windows, so `src/contracts.py` validation is
not applied: that validator exists to keep a model's fold score file honest, and this file
is a forecast, not a fold result.

Output: outputs/alerts.csv    model, fold, series, commodity, admin1, mi, score, threshold, alert

Run:  python src/score_latest.py        (after python src/fit_final.py)
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import baseline           # noqa: E402
import folds              # noqa: E402
import model_features as mf  # noqa: E402
import model_store        # noqa: E402

OUTPUTS = os.path.join(ROOT, "outputs")
FOLD_TABLE = os.path.join(OUTPUTS, "fold_table.csv")
PANEL = os.path.join(OUTPUTS, "panel.csv")
OUT = os.path.join(OUTPUTS, "alerts.csv")
FROZEN_FOLD = "3"


def design(frame, columns, categories):
    """The prediction matrix, with the training category levels rather than the new ones."""
    matrix = frame.reindex(columns=columns).copy()
    for column, levels in categories.items():
        if column in matrix.columns:
            matrix[column] = pd.Categorical(matrix[column].astype(str), categories=levels)
    return matrix


def lightgbm_rows(prices, target_mi, rate_by_month):
    """One prediction row per series that quotes at the forecast origin."""
    histories = mf.histories(prices)
    origin_mi = int(target_mi) - 1
    rows = []
    for (commodity, state), history in sorted(histories.items()):
        if origin_mi not in history:
            continue
        feature = mf.feature_at(commodity, state, target_mi, history, rate_by_month)
        if feature is None:
            continue
        feature["series"] = str(commodity) + " | " + str(state)
        rows.append(feature)
    if not rows:
        raise SystemExit("no series quotes at %s, so no forecast can be issued"
                         % folds.month_label(origin_mi))
    return pd.DataFrame(rows)


def predict(estimator, frame, columns, categories):
    """Predicted percentage change, from a fitted pooled model."""
    if frame.empty:
        return np.asarray([], dtype=float)
    matrix = design(frame, columns, categories)
    with np.errstate(over="ignore", invalid="ignore"):
        scores = np.expm1(estimator.predict(matrix))
    if not np.isfinite(scores).all():
        raise SystemExit("a saved LightGBM model produced a non-finite score")
    return np.asarray(scores, dtype=float)


def sarima_scores(models, origin_mi):
    """One-step forecasts from the saved per-series fits."""
    rows = []
    for series, saved in sorted(models.items()):
        if saved.get("fitted_through") != folds.month_label(int(origin_mi)):
            raise SystemExit("%s was fitted through %s but the origin is %s; rerun "
                             "`python src/fit_final.py`" % (series, saved.get("fitted_through"),
                                                            folds.month_label(int(origin_mi))))
        forecast = saved["result"].get_forecast(steps=1)
        predicted_log_price = float(np.asarray(forecast.predicted_mean).reshape(-1)[0])
        with np.errstate(over="ignore", invalid="ignore"):
            score = float(np.expm1(predicted_log_price - saved["origin_log_price"]))
        if not np.isfinite(score):
            continue
        rows.append({"series": series, "score": score})
    if not rows:
        raise SystemExit("the saved SARIMA fits produced no finite forecast")
    return pd.DataFrame(rows)


def seasonal_scores(prices, target_mi):
    """The seasonal rule needs no fit: the price twelve months earlier over the origin price."""
    price = baseline.price_lookup(pd.read_csv(PANEL))
    origin_mi = int(target_mi) - 1
    rows = []
    for (commodity, state), history in sorted(mf.histories(prices).items()):
        if origin_mi not in history:
            continue
        score = baseline.seasonal_score(price, commodity, state, int(target_mi))
        if score is None or not np.isfinite(score):
            continue
        rows.append({"series": str(commodity) + " | " + str(state), "score": float(score)})
    return pd.DataFrame(rows)


def frozen_thresholds(path=FOLD_TABLE):
    """The fold 3 threshold per rule, as written by the fold harness."""
    if not os.path.exists(path):
        raise SystemExit("run `python src/run_folds.py` for each score file first: the frozen "
                         "thresholds live in %s" % os.path.relpath(path, ROOT))
    table = pd.read_csv(path)
    selected = table[table["fold"].astype(str) == FROZEN_FOLD]
    if selected.empty:
        raise SystemExit("%s has no fold %s rows" % (os.path.relpath(path, ROOT), FROZEN_FOLD))
    return {str(row["model"]): float(row["threshold"]) for _, row in selected.iterrows()}


def assemble(scores_by_model, prices, target_mi, thresholds):
    """Stack the four rules into the alert file, one row per rule and series."""
    names = {"%s | %s" % (commodity, state): (str(commodity), str(state))
             for commodity, state in mf.histories(prices)}
    origin_rows = prices[prices["mi"].astype(int) == int(target_mi) - 1]
    quoted = set(zip(origin_rows["commodity"].astype(str), origin_rows["admin1"].astype(str)))
    pieces = []
    for model, scores in scores_by_model.items():
        if scores.empty:
            continue
        if model not in thresholds:
            raise SystemExit("%s has no frozen threshold in the fold table" % model)
        block = scores.copy()
        unknown = sorted(set(block["series"]) - set(names))
        if unknown:
            raise SystemExit("%d scored series are not in the price file, the first being %s"
                             % (len(unknown), unknown[0]))
        block["commodity"] = [names[series][0] for series in block["series"]]
        block["admin1"] = [names[series][1] for series in block["series"]]
        missing = [series for series, pair in zip(block["series"],
                                                  zip(block["commodity"], block["admin1"]))
                   if pair not in quoted]
        if missing:
            raise SystemExit("%d scored series do not quote at the origin, the first being %s"
                             % (len(missing), missing[0]))
        block["model"] = model
        block["fold"] = FROZEN_FOLD
        block["mi"] = int(target_mi)
        block["threshold"] = thresholds[model]
        block["alert"] = block["score"] >= block["threshold"]
        pieces.append(block[["model", "fold", "series", "commodity", "admin1", "mi", "score",
                             "threshold", "alert"]])
    if not pieces:
        raise SystemExit("no rule produced a forecast for %s" % folds.month_label(int(target_mi)))
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["model", "alert", "score"], ascending=[True, False, False])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", default=None, help="a saved model bundle, default models/final_origin.joblib")
    parser.add_argument("--output", default=None, help="where to write the alert file")
    args = parser.parse_args()

    saved = model_store.load(args.bundle)
    target_mi = int(saved["target_mi"])
    origin_mi = int(saved["origin_mi"])
    if origin_mi != target_mi - 1:
        raise SystemExit("the bundle forecasts month %d from origin %d; one month ahead is "
                         "required" % (target_mi, origin_mi))

    prices = mf.read_prices()
    rate = mf.read_rates()
    rows_plain = lightgbm_rows(prices, target_mi, None)
    rows_fx = lightgbm_rows(prices, target_mi, rate)

    categories = saved["categories"]
    scores = {
        "seasonal": seasonal_scores(prices, target_mi),
        "sarima": sarima_scores(saved["sarima"], origin_mi),
        "lightgbm": pd.DataFrame({
            "series": rows_plain["series"],
            "score": predict(saved["lightgbm"], rows_plain,
                             saved["feature_columns"]["lightgbm"], categories)}),
        "lightgbm_fx": pd.DataFrame({
            "series": rows_fx["series"],
            "score": predict(saved["lightgbm_fx"], rows_fx,
                             saved["feature_columns"]["lightgbm_fx"], categories)}),
    }

    result = assemble(scores, prices, target_mi, frozen_thresholds())
    path = args.output or OUT
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    result.to_csv(path, index=False, lineterminator="\n")

    print("Outcome month %s, forecast from %s, thresholds frozen at fold %s"
          % (folds.month_label(target_mi), folds.month_label(origin_mi), FROZEN_FOLD))
    print("rule          series  flags  threshold")
    for model in ("seasonal", "sarima", "lightgbm", "lightgbm_fx"):
        block = result[result["model"] == model]
        print("%-13s %6d %6d  %9.4f"
              % (model, len(block), int(block["alert"].sum()),
                 float(block["threshold"].iloc[0]) if len(block) else float("nan")))
    print("\nwrote %s (%d rows, no outcome column, nothing fitted here)"
          % (os.path.relpath(path, ROOT), len(result)))


if __name__ == "__main__":
    main()
