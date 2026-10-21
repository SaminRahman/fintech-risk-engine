"""
risk_score.py
Adds a risk score and risk tier to every application using SQL,
saves the result, then checks whether the tiers really predict fraud.
"""

import duckdb
from pathlib import Path

# Make sure the output folder exists (exist_ok=True: no error if it's already there)
Path("data/processed").mkdir(parents=True, exist_ok=True)

# --- THE SCORING QUERY ---
# WITH ... AS is a "CTE": it gives a name (scored) to a first step,
# so the second step can build on it. Think of it as a saved intermediate table.
scoring_sql = """
WITH scored AS (
    SELECT *, -- the * means "all columns from the input table"
              -- each CASE WHEN checks a condition and assigns a score based on it
              -- the five results are summed to get a total risk score for each application
              (CASE WHEN channel = 'online'      THEN 10 ELSE 0 END
              + CASE WHEN device_price >= 1400   THEN 5  ELSE 0 END
              + CASE WHEN account_age_days < 30  THEN 20 ELSE 0 END
              + CASE WHEN apps_last_24h >= 2     THEN 25 ELSE 0 END
              + CASE WHEN address_mismatch       THEN 40 ELSE 0 END
              ) AS risk_score
    FROM 'data/raw/applications.csv'
)

SELECT *,
         -- Turn the score into a tier. SQL stops at the first match,
         -- so we check the highest tier first.
         CASE WHEN risk_score >= 40 THEN 'High'
              WHEN risk_score >= 15 THEN 'Medium'
              ELSE 'Low'
         END AS risk_tier
FROM scored
"""

# --- SAVE THE SCORED DATA ---
# COPY (query) TO 'file' writes the query result straight to a CSV.
duckdb.sql(f"COPY ({scoring_sql}) TO 'data/processed/scored_applications.csv' (HEADER, DELIMITER ',')")
print("Saved scored applications to data/processed/scored_applications.csv\n")

# --- LOOK AT THE 5 RISKIEST APPLICATIONS ---
print("Top 5 riskiest applications:")
print(duckdb.sql("""
    SELECT application_id, channel, device_price, risk_score, risk_tier, is_fraud
    FROM 'data/processed/scored_applications.csv'
    ORDER BY risk_score DESC
    LIMIT 5
"""))

# --- THE REAL TEST: does the score predict fraud? ---
# Group by tier and compare fraud rates. A good score means
# High > Medium > Low.
print("Fraud rate by risk tier:")
print(duckdb.sql("""
    SELECT risk_tier,
           COUNT(*)                              AS applications,
           SUM(is_fraud::INT)                    AS fraud_cases,
           ROUND(100.0 * AVG(is_fraud::INT), 2)  AS fraud_rate_pct
    FROM 'data/processed/scored_applications.csv'
    GROUP BY risk_tier
    -- A CASE inside ORDER BY lets us sort in our own order, not alphabetically
    ORDER BY CASE risk_tier WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
"""))