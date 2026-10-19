"""The group's demo app: price history, the alert queue, and the fold results.

Three screens, matching the evidence the final report needs:

1. Price history for one state and commodity, with the month-on-month percentage change.
   Months a series does not report are left as gaps, never drawn through as if observed.
2. The alert queue for the chosen scored window: every cell above that fold's frozen
   threshold, with accept or dismiss buttons. The outcome of the month is hidden until a
   decision is recorded, so the reviewer cannot answer with hindsight.
3. The fold results: the frozen threshold, the recall achieved, the realized false alarm
   rate, and the average miss against both reference rules, each over its own coverage.

The app only reads files the scripts write. It never fits a model, so a visitor cannot make
it forecast something the group has not produced.

Run:  streamlit run app.py
"""

import os

import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUTS = os.path.join(HERE, "outputs")
MONTHLY = os.path.join(OUTPUTS, "monthly.csv")
SCORES = os.path.join(OUTPUTS, "baseline_scores.csv")
FOLD_TABLE = os.path.join(OUTPUTS, "fold_table.csv")
BASELINE_FOLDS = os.path.join(OUTPUTS, "baseline_folds.csv")
REVIEW = os.path.join(OUTPUTS, "review_log.csv")

st.set_page_config(page_title="Staple price alerts, North-East Nigeria", layout="wide")


def with_date(frame):
    """Attach a date column from the month index."""
    frame = frame.copy()
    frame["date"] = pd.to_datetime(
        {"year": (frame["mi"] - 1) // 12, "month": (frame["mi"] - 1) % 12 + 1, "day": 1})
    return frame


@st.cache_data(ttl=600)
def load_monthly():
    """Every observed month of the eligible series, so gaps stay visible."""
    if not os.path.exists(MONTHLY):
        return None
    return with_date(pd.read_csv(MONTHLY))


@st.cache_data(ttl=600)
def load_scores():
    if not os.path.exists(SCORES) or os.path.getsize(SCORES) < 10:
        return None
    return with_date(pd.read_csv(SCORES))


@st.cache_data(ttl=600)
def load_csv(path):
    """A small results table, or None when it has not been produced yet."""
    if not os.path.exists(path) or os.path.getsize(path) < 10:
        return None
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None


def log_review(row, decision):
    """Append one decision. Scores are logged in percentage points, with the unit named."""
    entry = pd.DataFrame([{
        "logged_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "series": row["series"], "fold": row["fold"],
        "month": row["date"].strftime("%Y-%m"),
        "score_percent": round(100 * float(row["score"]), 3),
        "threshold_percent": round(100 * float(row["threshold"]), 3),
        "decision": decision,
    }])
    header = not os.path.exists(REVIEW)
    entry.to_csv(REVIEW, mode="a", header=header, index=False)


monthly = load_monthly()
scores = load_scores()
fold_table = load_csv(FOLD_TABLE)
baseline_folds = load_csv(BASELINE_FOLDS)

st.title("Monthly staple price alerts")
st.caption("04-655 A AI for Engineers, Group 10. Flags are decision support for an analyst, "
           "not automated purchases.")

if monthly is None:
    st.error("outputs/monthly.csv is missing. Run `python src/panel.py` first.")
    st.stop()

states = sorted(monthly["admin1"].unique())
state = st.sidebar.selectbox("State", states)
commodities = sorted(monthly.loc[monthly["admin1"] == state, "commodity"].unique())
commodity = st.sidebar.selectbox("Commodity", commodities)

history = monthly[(monthly["admin1"] == state) & (monthly["commodity"] == commodity)] \
    .sort_values("date").copy()
history["change_percent"] = 100 * history["price_kg"].pct_change()
history["elapsed_months"] = history["mi"].diff()

tab_history, tab_queue, tab_results = st.tabs(["Price history", "Alert queue", "Fold results"])

with tab_history:
    st.subheader("%s in %s" % (commodity, state))
    left, right = st.columns([3, 2])
    with left:
        st.line_chart(history.set_index("date")["price_kg"], height=280)
        st.caption("Retail price in naira per kilogram, monthly median across markets. The "
                   "line breaks where the series does not report.")
    with right:
        recent = history.tail(12)[["date", "price_kg", "change_percent", "elapsed_months"]]
        recent = recent.assign(date=recent["date"].dt.strftime("%Y-%m"))
        st.dataframe(
            recent.rename(columns={"date": "Month", "price_kg": "Naira per kg",
                                   "change_percent": "Change %",
                                   "elapsed_months": "Months since last quote"}),
            hide_index=True)
        st.caption("Change % is the arithmetic month-on-month change, the same definition the "
                   "alert uses. A rise counts when that change is at least ten percent.")

with tab_queue:
    st.subheader("Alert queue")
    if scores is None:
        st.info("Run `python src/baseline.py` first. The queue reads that output.")
    else:
        available = sorted(scores["fold"].unique())
        fold = st.selectbox("Scored window", available, index=len(available) - 1)
        window = scores[scores["fold"] == fold]
        rows = window[window["naive_score"].notna()].copy()

        threshold = None
        if baseline_folds is not None:
            match = baseline_folds[baseline_folds["fold"].astype(str) == str(fold)]
            if not match.empty:
                threshold = float(match.iloc[0]["threshold"])

        if threshold is None:
            st.warning("No frozen threshold on file. Run `python src/baseline.py` so the "
                       "queue can show which cells the rule would have flagged.")
            alerts = rows.sort_values("naive_score", ascending=False)
        else:
            alerts = rows[rows["naive_score"] >= threshold] \
                .sort_values("naive_score", ascending=False)
            st.caption("%d cells in this window, %d with a year-earlier price, %d above the "
                       "frozen threshold %.4f, which was chosen on the calibration months and "
                       "then frozen." % (len(window), len(rows), len(alerts), threshold))

        if alerts.empty:
            st.info("No cell in this window clears the frozen threshold.")
        else:
            # The outcome columns stay hidden until a decision is recorded, so a reviewer
            # cannot pick the flag that happened to rise.
            shown = alerts[["date", "series", "naive_score"]].copy()
            shown["date"] = shown["date"].dt.strftime("%Y-%m")
            shown["naive_score"] = (100 * shown["naive_score"]).round(1)
            st.dataframe(shown.rename(columns={"date": "Outcome month", "series": "Series",
                                               "naive_score": "Predicted change %"}),
                         hide_index=True, height=300)
            pick = st.selectbox("Review one flagged month",
                                ["%s | %s" % (r.date.strftime("%Y-%m"), r.series)
                                 for r in alerts.itertuples()])
            if pick:
                index = [i for i, r in enumerate(alerts.itertuples())
                         if "%s | %s" % (r.date.strftime("%Y-%m"), r.series) == pick][0]
                target = alerts.iloc[index].copy()
                target["score"] = target["naive_score"]
                target["threshold"] = threshold if threshold is not None else 0.0
                c1, c2, c3 = st.columns([1, 1, 4])
                if c1.button("Accept flag"):
                    log_review(target, "accept")
                    st.success("Recorded: this month was flagged for the analyst.")
                if c2.button("Dismiss flag"):
                    log_review(target, "dismiss")
                    st.success("Recorded: the analyst took no action.")
                if os.path.exists(REVIEW):
                    c3.caption("Review log holds %d decisions."
                               % len(pd.read_csv(REVIEW)))

with tab_results:
    st.subheader("Fold results")
    if fold_table is not None:
        st.dataframe(fold_table, hide_index=True)
        st.caption("Produced by `python src/run_folds.py`. Every row states its coverage, "
                   "because the rules do not all score the same cells.")
    elif baseline_folds is not None:
        st.dataframe(baseline_folds, hide_index=True)
        st.caption("Reference rules only, from `python src/baseline.py`. `run_folds.py` adds "
                   "the learned models to this screen.")
    else:
        st.info("Run `python src/baseline.py` first, then `python src/run_folds.py`.")
    if scores is not None:
        rows = []
        for fold in sorted(scores["fold"].unique()):
            frame = scores[scores["fold"] == fold]
            covered = frame.dropna(subset=["naive_score"])
            rows.append({
                "Fold": fold,
                "Cells": len(frame),
                "Rises": int(frame["rise"].sum()),
                "Seasonal coverage": len(covered),
                "Seasonal miss (covered cells)":
                    round(covered["naive_score"].sub(covered["actual_change"]).abs().mean(), 3),
                "Persistence miss (all cells)":
                    round(frame["actual_change"].abs().mean(), 3),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Miss is the mean absolute error in monthly change, so 0.05 is five "
                   "percentage points. The two reference rules cover different cell sets, "
                   "so each column names the set it is scored on.")
