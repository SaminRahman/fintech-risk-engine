"""
test_scoring.py
Tests for the risk-score rules. Each test is a tiny example you can check by hand.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.scoring import risk_score, risk_tier


def make_app(**changes):
    """Build ONE fake application with every red flag OFF, then switch on what a test needs."""
    row = {
        "channel": "retail_store",
        "device_price": 700,
        "account_age_days": 1000,
        "apps_last_24h": 0,
        "address_mismatch": False,
    }
    row.update(changes)  # overwrite only the fields the test cares about
    return pd.DataFrame([row])


def score_of(**changes):
    return risk_score(make_app(**changes)).iloc[0]


def test_clean_application_scores_zero():
    assert score_of() == 0


def test_each_flag_adds_its_points():
    assert score_of(channel="online") == 10
    assert score_of(device_price=1400) == 5
    assert score_of(account_age_days=29) == 20
    assert score_of(apps_last_24h=2) == 25
    assert score_of(address_mismatch=True) == 40


def test_flag_boundaries():
    # The rules say "under 30 days", "$1,400 or more" and "2 or more applications".
    assert score_of(account_age_days=30) == 0   # 30 is NOT under 30
    assert score_of(device_price=1399) == 0
    assert score_of(apps_last_24h=1) == 0


def test_worked_example():
    # online (10) + $1,400 phone (5) + 10-day-old account (20) = 35 -> Medium
    app = make_app(channel="online", device_price=1400, account_age_days=10)
    assert risk_score(app).iloc[0] == 35
    assert risk_tier(risk_score(app)).iloc[0] == "Medium"


def test_tier_boundaries():
    tiers = risk_tier(pd.Series([0, 14, 15, 39, 40, 100]))
    assert list(tiers) == ["Low", "Low", "Medium", "Medium", "High", "High"]


def test_python_scoring_matches_the_sql_output():
    # data/processed/... was produced by the SQL in src/risk_score.py.
    path = Path("data/processed/scored_applications.csv")
    if not path.exists():
        pytest.skip("Run python src/risk_score.py first")
    df = pd.read_csv(path)
    assert (risk_score(df) == df["risk_score"]).all()
    assert (risk_tier(df["risk_score"]) == df["risk_tier"]).all()