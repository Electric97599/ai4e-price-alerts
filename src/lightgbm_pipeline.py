"""Pooled monthly LightGBM forecaster, optionally using the lagged CBN rate.

Forecast for month t is issued at t-1. Every training label ends by t-1 and every
feature is built from observations through t-1. Run without arguments for the full fold
calendar, or pass --fold 1/2/3 for that fold's calibration and scored windows.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import contracts  # noqa: E402
import folds  # noqa: E402
import model_config  # noqa: E402
import model_features as mf  # noqa: E402


def months_for_fold(fold_label=None):
    selected = [f for f in folds.FOLDS if fold_label is None or f["fold"] == str(fold_label)]
    if not selected:
        raise SystemExit("unknown fold %s; choose 1, 2 or 3" % fold_label)
    months = set()
    for fold in selected:
        for part in ("calibration", "scored"):
            start, end = fold[part]
            months.update(range(folds.mi_of(start), folds.mi_of(end) + 1))
    return sorted(months)


def run(with_fx=False, fold_label=None, output=None):
    prices = mf.read_prices()
    rate_map = mf.read_rates() if with_fx else None
    train, y = mf.training_rows(prices, rate_map)
    target_months = months_for_fold(fold_label)
    target = mf.target_rows(prices, target_months, rate_map)
    if target.empty:
        raise SystemExit("no eligible panel cells have the required forecast-origin features")

    features = mf.feature_columns(with_fx)
    predictions = []
    month_values = sorted(target["mi"].unique())
    for index, target_mi in enumerate(month_values, start=1):
        train_mask = train["mi"] < int(target_mi)
        tr = train.loc[train_mask]
        te = target[target["mi"] == target_mi]
        if len(tr) < 30:
            raise SystemExit("only %d historical training examples before %s" %
                             (len(tr), folds.month_label(int(target_mi))))
        train_x = mf.prepare_matrix(tr[features], train)
        test_x = mf.prepare_matrix(te[features], train)
        estimator = LGBMRegressor(**model_config.LGBM_PARAMS)
        estimator.fit(train_x, y[train_mask.to_numpy()], categorical_feature=mf.CATEGORICAL_FEATURES)
        forecast_log_change = estimator.predict(test_x)
        with np.errstate(over="ignore", invalid="ignore"):
            scores = np.expm1(forecast_log_change)
        if not np.isfinite(scores).all():
            raise SystemExit("LightGBM produced a non-finite score for %s" %
                             folds.month_label(int(target_mi)))
        predictions.append(pd.DataFrame({"series": te["series"].to_numpy(),
                                         "mi": int(target_mi), "score": scores}))
        if index % 12 == 0 or index == len(month_values):
            print("%s: forecast month %s (%d/%d)" %
                  ("LightGBM with CBN rate" if with_fx else "LightGBM",
                   folds.month_label(int(target_mi)), index, len(month_values)))

    result = contracts.validate_scores(pd.concat(predictions, ignore_index=True),
                                       name="lightgbm_fx" if with_fx else "lightgbm")
    if output is None:
        stem = "lightgbm_fx" if with_fx else "lightgbm"
        suffix = "_fold%s" % fold_label if fold_label is not None else ""
        output = os.path.join(ROOT, "outputs", stem + suffix + "_scores.csv")
    contracts.write_scores(result, output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-fx", action="store_true", help="add the rate known through the forecast origin")
    parser.add_argument("--fold", choices=[f["fold"] for f in folds.FOLDS])
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    run(args.with_fx, args.fold, args.output)


if __name__ == "__main__":
    main()
