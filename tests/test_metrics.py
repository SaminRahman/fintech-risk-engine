"""
test_metrics.py
Tests for src/metrics.py using tiny tables where the right answer can be worked out by hand.
"""

import pandas as pd
import pytest

from src.metrics import lift, net_benefit_table, wobble_pct


def test_wobble_hand_example():
    # rate 10%, 100 applications: 200 * sqrt(0.1 * 0.9 / 100) = 200 * 0.03 = 6.0
    assert wobble_pct(10, 100) == pytest.approx(6.0)


def test_smaller_groups_wobble_more():
    assert wobble_pct(3.5, 100) > wobble_pct(3.5, 1000)


def test_wobble_matches_the_dashboard_values():
    # Values shown on the dashboard's credit-score chart
    assert round(wobble_pct(3.41, 645), 2) == 1.43
    assert round(wobble_pct(3.87, 1888), 2) == 0.89


def test_lift_basic_and_zero_division():
    result = lift(pd.Series([10.0, 5.0]), pd.Series([2.0, 0.0]))
    assert result.iloc[0] == pytest.approx(5.0)
    assert pd.isna(result.iloc[1])  # 5 / 0 would be infinity; we return "not a number"


def toy_table():
    # 90 safe applications (score 0) and 10 risky ones (score 40), with fraud dollars for each
    return pd.DataFrame({
        "risk_score": [0, 40],
        "applications": [90, 10],
        "fraud_loss": [1000, 2000],
    })


def test_net_benefit_hand_example():
    # Review cost $10, reviews catch 50% of fraud.
    # Review only score 40: 10 reviews cost $100; prevented 0.5 * 2000 = $1,000; net $900.
    # Review everyone:     100 reviews cost $1,000; prevented 0.5 * 3000 = $1,500; net $500.
    table = net_benefit_table(toy_table(), review_cost=10, catch_rate=0.5)
    assert list(table["risk_score"]) == [40, 0]  # riskiest first
    assert list(table["pct_reviewed"]) == [10, 100]
    assert list(table["net_benefit"]) == [900, 500]


def test_free_perfect_reviews_prevent_all_fraud_loss():
    # If reviews cost nothing and catch everything, reviewing everyone saves the whole $3,000.
    table = net_benefit_table(toy_table(), review_cost=0, catch_rate=1.0)
    assert table["net_benefit"].iloc[-1] == 3000


def test_input_table_is_not_changed():
    original = toy_table()
    net_benefit_table(original, review_cost=10, catch_rate=0.5)
    assert "net_benefit" not in original.columns