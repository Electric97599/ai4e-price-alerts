"""One place for the saved final-origin models, so scoring never refits.

Issue #4 asks for the fitted models to be saved with joblib so the monthly scorer and the
app never refit. `src/fit_final.py` writes one bundle with this module, and
`src/score_latest.py` only reads it. Keeping the read and the write in one file means the
key names cannot drift apart.

The bundle is a plain dict, stamped with the month it was trained for:

    {"origin_mi": 24321,          # last month whose prices the fits could see
     "target_mi": 24322,          # the outcome month those fits forecast
     "feature_columns": {"lightgbm": [...], "lightgbm_fx": [...]},
     "categories": {"admin1": [...], "commodity": [...]},
     "lightgbm": LGBMRegressor,
     "lightgbm_fx": LGBMRegressor,
     "sarima": {"Commodity | State": {"order": [1, 1, 0], "origin_log_price": 9.8,
                                      "result": <SARIMAXResults>}},
     "settings": {"lightgbm": {...}, "sarima": {...}},
     "versions": {"python": "3.13.5", "lightgbm": "4.7.0", "statsmodels": "0.14.4"}}

Unpickling a statsmodels result only needs the same statsmodels version, so the version
stamp is written beside it: a mismatch is a rerun of `src/fit_final.py`, not a quiet
reinterpretation of the saved coefficients.
"""

import os
import platform

import joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
BUNDLE = os.path.join(MODELS, "final_origin.joblib")


def save(bundle, path=None):
    """Write the bundle, creating models/ if it is missing."""
    path = BUNDLE if path is None else path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(bundle, path, compress=3)
    print("wrote %s (%.1f MB)" % (os.path.relpath(path, ROOT),
                                 os.path.getsize(path) / 1e6))
    return path


def load(path=None):
    """Read the bundle, or stop with the command that recreates it."""
    path = BUNDLE if path is None else path
    if not os.path.exists(path):
        raise SystemExit("%s is missing. Run `python src/fit_final.py` first: the scorer "
                         "loads saved models and never fits one." % os.path.relpath(path, ROOT))
    return joblib.load(path)


def versions():
    """The versions that have to match for the pickled fits to load."""
    import lightgbm
    import numpy
    import pandas
    import statsmodels

    return {"python": platform.python_version(), "numpy": numpy.__version__,
            "pandas": pandas.__version__, "lightgbm": lightgbm.__version__,
            "statsmodels": statsmodels.__version__}
