"""Build the evaluation panel for the AI4E price-spike project.

Input : data/nigeria/wfp_food_prices_nga.csv  (WFP price database, HDX, CC BY-IGO)
Output: outputs/panel.csv            one row per commodity, state and consecutive month pair
        console report               the counts that appear in Table 1 of the proposal

Run:  python src/panel.py

Every number used in the proposal must come from this script. If the counts printed
here disagree with Table 1, the proposal is wrong, not the script.

Two eligibility definitions are reported on purpose. The proposal uses the first one.
The second is printed so a reader who adds a consecutive-month condition can see why
their count differs.
"""

import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data", "nigeria", "wfp_food_prices_nga.csv")
OUT_DIR = os.path.join(ROOT, "outputs")
OUT = os.path.join(OUT_DIR, "panel.csv")

# A rise counts when the price goes up by this much or more in one month.
RISE_THRESHOLD = 0.10

STATES = ["Borno", "Yobe", "Adamawa"]

# Eligibility is frozen before the first calibration period opens, so no scored month
# and no calibration month can influence which series take part.
FROZEN_AT = "2022-06"
MIN_OBSERVATIONS = 48
MIN_CONSECUTIVE = 12

# fold label, calibration start, calibration end, scored start, scored end
FOLDS = [
    ("1", "Jul 2022", "Jun 2023", "2023-07", "2024-06"),
    ("2", "Jul 2023", "Jun 2024", "2024-07", "2025-06"),
    ("3", "Jul 2024", "Jun 2025", "2025-07", "2026-06"),
]


def unit_multiplier(unit):
    """Return the number of kilograms in one unit, or NaN when the unit is not a mass."""
    u = str(unit).strip().upper()
    if u == "KG":
        return 1.0
    m = re.match(r"^([\d.]+)\s*KG$", u)
    if m:
        return float(m.group(1))
    m = re.match(r"^([\d.]+)\s*G$", u)
    if m:
        return float(m.group(1)) / 1000.0
    return np.nan


def month_index(series):
    """Year times twelve plus month, so consecutive months differ by one."""
    return series.dt.year * 12 + series.dt.month


def mi_of(text):
    year, month = text.split("-")
    return int(year) * 12 + int(month)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_monthly(raw):
    """Retail quotes in naira per kilogram, monthly median per state, all months kept."""
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["kg"] = df["unit"].map(unit_multiplier)
    df["price_kg"] = df["price"] / df["kg"]
    retail = df[(df["pricetype"] == "Retail") & df["price_kg"].notna() & (df["price_kg"] > 0)]
    retail = retail.assign(mi=month_index(retail["date"]))
    monthly = (
        retail.groupby(["commodity", "admin1", "mi"])
        .agg(price_kg=("price_kg", "median"), markets=("market", "nunique"), quotes=("price_kg", "size"))
        .reset_index()
        .sort_values(["commodity", "admin1", "mi"])
    )
    monthly["key"] = monthly["commodity"] + "|" + monthly["admin1"]
    return retail, monthly


def build_panel(monthly):
    """Keep only month pairs that sit in consecutive months."""
    panel = monthly.copy()
    panel["prev_mi"] = panel.groupby("key")["mi"].shift(1)
    panel["prev_price_kg"] = panel.groupby("key")["price_kg"].shift(1)
    panel = panel[(panel["mi"] - panel["prev_mi"]) == 1].copy()
    panel["change"] = np.log(panel["price_kg"] / panel["prev_price_kg"])
    # The rule is "at least 10 percent", so a rise of exactly 10 percent counts. Comparing
    # logs drops exact-boundary cases through floating point, so test the ratio directly
    # and allow a hair of rounding slack.
    threshold = (1 + RISE_THRESHOLD) * (1 - 1e-9)
    panel["rise"] = (panel["price_kg"] >= panel["prev_price_kg"] * threshold).astype(int)
    return panel


def longest_run(months):
    if not months:
        return 0
    best = cur = 1
    for i in range(1, len(months)):
        cur = cur + 1 if months[i] - months[i - 1] == 1 else 1
        best = max(best, cur)
    return best


def eligible_keys(monthly, require_consecutive=False):
    """Series clearing the frozen coverage rule, using only months up to FROZEN_AT."""
    cutoff = mi_of(FROZEN_AT)
    early = monthly[(monthly["mi"] <= cutoff) & (monthly["admin1"].isin(STATES))]
    keep = set()
    for key, group in early.groupby("key"):
        months = sorted(group["mi"].tolist())
        if len(months) < MIN_OBSERVATIONS:
            continue
        if require_consecutive and longest_run(months) < MIN_CONSECUTIVE:
            continue
        keep.add(key)
    return keep


def main():
    if not os.path.exists(DATA):
        sys.exit("missing data file: %s" % DATA)

    raw = pd.read_csv(DATA)
    print("data file      : %s" % DATA)
    print("sha256         : %s" % sha256(DATA))
    print("rows           : %d" % len(raw))
    print("period         : %s to %s" % (raw["date"].min(), raw["date"].max()))
    print("markets        : %d | commodities: %d | states: %d"
          % (raw["market"].nunique(), raw["commodity"].nunique(), raw["admin1"].nunique()))
    print()

    retail, monthly = build_monthly(raw)
    panel = build_panel(monthly)
    keep = eligible_keys(monthly)
    strict = eligible_keys(monthly, require_consecutive=True)

    print("retail mass-unit quotes kept : %d" % len(retail))
    print("consecutive month pairs      : %d" % len(panel))
    print("eligibility cut-off          : %s (before the first calibration period)" % FROZEN_AT)
    print("eligible series              : %d across %d commodities in %s"
          % (len(keep), len({k.split('|')[0] for k in keep}), ", ".join(STATES)))
    pair_based = set(panel[panel["mi"] <= mi_of(FROZEN_AT)].groupby("key").size().pipe(lambda s: s[s >= MIN_OBSERVATIONS]).index)
    pair_based &= set(monthly[monthly["admin1"].isin(STATES)]["key"])
    print("  if eligibility is counted on consecutive pairs instead of monthly observations: %d series across %d commodities"
          % (len(pair_based), len({k.split('|')[0] for k in pair_based})))
    print("  the proposal uses the first count, which matches the stated rule")
    print()

    print("Table 1 check")
    print("%-5s %-12s %-19s %-19s %6s %6s %10s" %
          ("fold", "fit through", "calibration", "scored", "cells", "rises", "naive lag"))
    total_cells = total_rises = 0
    for label, cal_a, cal_b, test_a, test_b in FOLDS:
        scored = panel[(panel["mi"] >= mi_of(test_a)) & (panel["mi"] <= mi_of(test_b))]
        scored = scored[scored["key"].isin(keep)]
        available = monthly.set_index(["key", "mi"])["price_kg"]
        naive_cells = sum(1 for k, m in zip(scored["key"], scored["mi"]) if (k, m - 12) in available.index)
        cells = len(scored)
        rises = int(scored["rise"].sum())
        total_cells += cells
        total_rises += rises
        fit = pd.Timestamp(year=int(cal_a.split()[1]), month=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(cal_a.split()[0]) + 1, day=1) - pd.offsets.MonthBegin(1)
        print("%-5s %-12s %-19s %-19s %6d %6d %10d" %
              (label, fit.strftime("%b %Y"), "%s to %s" % (cal_a, cal_b), "%s to %s" % (test_a, test_b), cells, rises, naive_cells))
    print("%-5s %-12s %-19s %-19s %6d %6d" %
          ("all", "", "", "", total_cells, total_rises))
    print("rise rate over scored cells: %.2f percent" % (100 * total_rises / total_cells))

    # Balanced market check: markets that quote in every scored window.
    windows = [(mi_of(test_a), mi_of(test_b)) for _, _, _, test_a, test_b in FOLDS]
    near = retail[retail["admin1"].isin(STATES)]
    quotes = near.assign(ym=month_index(near["date"]))
    active = [m for m in sorted(quotes["market"].unique())
              if all(((quotes["market"] == m) & (quotes["ym"] >= a) & (quotes["ym"] <= b)).any() for a, b in windows)]
    balanced = raw[raw["market"].isin(active)]
    _, monthly_b = build_monthly(balanced)
    panel_b = build_panel(monthly_b)
    keep_b = eligible_keys(monthly_b)
    cells_b = rises_b = 0
    for _, _, _, test_a, test_b in FOLDS:
        sc = panel_b[(panel_b["mi"] >= mi_of(test_a)) & (panel_b["mi"] <= mi_of(test_b))]
        sc = sc[sc["key"].isin(keep_b)]
        cells_b += len(sc)
        rises_b += int(sc["rise"].sum())
    print()
    print("Balanced market check")
    print("markets active in all three scored windows: %d of %d in the three states"
          % (len(active), quotes["market"].nunique()))
    print("series %d | cells %d | rises %d | %.1f percent"
          % (len(keep_b), cells_b, rises_b, 100 * rises_b / cells_b))

    os.makedirs(OUT_DIR, exist_ok=True)
    cols = ["commodity", "admin1", "mi", "price_kg", "prev_price_kg", "change", "rise", "markets", "quotes"]
    panel[panel["key"].isin(keep)][cols].to_csv(OUT, index=False)
    print()
    print("panel written  : %s (eligible series only)" % OUT)


if __name__ == "__main__":
    main()
