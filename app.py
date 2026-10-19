"""The group's demo app: price history, the alert queue, and the fold results.

Three screens, matching the evidence the final report needs:

1. Price history for one state and commodity, with the month-on-month change.
2. The alert queue for the last scored window: each flagged cell, its score, and an
   accept or dismiss button. The choices are appended to outputs/review_log.csv, which
   is the record of a human supervising the system.
3. The fold table: cells, rises, coverage, the frozen threshold, the recall achieved,
   the false alarm rate achieved, and the average miss against both reference rules.

The app only reads files the scripts write. It never fits a model, so a visitor cannot
make it forecast something the group has not produced.

Run:  streamlit run app.py
"""

import os

import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(HERE, "outputs", "panel.csv")
SCORES = os.path.join(HERE, "outputs", "baseline_scores.csv")
REVIEW = os.path.join(HERE, "outputs", "review_log.csv")

st.set_page_config(page_title="Staple price alerts, North-East Nigeria", layout="wide")


@st.cache_data
def load_panel():
    frame = pd.read_csv(PANEL)
    frame["date"] = pd.to_datetime(
        {"year": (frame["mi"] - 1) // 12, "month": (frame["mi"] - 1) % 12 + 1, "day": 1})
    return frame


@st.cache_data
def load_scores():
    if not os.path.exists(SCORES):
        return None
    frame = pd.read_csv(SCORES)
    frame["date"] = pd.to_datetime(
        {"year": (frame["mi"] - 1) // 12, "month": (frame["mi"] - 1) % 12 + 1, "day": 1})
    return frame


def log_review(row, decision):
    entry = pd.DataFrame([{
        "logged_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "series": row["series"], "fold": row["fold"],
        "month": row["date"].strftime("%Y-%m"), "score": row["naive_score"],
        "decision": decision,
    }])
    header = not os.path.exists(REVIEW)
    entry.to_csv(REVIEW, mode="a", header=header, index=False)


panel = load_panel()
scores = load_scores()

st.title("Monthly staple price alerts")
st.caption("04-655 A AI for Engineers, Group 10. Flags are decision support for an "
           "analyst, not automated purchases.")

states = sorted(panel["admin1"].unique())
state = st.sidebar.selectbox("State", states)
commodities = sorted(panel.loc[panel["admin1"] == state, "commodity"].unique())
commodity = st.sidebar.selectbox("Commodity", commodities)

history = panel[(panel["admin1"] == state) & (panel["commodity"] == commodity)].sort_values("date")

tab_history, tab_queue, tab_results = st.tabs(["Price history", "Alert queue", "Fold results"])

with tab_history:
    st.subheader("%s in %s" % (commodity, state))
    left, right = st.columns([3, 2])
    with left:
        st.line_chart(history.set_index("date")["price_kg"], height=280)
        st.caption("Retail price in naira per kilogram, monthly median across markets.")
    with right:
        recent = history.tail(12)[["date", "price_kg", "change", "rise"]].copy()
        recent["change"] = (recent["change"] * 100).round(1)
        recent["date"] = recent["date"].dt.strftime("%Y-%m")
        recent["rise"] = recent["rise"].map({1: "yes", 0: "no"})
        st.dataframe(recent.rename(columns={"date": "Month", "price_kg": "Naira per kg",
                                            "change": "Change %", "rise": "10% rise"}),
                     hide_index=True)
        st.caption("A rise counts when the month-on-month change is at least ten percent.")

with tab_queue:
    st.subheader("Alert queue")
    if scores is None:
        st.info("Run `python src/baseline.py` first. The queue reads that output.")
    else:
        latest = sorted(scores["fold"].unique())[-1]
        rows = scores[(scores["fold"] == latest) & scores["naive_score"].notna()].copy()
        rows = rows.sort_values("naive_score", ascending=False).head(25)
        st.caption("Scored window %s. Ranked by the reference rule's predicted change; "
                   "the alerting models replace this score in the modelling weeks." % latest)
        shown = rows[["date", "series", "naive_score", "actual_change", "rise"]].copy()
        shown["date"] = shown["date"].dt.strftime("%Y-%m")
        shown["naive_score"] = (shown["naive_score"] * 100).round(1)
        shown["actual_change"] = (shown["actual_change"] * 100).round(1)
        st.dataframe(shown.rename(columns={"date": "Outcome month", "series": "Series",
                                           "naive_score": "Predicted change %",
                                           "actual_change": "Actual change %",
                                           "rise": "Rose 10%+"}),
                     hide_index=True, height=300)
        pick = st.selectbox("Review one flagged month",
                            ["%s | %s" % (r.date.strftime("%Y-%m"), r.series)
                             for r in rows.itertuples()])
        target = rows.iloc[[i for i, r in enumerate(rows.itertuples())
                            if "%s | %s" % (r.date.strftime("%Y-%m"), r.series) == pick][0]]
        c1, c2, c3 = st.columns([1, 1, 4])
        if c1.button("Accept flag"):
            log_review(target, "accept")
            st.success("Recorded: buy ahead of this month.")
        if c2.button("Dismiss flag"):
            log_review(target, "dismiss")
            st.success("Recorded: no action taken.")
        if os.path.exists(REVIEW):
            c3.caption("Review log holds %d decisions." % len(pd.read_csv(REVIEW)))

with tab_results:
    st.subheader("Fold results")
    st.caption("Reference rules on the same three windows. The alerting models report "
               "beside these numbers once the modelling issues land.")
    if scores is None:
        st.info("Run `python src/baseline.py` first.")
    else:
        rows = []
        for fold in sorted(scores["fold"].unique()):
            frame = scores[scores["fold"] == fold]
            covered = frame.dropna(subset=["naive_score"])
            rows.append({
                "Fold": fold, "Cells": len(frame), "Rises": int(frame["rise"].sum()),
                "Seasonal coverage": len(covered),
                "Seasonal miss": round(covered["naive_score"].sub(covered["actual_change"]).abs().mean(), 3),
                "Persistence miss": round(frame["actual_change"].abs().mean(), 3),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Miss is the mean absolute error in monthly price change, so 0.05 is "
                   "five percentage points on a typical month. Both references are scored "
                   "on their own coverage; compare a model on the cells it shares with them.")
