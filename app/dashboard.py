"""
dashboard.py
First Streamlit page: headline numbers and a chart of fraud rate by risk tier.
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

# Stop with a friendly message if Part A's file doesn't exist yet
if not Path(DATA).exists():
    st.error("Scored data not found. Run: python src/risk_score.py")
    st.stop()


# --- HELPER: run a SQL query and return a table (a pandas DataFrame) ---
# @st.cache_data remembers results, so the page doesn't re-run
# the same query every time you click something.
@st.cache_data
def run_query(sql):
    return duckdb.sql(sql).df()


# --- SECTION 1: headline numbers (KPIs) ---
kpi = run_query(f"""
    SELECT COUNT(*)                              AS applications,
           SUM(is_fraud::INT)                    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct,
           ROUND(100.0 * AVG((risk_tier = 'High')::INT), 1) AS high_risk_share_pct
    FROM '{DATA}'
""")

# Split the page into 4 side-by-side columns and put one metric in each
c1, c2, c3, c4 = st.columns(4)
c1.metric("Applications", f"{int(kpi['applications'][0]):,}")
c2.metric("Fraud cases", f"{int(kpi['fraud_cases'][0]):,}")
c3.metric("Fraud rate", f"{float(kpi['fraud_rate_pct'][0])}%")
c4.metric("High-risk share of applications", f"{float(kpi['high_risk_share_pct'][0])}%")

# --- SECTION 2: fraud rate by risk tier (does the score work?) ---
tiers = run_query(f"""
    SELECT risk_tier,
           COUNT(*)                              AS applications,
           SUM(is_fraud::INT)                    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct
    FROM '{DATA}'
    GROUP BY risk_tier
""")

fig = px.bar(
    tiers,
    x="risk_tier",
    y="fraud_rate_pct",
    color="risk_tier",
    text="fraud_rate_pct",
    category_orders={"risk_tier": ["Low", "Medium", "High"]},  # force this left-to-right order
    color_discrete_map={"Low": "#2e7d32", "Medium": "#f9a825", "High": "#c62828"},
    labels={"risk_tier": "Risk tier", "fraud_rate_pct": "Fraud rate (%)"},
    title="Fraud rate by risk tier",
)
st.plotly_chart(fig)

# --- SECTION 3: the numbers behind the chart ---
st.subheader("Tier breakdown")
st.dataframe(tiers, hide_index=True)