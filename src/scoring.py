"""
scoring.py
The risk-score rules, written once in Python.

The pipeline scores applications in SQL (src/risk_score.py). This file is a second,
independent version of the same rules, used by the tests. If someone changes the
SQL points and forgets this file (or the other way round), a test fails.
"""

import numpy as np
import pandas as pd

# Points per red flag. Keep in step with the CASE WHEN lines in src/risk_score.py.
POINTS = {
    "online": 10,
    "expensive_device": 5,
    "new_account": 20,
    "burst": 25,
    "address_mismatch": 40,
}

HIGH_CUTOFF = 40    # a score of 40 or more -> High
MEDIUM_CUTOFF = 15  # 15 to 39 -> Medium; below 15 -> Low


def risk_score(df):
    """Return the risk score (0-100) for every row of an applications table."""
    return (
        POINTS["online"] * (df["channel"] == "online")
        + POINTS["expensive_device"] * (df["device_price"] >= 1400)
        + POINTS["new_account"] * (df["account_age_days"] < 30)
        + POINTS["burst"] * (df["apps_last_24h"] >= 2)
        + POINTS["address_mismatch"] * df["address_mismatch"].astype(bool)
    )


def risk_tier(score):
    """Turn a column of scores into 'High' / 'Medium' / 'Low'."""
    tier = np.where(score >= HIGH_CUTOFF, "High", np.where(score >= MEDIUM_CUTOFF, "Medium", "Low"))
    return pd.Series(tier, index=score.index)