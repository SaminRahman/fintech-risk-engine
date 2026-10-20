"""
first_query.py
Your first SQL query. DuckDB lets us run SQL directly on a CSV file,
with no database server to install or set up.
"""

import duckdb

# A triple-quoted string lets us write SQL across several lines.
query = """
SELECT channel,                                   -- group label: which channel
       COUNT(*)                   AS applications,  -- how many applications in each group
       SUM(is_fraud::INT)         AS fraud_cases,   -- ::INT turns True/False into 1/0, so SUM counts frauds
       ROUND(100.0 * AVG(is_fraud::INT), 2) AS fraud_rate_pct  -- average of 1s and 0s = fraud rate
FROM 'data/raw/applications.csv'                  -- DuckDB reads the CSV like a table
GROUP BY channel                                  -- one result row per channel
ORDER BY fraud_rate_pct DESC                      -- riskiest channel at the top
"""

# Run the query and print the result table.
print(duckdb.sql(query))