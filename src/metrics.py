"""
metrics.py
Small calculations used by the dashboard. Each function does ONE job and has tests.
"""


def wobble_pct(rate_pct, n):
    """Normal random wobble of a rate: about +/- 2 standard errors, in percentage points.

    rate_pct: the fraud rate in percent (for example 3.5)
    n: how many applications that rate is based on. Smaller n means bigger wobble.
    """
    p = rate_pct / 100
    return 200 * (p * (1 - p) / n) ** 0.5


def lift(rate_with, rate_without):
    """How many times riskier the flagged group is (rate with the flag / rate without it).

    Takes two pandas columns. If the 'without' rate is 0, the answer is 'not a number'
    instead of infinity.
    """
    return (rate_with / rate_without).replace([float("inf")], float("nan"))


def net_benefit_table(by_score, review_cost, catch_rate):
    """Add running totals to a table with one row per risk score.

    by_score needs the columns: risk_score, applications, fraud_loss.
    Rows are sorted riskiest first, so each row means
    "review everyone with a score at least this high".
    """
    table = by_score.sort_values("risk_score", ascending=False).copy()
    table["reviewed"] = table["applications"].cumsum()
    table["pct_reviewed"] = 100 * table["reviewed"] / table["applications"].sum()
    table["loss_prevented"] = catch_rate * table["fraud_loss"].cumsum()
    table["review_total"] = review_cost * table["reviewed"]
    table["net_benefit"] = table["loss_prevented"] - table["review_total"]
    return table