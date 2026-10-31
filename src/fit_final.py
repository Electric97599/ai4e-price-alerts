"""Fit the learned rules once at the newest origin and save them with joblib.

The fold calendar in `src/folds.py` stops at 2026-06, so the score files behind the fold
table cannot answer the question an analyst asks in October: what does the rule say about
this month. This script fits each learned rule on everything through the newest origin, at
the same settings the folds use, and writes one bundle with `src/model_store.py`.
`src/score_latest.py` then turns that bundle into the alert queue and never fits anything,
which is the clause issue #4 asks for.

The seasonal rule needs no fit. It is arithmetic on two observed prices, so
`src/score_latest.py` computes it directly and this script leaves it alone.

Fitting here is deliberately identical to the fold loop: the LightGBM label set is every
observed one-step change up to the origin, with the same feature list, and each SARIMA
series re-selects its order by AIC over the same five-candidate grid on the same 60 month
window. Nothing is retuned on the newer data, because a threshold or an order chosen on the
month being scored would break the calibration rule the project exists to test.

Output: models/final_origin.joblib

Run:  python src/fit_final.py                     # newest month with an observed price
      python src/fit_final.py --target-month 2026-11
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

import folds              # noqa: E402
import model_config       # noqa: E402
import model_features as mf  # noqa: E402
import model_store        # noqa: E402
import sarima             # noqa: E402


def newest_target(prices):
    """The newest month the price file reports, which is the month the queue should show."""
    return int(prices["mi"].max())


def fit_lightgbm(prices, rate_by_month, origin_mi, with_fx=False):
    """Fit one pooled model on every one-step example labelled through the origin."""
    train, labels = mf.training_rows(prices, rate_by_month)
    mask = (train["mi"] <= int(origin_mi)).to_numpy()
    used = train.loc[mask]
    if len(used) < 30:
        raise SystemExit("only %d one-step examples exist through %s, too few to fit"
                         % (len(used), folds.month_label(int(origin_mi))))
    features = mf.feature_columns(with_fx)
    matrix = mf.prepare_matrix(used[features], train)
    estimator = LGBMRegressor(**model_config.LGBM_PARAMS)
    estimator.fit(matrix, labels[mask], categorical_feature=mf.CATEGORICAL_FEATURES)
    print("%s: fitted on %d one-step examples through %s"
          % ("LightGBM with CBN rate" if with_fx else "LightGBM", len(used),
             folds.month_label(int(origin_mi))))
    return estimator, features, len(used)


def fit_sarima(prices, origin_mi):
    """Fit one SARIMA per series at the origin, keeping the AIC choice each series made."""
    histories = mf.histories(prices)
    fitted = {}
    skipped_short, failed_fit = 0, 0
    keys = sorted(histories)
    for index, key in enumerate(keys, start=1):
        history = histories[key]
        if int(origin_mi) not in history:
            continue
        first_mi = max(min(history), int(origin_mi) - model_config.SARIMA_WINDOW_MONTHS + 1)
        observed = [m for m in history if first_mi <= m <= int(origin_mi)]
        if len(observed) < model_config.SARIMA_MIN_OBSERVATIONS:
            skipped_short += 1
            continue
        # Same calendar-indexed window as the fold loop: NaN marks a missing month and is
        # never replaced, so the seasonal lag stays twelve months.
        endog = np.asarray([np.log(history.get(m, np.nan))
                            for m in range(first_mi, int(origin_mi) + 1)], dtype=float)
        result, order, score, _ = sarima.select_fit(endog)
        if result is None:
            failed_fit += 1
            continue
        fitted[str(key[0]) + " | " + str(key[1])] = {
            "order": [int(x) for x in order],
            "origin_log_price": float(endog[-1]),
            "fitted_through": folds.month_label(int(origin_mi)),
            "result": result,
        }
        if index % 10 == 0 or index == len(keys):
            print("SARIMA: fitted %d/%d series" % (index, len(keys)), flush=True)
    print("SARIMA models saved: %d; skipped for fewer than %d observations: %d; fit failures: %d"
          % (len(fitted), model_config.SARIMA_MIN_OBSERVATIONS, skipped_short, failed_fit))
    if not fitted:
        raise SystemExit("no SARIMA series could be fitted at this origin")
    return fitted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-month", default=None,
                        help="outcome month as YYYY-MM; default is the newest month in the "
                             "price file, so the fits see everything published so far")
    parser.add_argument("--output", default=None, help="where to write the bundle")
    args = parser.parse_args()

    prices = mf.read_prices()
    target_mi = (newest_target(prices) if args.target_month is None
                 else folds.mi_of(args.target_month))
    origin_mi = target_mi - 1
    observed = sum(1 for history in mf.histories(prices).values() if origin_mi in history)
    print("target month %s, fitted through %s, %d series quote at the origin"
          % (folds.month_label(target_mi), folds.month_label(origin_mi), observed))

    rate = mf.read_rates()
    lightgbm, features_plain, rows_plain = fit_lightgbm(prices, None, origin_mi, with_fx=False)
    lightgbm_fx, features_fx, rows_fx = fit_lightgbm(prices, rate, origin_mi, with_fx=True)
    sarima_models = fit_sarima(prices, origin_mi)

    train, _ = mf.training_rows(prices, None)
    categories = {column: sorted(train[column].dropna().astype(str).unique())
                  for column in mf.CATEGORICAL_FEATURES}

    bundle = {
        "origin_mi": int(origin_mi),
        "target_mi": int(target_mi),
        "feature_columns": {"lightgbm": features_plain, "lightgbm_fx": features_fx},
        "categories": {key: [str(x) for x in values] for key, values in categories.items()},
        "lightgbm": lightgbm,
        "lightgbm_fx": lightgbm_fx,
        "sarima": sarima_models,
        "training_rows": {"lightgbm": rows_plain, "lightgbm_fx": rows_fx},
        "settings": {"lightgbm": dict(model_config.LGBM_PARAMS),
                     "sarima_orders": [list(order) for order in model_config.SARIMA_ORDERS],
                     "sarima_seasonal_order": list(model_config.SARIMA_SEASONAL_ORDER),
                     "sarima_min_observations": model_config.SARIMA_MIN_OBSERVATIONS,
                     "sarima_window_months": model_config.SARIMA_WINDOW_MONTHS},
        "versions": model_store.versions(),
    }
    model_store.save(bundle, args.output)
    print("%d SARIMA fits, 2 LightGBM fits, saved for target month %s"
          % (len(sarima_models), folds.month_label(target_mi)))


if __name__ == "__main__":
    main()
