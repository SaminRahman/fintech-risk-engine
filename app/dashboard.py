"""
dashboard.py (version 2: sidebar filters)
Run with:  streamlit run app/dashboard.py
"""

from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

DATA = "data/processed/scored_applications.csv"

# --- PAGE SETUP ---
st.set_page_config(page_title="Fraud Risk Engine", layout="wide")
st.title("FinTech & Risk Operations Engine")
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