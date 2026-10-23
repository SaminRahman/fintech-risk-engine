"""
test_data.py
Sanity checks on the generated data (data/raw/applications.csv).

These tests exist because of a real bug: address_mismatch was False for every row
and nothing crashed. A test like the one below catches that in one second.
Run from the project folder with:  python -m pytest
"""

from pathlib import Path

import pandas as pd
import pytest

DATA = Path("data/raw/applications.csv")


@pytest.fixture(scope="module")
def apps():
    """Load the data once and share it with every test in this file."""
    if not DATA.exists():
        pytest.skip("Run python src/generate_data.py first")
    return pd.read_csv(DATA)


def test_row_count_and_unique_ids(apps):
    assert len(apps) == 5000
    assert apps["application_id"].is_unique


def test_no_missing_values(apps):
    assert apps.isna().sum().sum() == 0


def test_categories_are_the_expected_ones(apps):
    assert set(apps["channel"]) == {"retail_store", "online", "call_center"}
    assert set(apps["device"]) == {"Flagship Phone", "Mid-range Phone", "Tablet", "Laptop"}


def test_credit_scores_stay_in_range(apps):
    assert apps["credit_score"].between(300, 850).all()


def test_address_mismatch_is_about_8_percent(apps):
    # The bug made this exactly 0%. We expect about 8%; the wide range allows for random wobble.
    rate = apps["address_mismatch"].mean()
    assert 0.06 < rate < 0.10


def test_overall_fraud_rate_is_plausible(apps):
    # Our hand calculation said about 3.3%. Anything from 2.5% to 4.5% is believable.
    rate = apps["is_fraud"].mean()
    assert 0.025 < rate < 0.045