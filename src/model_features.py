"""Shared, causal features for the pooled LightGBM model variants.

Features for target month t are built entirely from observed prices through t-1. Gaps
remain absent: exact monthly lags become missing, and trailing averages use only prices
that were actually observed inside their calendar window.
"""

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MONTHLY = os.path.join(ROOT, "outputs", "monthly.csv")
PANEL = os.path.join(ROOT, "outputs", "panel.csv")
FX_MONTHLY = os.path.join(ROOT, "data", "nigeria", "cbn_nfem_usd_monthly.csv")

NUMERIC_FEATURES = [
    "target_month", "log_price_lag1", "log_price_lag2", "log_price_lag3",
    "change_lag1", "change_lag2", "change_lag3", "mean_log_price_3",
    "mean_log_price_12", "observations_3", "observations_12",
]
CATEGORICAL_FEATURES = ["admin1", "commodity"]


def read_prices(path=MONTHLY):
    frame = pd.read_csv(path)
    required = {"commodity", "admin1", "mi", "price_kg"}
    if not required.issubset(frame.columns):
        raise SystemExit("%s is missing monthly price columns: %s" %
                         (path, ", ".join(sorted(required - set(frame.columns)))))
    frame["mi"] = frame["mi"].astype(int)
    frame["price_kg"] = pd.to_numeric(frame["price_kg"], errors="coerce")
    frame = frame.dropna(subset=["price_kg"])
    frame = frame[frame["price_kg"] > 0]
    if frame.duplicated(["commodity", "admin1", "mi"]).any():
        raise SystemExit("monthly prices contain duplicate commodity/state/month rows")
    return frame.sort_values(["commodity", "admin1", "mi"]).reset_index(drop=True)


def read_rates(path=FX_MONTHLY):
    rate = pd.read_csv(path)
    if not {"month", "ngn_per_usd"}.issubset(rate.columns):
        raise SystemExit("%s needs month and ngn_per_usd" % path)
    parts = rate["month"].astype(str).str.split("-", expand=True)
    rate["mi"] = parts[0].astype(int) * 12 + parts[1].astype(int)
    if rate["mi"].duplicated().any():
        raise SystemExit("monthly exchange rate has duplicate months")
    return dict(zip(rate["mi"].astype(int), pd.to_numeric(rate["ngn_per_usd"], errors="coerce")))


def histories(prices):
    return {
        (str(commodity), str(state)): dict(zip(group["mi"].astype(int), group["price_kg"].astype(float)))
        for (commodity, state), group in prices.groupby(["commodity", "admin1"], sort=False)
    }


def feature_at(commodity, state, target_mi, history, rate_by_month=None):
    """Return a single prediction row for target month, or None if origin price is absent."""
    origin = int(target_mi) - 1
    if origin not in history or history[origin] <= 0:
        return None
    log_prices = {m: np.log(p) for m, p in history.items() if m <= origin and p > 0}
    row = {"commodity": str(commodity), "admin1": str(state),
           "target_month": int(target_mi) % 12 or 12}
    for lag in (1, 2, 3):
        row["log_price_lag%d" % lag] = log_prices.get(origin - lag + 1, np.nan)
        prior = log_prices.get(origin - lag)
        current = log_prices.get(origin - lag + 1)
        row["change_lag%d" % lag] = (current - prior) if prior is not None and current is not None else np.nan
    for window in (3, 12):
        values = [log_prices[m] for m in range(origin - window + 1, origin + 1) if m in log_prices]
        row["mean_log_price_%d" % window] = float(np.mean(values)) if values else np.nan
        row["observations_%d" % window] = len(values)
    if rate_by_month is not None:
        # t-1 is the latest complete month available when a forecast for t is issued.
        rate = rate_by_month.get(origin)
        if rate is None or not np.isfinite(rate) or rate <= 0:
            return None
        row["log_ngn_per_usd"] = float(np.log(rate))
    return row


def training_rows(prices, rate_by_month=None):
    """Construct historical one-step examples with features known at each origin."""
    store = histories(prices)
    rows, labels = [], []
    for (commodity, state), group in prices.groupby(["commodity", "admin1"], sort=False):
        history = store[(str(commodity), str(state))]
        for target_mi, price in zip(group["mi"].astype(int), group["price_kg"].astype(float)):
            origin_mi = target_mi - 1
            if origin_mi not in history:
                continue
            feature = feature_at(commodity, state, target_mi, history, rate_by_month)
            if feature is None:
                continue
            y = np.log(price / history[origin_mi])
            if np.isfinite(y):
                feature["series"] = str(commodity) + " | " + str(state)
                feature["mi"] = int(target_mi)
                rows.append(feature)
                labels.append(float(y))
    x = pd.DataFrame(rows)
    return x, np.asarray(labels, dtype=float)


def target_rows(prices, targets, rate_by_month=None):
    """Features for the actual panel cells within targets, keyed for output alignment."""
    store = histories(prices)
    panel = pd.read_csv(PANEL)
    panel["mi"] = panel["mi"].astype(int)
    wanted = set(int(x) for x in targets)
    panel = panel[panel["mi"].isin(wanted)].copy()
    rows = []
    for row in panel.itertuples(index=False):
        history = store[(str(row.commodity), str(row.admin1))]
        feature = feature_at(row.commodity, row.admin1, int(row.mi), history, rate_by_month)
        if feature is not None:
            feature["series"] = str(row.commodity) + " | " + str(row.admin1)
            feature["mi"] = int(row.mi)
            rows.append(feature)
    return pd.DataFrame(rows)


def feature_columns(with_fx=False):
    return NUMERIC_FEATURES + (CATEGORICAL_FEATURES.copy()) + (["log_ngn_per_usd"] if with_fx else [])


def prepare_matrix(frame, reference):
    """Use identical category levels for a train/test pair to keep LightGBM stable."""
    out = frame.copy()
    for col in CATEGORICAL_FEATURES:
        levels = sorted(reference[col].dropna().astype(str).unique())
        out[col] = pd.Categorical(out[col].astype(str), categories=levels)
    return out
