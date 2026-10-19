"""The one file format every model in this repository writes and every report reads.

A score file is a CSV with three columns and no index:

    series,mi,score

`series` is "Commodity | State", `mi` is the outcome month as year * 12 + month, and
`score` is the predicted one month percentage change. Anything else is a bug, so the
validators here fail loudly rather than letting a model slip through with a column of
NaNs or a month that is not in any fold.

Typical use, inside a new model module:

    from contracts import write_scores, validate_scores
    frame = validate_scores(frame, name="sarima")
    write_scores(frame, "outputs/sarima_scores.csv")
"""

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUTS = os.path.join(ROOT, "outputs")

SCORE_COLUMNS = ["series", "mi", "score"]
LABEL_COLUMNS = ["series", "mi", "rise"]


def fold_months():
    """Every outcome month that belongs to a fold window, calibration and scored."""
    import folds as folds_mod
    months = set()
    for fold in folds_mod.FOLDS:
        for part in ("calibration", "scored"):
            start, end = fold[part]
            months.update(range(folds_mod.mi_of(start), folds_mod.mi_of(end) + 1))
    return months


def validate_scores(frame, name="scores", check_folds=True):
    """Return the frame with only the three score columns, or raise with the reason."""
    missing = [c for c in SCORE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError("%s is missing %s; a score file is series, mi, score"
                         % (name, ", ".join(missing)))
    out = frame[SCORE_COLUMNS].copy()
    if out.empty:
        raise ValueError("%s is empty" % name)
    if out["score"].isna().any():
        raise ValueError("%s has %d NaN scores; omit the row instead, so coverage stays "
                         "visible" % (name, int(out["score"].isna().sum())))
    try:
        out["score"] = out["score"].astype(float)
    except (TypeError, ValueError):
        raise ValueError("%s has a score that is not a number" % name)
    if not np.isfinite(out["score"]).all():
        raise ValueError("%s has infinite scores" % name)
    if out["mi"].isna().any() or (out["mi"] != out["mi"].astype(int)).any():
        raise ValueError("%s has a month index that is not a whole number" % name)
    out["mi"] = out["mi"].astype(int)
    if out.duplicated(subset=["series", "mi"]).any():
        raise ValueError("%s has duplicate series and month rows" % name)
    if check_folds:
        outside = sorted(set(out["mi"]) - fold_months())
        if outside:
            raise ValueError("%s has %d month(s) outside every fold window, the first being "
                             "%d; a score file covers the six fold windows only"
                             % (name, len(outside), outside[0]))
    return out


def write_scores(frame, path):
    """Validate and write, creating the outputs directory if it is missing."""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    validate_scores(frame).to_csv(path, index=False)
    print("wrote %s (%d rows)" % (os.path.relpath(path, ROOT), len(frame)))
    return path


def read_labels(path=None):
    """The rise label for every scored cell, keyed by series and month."""
    path = path or os.path.join(OUTPUTS, "panel.csv")
    panel = pd.read_csv(path)
    panel["series"] = panel["commodity"].astype(str) + " | " + panel["admin1"].astype(str)
    return panel[LABEL_COLUMNS].copy()


def join_labels(scores, labels=None):
    """Attach the rise label to each score, dropping scores with no label."""
    scores = validate_scores(scores)
    labels = read_labels() if labels is None else labels
    joined = scores.merge(labels, on=["series", "mi"], how="inner")
    dropped = len(scores) - len(joined)
    if dropped:
        print("note: %d scores had no rise label and were dropped" % dropped)
    return joined
