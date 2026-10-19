"""The measures in the proposal, implemented once so every model reports the same way.

Definitions, as written in the proposal:

* A cell is a commodity, state and outcome month. It rises when the price is at least
  ten percent higher than the month before.
* The alert score is the predicted percentage change, forecast price over current
  price minus one.
* The threshold is chosen per rule and per variant inside each fold: it maximises
  recall on the CALIBRATION cells subject to a false positive rate of at most ten
  percent, that rate being false positives over the cells that did not rise, with ties
  broken toward the higher threshold. It is then frozen and applied to the scored cells.
* Secondary measures: precision recall area, mean absolute error against the
  persistence and seasonal rules, and an assumed weighted penalty per 1,000 scored
  cells, where a missed rise counts k and a false alarm counts one.

Run:  python src/metrics.py    (runs the self tests, no data needed)
"""

import numpy as np

MAX_FPR = 0.10


def confusion(scores, rises, threshold):
    """Alerts, true positives, false positives and false negatives at a threshold."""
    scores = np.asarray(scores, dtype=float)
    rises = np.asarray(rises, dtype=int)
    alert = scores >= threshold
    tp = int(np.sum(alert & (rises == 1)))
    fp = int(np.sum(alert & (rises == 0)))
    fn = int(np.sum(~alert & (rises == 1)))
    tn = int(np.sum(~alert & (rises == 0)))
    return {"alert": alert, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def recall(scores, rises, threshold):
    c = confusion(scores, rises, threshold)
    return c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else float("nan")


def false_positive_rate(scores, rises, threshold):
    c = confusion(scores, rises, threshold)
    return c["fp"] / (c["fp"] + c["tn"]) if (c["fp"] + c["tn"]) else float("nan")


def choose_threshold(scores, rises, max_fpr=MAX_FPR):
    """Maximise calibration recall subject to a false positive rate of at most max_fpr.

    Ties go to the higher threshold, which issues fewer alerts. A threshold above the
    largest score is always a candidate, so a rule that cannot meet the cap without
    alerting everything can still return "never alert".
    """
    scores = np.asarray(scores, dtype=float)
    rises = np.asarray(rises, dtype=int)
    candidates = np.unique(scores)[::-1]        # highest first
    candidates = np.append(candidates, np.inf)  # never alert
    best = None
    for thr in candidates:
        r = recall(scores, rises, thr)
        f = false_positive_rate(scores, rises, thr)
        if np.isnan(r) or np.isnan(f) or f > max_fpr + 1e-12:
            continue
        key = (r, thr)
        if best is None or key > best[0]:
            best = (key, thr)
    return float("inf") if best is None else float(best[1])


def precision_recall_area(scores, rises):
    """Average precision, the step-wise area under the precision recall curve."""
    try:
        from sklearn.metrics import average_precision_score
    except ImportError:  # keep the module usable without scikit-learn
        scores = np.asarray(scores, dtype=float)
        rises = np.asarray(rises, dtype=int)
        order = np.argsort(-scores)
        rises = rises[order]
        hits, total, ap = 0, 0, 0.0
        prev_recall = 0.0
        for i, y in enumerate(rises, start=1):
            hits += int(y)
            if y:
                ap += (hits / i) * (hits / len(rises) - prev_recall)
                prev_recall = hits / len(rises)
        return float(ap)
    return float(average_precision_score(np.asarray(rises, dtype=int),
                                         np.asarray(scores, dtype=float)))


def mean_absolute_error(actual_change, predicted_change):
    """Average miss in price change, the same units a buyer reads in naira per kilogram."""
    a = np.asarray(actual_change, dtype=float)
    p = np.asarray(predicted_change, dtype=float)
    return float(np.mean(np.abs(a - p)))


def weighted_penalty(alert, rises, k=3, per=1000):
    """Assumed weighted decision penalty per `per` scored cells.

    A missed rise counts k, a false alarm counts one. The weights are assumptions,
    never measured procurement costs, so report them at k = 1, 3 and 5.
    """
    alert = np.asarray(alert, dtype=bool)
    rises = np.asarray(rises, dtype=int).astype(bool)
    missed = int(np.sum(~alert & rises))
    false_alarm = int(np.sum(alert & ~rises))
    return per * (k * missed + false_alarm) / len(rises)


def _self_test():
    # Six cells, three rises. A rule that always alerts catches all three at a false
    # positive rate of one, so the cap forces a higher threshold.
    rises = [1, 0, 1, 0, 0, 1]
    scores = [0.30, 0.20, 0.10, 0.05, -0.02, -0.05]
    thr = choose_threshold(scores, rises, max_fpr=0.10)
    assert thr == 0.30, thr                      # only the top cell clears the cap
    c = confusion(scores, rises, thr)
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (1, 0, 2, 3), c
    assert abs(false_positive_rate(scores, rises, thr) - 0.0) < 1e-12
    assert abs(recall(scores, rises, thr) - 1 / 3) < 1e-12

    # Ties go to the higher threshold: same recall, fewer alerts. Both thresholds catch
    # the only rise, so the higher one wins.
    tied = [0.5, 0.5, 0.4]
    tre = [1, 0, 0]
    assert choose_threshold(tied, tre, max_fpr=1.0) == 0.5

    # A rule that cannot meet the cap without alerting everything returns never alert.
    flat = [0.0, 0.0, 0.0]
    assert choose_threshold(flat, [1, 0, 1], max_fpr=0.10) == float("inf")

    # Penalty: two missed rises at k = 3 and one false alarm over 1,000 cells.
    alert = [False, False, True, False]
    rr = [1, 1, 0, 0]
    assert weighted_penalty(alert, rr, k=3, per=1000) == 1000 * (3 * 2 + 1) / 4

    # Mean absolute error is in change units, so identical predictions score zero.
    assert mean_absolute_error([0.1, -0.1], [0.1, -0.1]) == 0.0
    print("metrics self test passed")


if __name__ == "__main__":
    _self_test()
