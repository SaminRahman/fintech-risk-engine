"""
dashboard.py (version 2: sidebar filters)
Run with:  streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

import duckdb
import plotly.express as px

import streamlit as st
# Streamlit only knows about the app/ folder, so tell Python where the project root is.
# That lets us write "from src.metrics import ...".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.metrics import lift, net_benefit_table, wobble_pct  # noqa: E402
# One look for every Plotly chart: white background, light grid lines.
px.defaults.template = "plotly_white"

import pandas as pd

DATA = "data/processed/scored_applications.csv"

# --- PAGE SETUP ---
st.set_page_config(page_title="Fraud Risk Engine", layout="wide")
st.title("FinTech & Risk Operations Engine")
st.caption(
    "Synthetic data: 5,000 fake device-financing applications with fraud patterns "
    "planted on purpose. The goal is to show the method, not to claim real-world results."
)

with st.expander("Key findings (full dataset, no filters)"):
    st.markdown(
        """
- **The risk score works.** High-tier applications are fraud about **10.7%** of the time, versus **2.2%** for Low, roughly 5 times higher.
- **Reviewing everyone is not the answer.** Whether a review pays off depends on what one costs. At $25 per review the best policy reviews about 74% of applications. At $60 it reviews only about 30%.
- **Small groups wobble.** Credit-score bands differ by less than the normal random wobble, so the dashboard shows error bars instead of declaring a winner.
        """
    )
st.caption("Synthetic device-financing applications scored with transparent SQL rules.")

if not Path(DATA).exists():
    st.error("Scored data not found. Run: python src/risk_score.py")
    st.stop()


# --- HELPERS ---
@st.cache_data  # remember the loaded data so we don't re-read the CSV on every click
def load_data():
    # SQL reads the CSV; .df() hands the result back as a pandas table
    return duckdb.sql(f"SELECT * FROM '{DATA}'").df()


def run_sql(sql, table):
    # Give DuckDB our filtered pandas table under the name "filtered",
    # so the SQL below can say: FROM filtered
    con = duckdb.connect()
    con.register("filtered", table)
    return con.sql(sql).df()


df = load_data()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

all_channels = sorted(df["channel"].unique())
all_devices = sorted(df["device"].unique())

# multiselect returns the list the visitor ticked; default = everything ticked
channels = st.sidebar.multiselect("Channel", all_channels, default=all_channels)
devices = st.sidebar.multiselect("Device", all_devices, default=all_devices)

min_date = df["applied_at"].min().date()
max_date = df["applied_at"].max().date()
date_range = st.sidebar.date_input(
    "Application date", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

# While the visitor is mid-click, date_input can return only a start date
if len(date_range) != 2:
    st.info("Pick an end date in the sidebar to apply the date filter.")
    st.stop()
start_date, end_date = date_range

# --- APPLY THE FILTERS ---
# Each line is a True/False column; & keeps only rows where ALL are True.
mask = (
    df["channel"].isin(channels)
    & df["device"].isin(devices)
    & (df["applied_at"].dt.date >= start_date)
    & (df["applied_at"].dt.date <= end_date)
)
filtered = df[mask]

if filtered.empty:
    st.warning("No applications match these filters. Widen your selection in the sidebar.")
    st.stop()

st.caption(f"Showing {len(filtered):,} of {len(df):,} applications")

# --- SECTION 1: headline numbers (KPIs) ---
kpi = run_sql("""
    SELECT COUNT(*)                              AS applications,
           SUM(is_fraud::INT)                    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct,
           ROUND(100.0 * AVG((risk_tier = 'High')::INT), 1) AS high_risk_share_pct
    FROM filtered
""", filtered)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Applications", f"{int(kpi['applications'][0]):,}")
c2.metric("Fraud cases", f"{int(kpi['fraud_cases'][0]):,}")
c3.metric("Fraud rate", f"{float(kpi['fraud_rate_pct'][0])}%")
c4.metric("High-risk share of applications", f"{float(kpi['high_risk_share_pct'][0])}%")

# --- SECTION 2: fraud rate by risk tier ---
tiers = run_sql("""
    SELECT risk_tier,
           COUNT(*)                              AS applications,
           SUM(is_fraud::INT)                    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct
    FROM filtered
    GROUP BY risk_tier
    ORDER BY CASE risk_tier WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
""", filtered)

fig = px.bar(
    tiers,
    x="risk_tier",
    y="fraud_rate_pct",
    color="risk_tier",
    text="fraud_rate_pct",
    category_orders={"risk_tier": ["Low", "Medium", "High"]},
    color_discrete_map={"Low": "#2e7d32", "Medium": "#f9a825", "High": "#c62828"},
    labels={"risk_tier": "Risk tier", "fraud_rate_pct": "Fraud rate (%)"},
    title="Fraud rate by risk tier",
)
st.plotly_chart(fig)

# --- SECTION 3: the numbers behind the chart ---
st.subheader("Tier breakdown")
st.dataframe(tiers, hide_index=True)

# --- SECTION 4: review-policy curve ---
# Question: if analysts review applications from riskiest to safest,
# how much of the fraud do they catch as they work down the list?
st.subheader("Review policy: how much fraud do we catch?")

total_apps = len(filtered)
total_fraud = int(filtered["is_fraud"].sum())  # True counts as 1, so sum = number of fraud cases

# Guard: with some filters there may be no fraud at all, and dividing by 0 would crash
if total_fraud == 0:
    st.info("No fraud cases in the current filter, so there is nothing to catch.")
else:
    # One row per distinct score: how many applications and fraud cases have that score.
    # CAST(... AS BIGINT) makes sure we get plain whole numbers back.
    by_score = run_sql("""
        SELECT risk_score,
               COUNT(*)                                AS applications,
               CAST(SUM(is_fraud::INT) AS BIGINT)      AS fraud_cases
        FROM filtered
        GROUP BY risk_score
    """, filtered)

    # Riskiest first, because analysts would review the highest scores first
    by_score = by_score.sort_values("risk_score", ascending=False)

    # cumsum() = running total. After the top-scoring rows, how much have we
    # reviewed so far, and how much fraud is in that pile?
    by_score["pct_reviewed"] = 100 * by_score["applications"].cumsum() / total_apps
    by_score["pct_fraud_caught"] = 100 * by_score["fraud_cases"].cumsum() / total_fraud

    fig2 = px.line(
        by_score,
        x="pct_reviewed",
        y="pct_fraud_caught",
        markers=True,
        hover_data={"risk_score": True, "pct_reviewed": ":.1f", "pct_fraud_caught": ":.1f"},
        labels={
            "pct_reviewed": "% of applications reviewed",
            "pct_fraud_caught": "% of all fraud caught",
            "risk_score": "Review all with score ≥",
        },
        title="Fraud caught vs. review effort",
    )
    # Dashed diagonal = what random review would achieve (review 30%, catch 30%)
    fig2.add_shape(type="line", x0=0, y0=0, x1=100, y1=100,
                   line=dict(dash="dash", color="gray"))
    fig2.update_xaxes(range=[0, 100])
    fig2.update_yaxes(range=[0, 100])
    st.plotly_chart(fig2)
    st.caption("The further the line bows above the dashed diagonal, the better the score "
               "is at putting fraud near the top of the review queue.")

# --- SECTION 5: what drives fraud? (fraud rate with vs. without each red flag) ---
st.subheader("What drives fraud? Fraud rate with vs. without each red flag")

# Five small queries stacked with UNION ALL. Each answers:
# "does THIS application have THIS flag?" (has_flag = True/False).
# GROUP BY flag then compares the fraud rate of rows WITH the flag to rows WITHOUT it.
# AVG(...) FILTER (WHERE ...) = "average, but only over rows where the condition is true".
flags = run_sql("""
    SELECT flag,
           CAST(SUM(has_flag::INT) AS BIGINT)                                AS apps_with_flag,
           ROUND(100.0 * AVG(is_fraud::INT) FILTER (WHERE has_flag), 2)      AS rate_with_flag,
           ROUND(100.0 * AVG(is_fraud::INT) FILTER (WHERE NOT has_flag), 2)  AS rate_without_flag
    FROM (
        SELECT 'Address mismatch' AS flag, address_mismatch AS has_flag, is_fraud FROM filtered
        UNION ALL
        SELECT '2+ applications in 24h', apps_last_24h >= 2, is_fraud FROM filtered
        UNION ALL
        SELECT 'Account under 30 days', account_age_days < 30, is_fraud FROM filtered
        UNION ALL
        SELECT 'Online channel', channel = 'online', is_fraud FROM filtered
        UNION ALL
        SELECT 'Device $1,400+', device_price >= 1400, is_fraud FROM filtered
    ) AS stacked
    GROUP BY flag
""", filtered)

# lift = how many times riskier the flagged applications are (see src/metrics.py)
flags["lift"] = lift(flags["rate_with_flag"], flags["rate_without_flag"]).round(1)
flags = flags.sort_values("lift", ascending=False)  # strongest flag first

# The chart wants "long" format: one row per (flag, present/absent) pair. melt() does that.
long = flags.melt(
    id_vars="flag",
    value_vars=["rate_with_flag", "rate_without_flag"],
    var_name="group",
    value_name="fraud_rate_pct",
)
long["group"] = long["group"].map({"rate_with_flag": "Flag present", "rate_without_flag": "Flag absent"})

fig3 = px.bar(
    long,
    x="flag",
    y="fraud_rate_pct",
    color="group",
    barmode="group",  # side-by-side bars instead of stacked
    text="fraud_rate_pct",
    category_orders={"flag": list(flags["flag"])},
    color_discrete_map={"Flag present": "#c62828", "Flag absent": "#9e9e9e"},
    labels={"flag": "Red flag", "fraud_rate_pct": "Fraud rate (%)", "group": ""},
    title="Fraud rate with vs. without each red flag",
)
st.plotly_chart(fig3)

st.dataframe(
    flags[["flag", "apps_with_flag", "rate_with_flag", "rate_without_flag", "lift"]],
    hide_index=True,
)
st.caption("Always read the rate next to the count. A flag that only a few dozen applications "
           "have can look very strong or very weak purely by chance.")


# --- SECTION 6: credit score check (we expect NO pattern) ---
# Our generator did NOT use credit score to decide fraud. If this chart showed a clear
# pattern, our analysis would be inventing one. This is a test of the analysis itself.
st.subheader("Credit score check: is it related to fraud?")

bands = run_sql("""
    SELECT CASE WHEN credit_score < 580 THEN 'Under 580'
                WHEN credit_score < 670 THEN '580-669'
                WHEN credit_score < 740 THEN '670-739'
                ELSE '740+'
           END                                   AS credit_band,
           COUNT(*)                              AS applications,
           CAST(SUM(is_fraud::INT) AS BIGINT)    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct
    FROM filtered
    GROUP BY credit_band
    ORDER BY MIN(credit_score)
""", filtered)

# "Normal wobble" for each band (see src/metrics.py)
bands["plus_minus_pct"] = wobble_pct(bands["fraud_rate_pct"], bands["applications"]).round(2)

overall_rate = 100 * filtered["is_fraud"].mean()  # overall fraud rate for the current filters

fig4 = px.bar(
    bands,
    x="credit_band",
    y="fraud_rate_pct",
    error_y="plus_minus_pct",  # the whiskers show normal wobble
    text="fraud_rate_pct",
    category_orders={"credit_band": list(bands["credit_band"])},
    labels={"credit_band": "Credit score band", "fraud_rate_pct": "Fraud rate (%)"},
    title="Fraud rate by credit-score band (whiskers = normal wobble)",
)
fig4.add_hline(y=overall_rate, line_dash="dash", line_color="gray", annotation_text="Overall rate")
st.plotly_chart(fig4)
st.dataframe(bands, hide_index=True)
st.caption("If every bar's whisker reaches the dashed line, the differences between bands "
           "are within normal random wobble: no detectable relationship.")

# --- SECTION 7: dollar impact (which review policy saves the most money?) ---
st.subheader("Dollar impact: which review policy saves the most money?")
st.caption("Assumptions: a fraud that gets through costs the full device price, and a manual "
           "review costs the same no matter who is reviewed. Move the sliders to test other assumptions.")

# Two sliders side by side. Moving either one reruns this whole section.
s1, s2 = st.columns(2)
review_cost = s1.slider("Cost per manual review ($)", 5, 100, 25, step=5)
catch_rate = s2.slider("Share of fraud a review catches (%)", 50, 100, 90, step=5) / 100

# One row per distinct risk score: applications, fraud cases and fraud DOLLARS.
# CASE WHEN is_fraud THEN device_price ELSE 0 END = "count the price only when it was fraud".
money = run_sql("""
    SELECT risk_score,
           COUNT(*)                                                             AS applications,
           CAST(SUM(is_fraud::INT) AS BIGINT)                                   AS fraud_cases,
           CAST(SUM(CASE WHEN is_fraud THEN device_price ELSE 0 END) AS BIGINT) AS fraud_loss
    FROM filtered
    GROUP BY risk_score
""", filtered)

total_fraud_loss = int(money["fraud_loss"].sum())

# Riskiest first, then running totals (see src/metrics.py)
money = net_benefit_table(money, review_cost, catch_rate)

# The best policy is the row with the highest net benefit (idxmax = "index of the maximum").
best = money.loc[money["net_benefit"].idxmax()]

if best["net_benefit"] <= 0:
    st.info("At these costs, manual review loses money, so the best policy is to review nobody.")
else:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Best policy", f"Review score ≥ {int(best['risk_score'])}")
    k2.metric("Applications reviewed", f"{best['pct_reviewed']:.1f}%")
    k3.metric("Fraud loss prevented", f"${best['loss_prevented']:,.0f}")
    k4.metric("Net benefit after review costs", f"${best['net_benefit']:,.0f}")

fig5 = px.line(
    money,
    x="pct_reviewed",
    y="net_benefit",
    markers=True,
    hover_data={"risk_score": True, "pct_reviewed": ":.1f", "net_benefit": ":,.0f"},
    labels={
        "pct_reviewed": "% of applications reviewed",
        "net_benefit": "Net benefit ($)",
        "risk_score": "Review all with score ≥",
    },
    title="Net benefit of each review cutoff",
)
# Dashed line at $0 = what you get by reviewing nobody
fig5.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Review nobody")
if best["net_benefit"] > 0:
    fig5.add_annotation(x=best["pct_reviewed"], y=best["net_benefit"],
                        text="Best", showarrow=True, arrowhead=2)
st.plotly_chart(fig5)

st.caption(f"Total fraud loss if nobody is reviewed: {total_fraud_loss:,} dollars.")
st.dataframe(
    money[["risk_score", "applications", "fraud_cases", "fraud_loss", "pct_reviewed",
           "loss_prevented", "review_total", "net_benefit"]].round(1),
    hide_index=True,
)