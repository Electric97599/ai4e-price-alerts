"""Per-series seasonal ARIMA forecast with monthly AIC order selection.

Each score for target month t is forecast from observations through t-1. The fit uses a
rolling window of at most 60 calendar months to keep the per-origin AIC search feasible.
Missing months stay missing in the monthly series and are handled as unobserved states by
SARIMAX; they are never filled or compressed away. A fixed candidate grid is refit at each origin.
"""

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

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


def forecast_one(origin_values, warm_starts=None):
    """Select the lowest-AIC fit and return forecast plus next-origin warm starts.

    Orders are still refit and compared by AIC at every origin. Starting each optimizer
    from the same order's previous-month estimate cuts repeated optimization time.
    """
    warm_starts = {} if warm_starts is None else warm_starts
    candidates = []
    next_starts = dict(warm_starts)
    for order in model_config.SARIMA_ORDERS:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = SARIMAX(
                    origin_values,
                    order=order,
                    seasonal_order=model_config.SARIMA_SEASONAL_ORDER,
                    trend="n",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                    simple_differencing=False,
                )
                start = warm_starts.get(order)
                try:
                    result = model.fit(start_params=start, method="lbfgs", disp=False,
                                       maxiter=model_config.SARIMA_MAXITER if start is None else 12)
                except Exception:
                    if start is None:
                        raise
                    result = model.fit(method="lbfgs", disp=False,
                                       maxiter=model_config.SARIMA_MAXITER)
            if np.isfinite(result.aic):
                candidates.append((float(result.aic), result))
                next_starts[order] = np.asarray(result.params, dtype=float)
        except Exception:
            continue
    if not candidates:
        return None, next_starts
    # A few unstable candidate fits can have finite AIC but overflow when converted
    # into a price-change score. Fall through to the next-lowest-AIC finite forecast.
    for _, result in sorted(candidates, key=lambda item: item[0]):
        try:
            predicted_log_price = float(
                np.asarray(result.get_forecast(steps=1).predicted_mean).reshape(-1)[0])
            with np.errstate(over="ignore", invalid="ignore"):
                score = float(np.expm1(predicted_log_price - origin_values[-1]))
            if np.isfinite(predicted_log_price) and np.isfinite(score):
                return score, next_starts
        except Exception:
            continue
    return None, next_starts


def run(fold_label=None, output=None):
    prices = mf.read_prices()
    store = mf.histories(prices)
    target_months = set(months_for_fold(fold_label))
    panel = pd.read_csv(mf.PANEL)
    panel["mi"] = panel["mi"].astype(int)
    panel = panel[panel["mi"].isin(target_months)]
    panel["series"] = panel["commodity"].astype(str) + " | " + panel["admin1"].astype(str)
    grouped = {(str(c), str(s)): g for (c, s), g in panel.groupby(["commodity", "admin1"], sort=False)}
    rows, skipped_short, failed_fit = [], 0, 0
    all_series = sorted(store)
    done = 0

    for series_index, key in enumerate(all_series, start=1):
        history = store[key]
        series_rows = grouped.get(key)
        if series_rows is None:
            continue
        warm_starts = {}
        for row in series_rows.itertuples(index=False):
            target_mi = int(row.mi)
            origin_mi = target_mi - 1
            if origin_mi not in history:
                continue
            first_mi = max(min(history), origin_mi - model_config.SARIMA_WINDOW_MONTHS + 1)
            observed = [m for m in history if first_mi <= m <= origin_mi]
            if len(observed) < model_config.SARIMA_MIN_OBSERVATIONS:
                skipped_short += 1
                continue
            # Preserve each calendar month on the index. NaN marks a missing observation;
            # no price value is imputed and the seasonal lag remains twelve months.
            endog = np.asarray([np.log(history.get(m, np.nan))
                                for m in range(first_mi, origin_mi + 1)], dtype=float)
            score, warm_starts = forecast_one(endog, warm_starts)
            done += 1
            if score is None:
                failed_fit += 1
                continue
            if np.isfinite(score):
                rows.append({"series": row.series, "mi": target_mi, "score": score})
            else:
                failed_fit += 1
        if series_index % 10 == 0 or series_index == len(all_series):
            print("SARIMA: completed %d/%d eligible series" %
                  (series_index, len(all_series)), flush=True)

    print("SARIMA forecasts fitted: %d; skipped for fewer than %d observations: %d; fit/score failures: %d"
          % (done, model_config.SARIMA_MIN_OBSERVATIONS, skipped_short, failed_fit))
    if not rows:
        raise SystemExit("SARIMA produced no finite forecasts")
    result = contracts.validate_scores(pd.DataFrame(rows), name="sarima")
    if output is None:
        suffix = "_fold%s" % fold_label if fold_label is not None else ""
        output = os.path.join(ROOT, "outputs", "sarima%s_scores.csv" % suffix)
    contracts.write_scores(result, output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", choices=[f["fold"] for f in folds.FOLDS])
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    run(args.fold, args.output)


if __name__ == "__main__":
    main()
