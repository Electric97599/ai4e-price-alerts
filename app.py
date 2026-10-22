"""Analyst demo: price history, monthly forecast alerts and fold results.

The app reads saved outputs only. It never fits a model and the alert queue never displays
the outcome used to score a forecast.
"""

import os

import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUTS = os.path.join(HERE, "outputs")
MONTHLY = os.path.join(OUTPUTS, "monthly.csv")
ALERTS = os.path.join(OUTPUTS, "alerts.csv")
FOLD_TABLE = os.path.join(OUTPUTS, "fold_table.csv")
REVIEW = os.path.join(OUTPUTS, "review_log.csv")

st.set_page_config(page_title="Staple price alerts, North-East Nigeria", layout="wide")


def with_date(frame):
    frame = frame.copy()
    frame["mi"] = frame["mi"].astype(int)
    frame["date"] = pd.to_datetime({"year": (frame["mi"] - 1) // 12,
                                    "month": (frame["mi"] - 1) % 12 + 1, "day": 1})
    return frame


@st.cache_data(ttl=600)
def load_csv(path):
    if not os.path.exists(path) or os.path.getsize(path) < 10:
        return None
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None


def log_review(row, decision):
    entry = pd.DataFrame([{
        "logged_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "model": row["model"], "series": row["series"], "fold": row["fold"],
        "outcome_month": row["date"].strftime("%Y-%m"),
        "score_percent": round(100 * float(row["score"]), 3),
        "threshold_percent": round(100 * float(row["threshold"]), 3),
        "decision": decision,
    }])
    entry.to_csv(REVIEW, mode="a", header=not os.path.exists(REVIEW), index=False)


monthly = load_csv(MONTHLY)
alerts = load_csv(ALERTS)
fold_table = load_csv(FOLD_TABLE)

st.title("Monthly staple price alerts")
st.caption("04-655 A AI for Engineers, Group 10. Flags support analyst review; they do not automate purchases.")

if monthly is None:
    st.error("outputs/monthly.csv is missing. Run `python src/panel.py` first.")
    st.stop()

monthly = with_date(monthly)
if alerts is not None and not alerts.empty:
    # A reviewer sees only prices available at the forecast origin, not the outcome
    # month (or any later month) whose alert is under review.
    origin_mi = int(alerts["mi"].astype(int).min()) - 1
    monthly = monthly[monthly["mi"] <= origin_mi].copy()
states = sorted(monthly["admin1"].unique())
state = st.sidebar.selectbox("State", states)
commodities = sorted(monthly.loc[monthly["admin1"] == state, "commodity"].unique())
commodity = st.sidebar.selectbox("Commodity", commodities)
history = monthly[(monthly["admin1"] == state) & (monthly["commodity"] == commodity)] \
    .sort_values("date").copy()
consecutive = history["mi"].diff().eq(1)
history["change_percent"] = (100 * history["price_kg"].pct_change(fill_method=None)).where(consecutive)
history["elapsed_months"] = history["mi"].diff()

tab_history, tab_queue, tab_results = st.tabs(["Price history", "Alert queue", "Fold results"])

with tab_history:
    st.subheader("%s in %s" % (commodity, state))
    left, right = st.columns([3, 2])
    with left:
        chart = history.set_index("date")["price_kg"].asfreq("MS")
        st.line_chart(chart, height=280)
        st.caption("Retail price in naira per kilogram, monthly median across markets. Gaps are left visible; history stops at the alert's forecast origin.")
    with right:
        recent = history.tail(12)[["date", "price_kg", "change_percent", "elapsed_months"]].copy()
        recent["date"] = recent["date"].dt.strftime("%Y-%m")
        st.dataframe(recent.rename(columns={"date": "Month", "price_kg": "Naira per kg",
                                            "change_percent": "Change %",
                                            "elapsed_months": "Months since last quote"}),
                     hide_index=True)
        st.caption("A rise is at least a ten percent month-on-month increase.")

with tab_queue:
    st.subheader("Latest scored-month alert queue")
    if alerts is None:
        st.info("Run `python src/score_alerts.py` after the model and fold scripts.")
    else:
        alerts = with_date(alerts)
        models = sorted(alerts["model"].unique())
        model = st.selectbox("Forecast rule", models)
        window = alerts[alerts["model"] == model].copy()
        flagged = window[window["alert"].astype(bool)].sort_values("score", ascending=False)
        st.caption("%d forecast cells are covered; %d clear the threshold frozen for fold %s."
                   % (len(window), len(flagged), window["fold"].iloc[0] if len(window) else "3"))
        if flagged.empty:
            st.info("No forecast for this rule clears the frozen threshold.")
        else:
            shown = flagged[["date", "series", "score"]].copy()
            shown["date"] = shown["date"].dt.strftime("%Y-%m")
            shown["score"] = (100 * shown["score"]).round(1)
            st.dataframe(shown.rename(columns={"date": "Outcome month", "series": "Series",
                                               "score": "Predicted change %"}),
                         hide_index=True, height=300)
            choices = ["%s | %s" % (r.date.strftime("%Y-%m"), r.series)
                       for r in flagged.itertuples()]
            pick = st.selectbox("Review one flagged forecast", choices)
            row = flagged.iloc[choices.index(pick)]
            left, right, info = st.columns([1, 1, 4])
            if left.button("Accept flag"):
                log_review(row, "accept")
                st.success("Decision recorded.")
            if right.button("Dismiss flag"):
                log_review(row, "dismiss")
                st.success("Decision recorded.")
            if os.path.exists(REVIEW):
                info.caption("Review log contains %d decisions." % len(pd.read_csv(REVIEW)))

with tab_results:
    st.subheader("Frozen-threshold fold results")
    if fold_table is None:
        st.info("Run `python src/run_folds.py` for each saved score file, then combine the results.")
    else:
        st.dataframe(fold_table.sort_values(["model", "fold"]), hide_index=True)
        st.caption("Rates are measured on covered cells; each row also reports full cell counts and coverage.")
