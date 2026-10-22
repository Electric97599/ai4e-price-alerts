"""Fixed, documented model settings shared by the reproducible runners."""

LGBM_PARAMS = {
    "objective": "regression",
    "n_estimators": 120,
    "learning_rate": 0.03,
    "num_leaves": 15,
    "max_depth": -1,
    "min_child_samples": 10,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": 1,
    "verbosity": -1,
    "deterministic": True,
    "force_col_wise": True,
}

# A deliberately small candidate set keeps a per-series, per-month AIC refit feasible.
# Every candidate uses one seasonal difference at lag 12 as the project specifies.
SARIMA_ORDERS = ((0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 2))
SARIMA_SEASONAL_ORDER = (0, 1, 0, 12)
SARIMA_MIN_OBSERVATIONS = 24
SARIMA_MAXITER = 25
SARIMA_WINDOW_MONTHS = 60
