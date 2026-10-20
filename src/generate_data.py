"""
generate_data.py
Creates FAKE device-financing applications, with fraud patterns baked in.
Why fake data? Real customer data is private. Synthetic data lets us build
and share a project publicly, and we control exactly what "fraud" looks like.
"""

# --- IMPORTS: tools we borrow from the libraries we installed ---
from pathlib import Path      # Pathlib: handles file/folder paths safely
import numpy as np            # NumPy: fast math and random number generation
import pandas as pd           # Pandas: tables of data (called "DataFrames")

# --- SETTINGS ---
# A random number generator with a "seed" (42). The seed makes the random numbers repeatable, so we can generate the same data again later.
rng = np.random.default_rng(42)
N = 5000  # number of applications to generate

# --- STEP 1: Basic application details ---
# A dictionary: each device maps to its price.
prices = {"Flagship Phone": 1400, "Mid-range Phone": 700, "Tablet": 900, "Laptop": 1600}

# Randomly pick a device for each of the N applications.
# p={...} sets the probability of each device being chosen:  40% flagship, 30% mid-range, etc.
device = rng.choice(list(prices), size=N, p=[0.40, 0.30, 0.15, 0.15])

# Look up the price for each chosen device
# [... d in device] is a "list comprehension": a one-line loop that builds a list of prices for each device in the device array.
amount = np.array([prices[d] for d in device])

# Which channel did the customer apply through?
channel = rng.choice(["retail_store", "online", "call_center"], size=N, p=[0.45, 0.35, 0.20])

# Credit scores follow a bell curve (normal distribution) with a mean of 670 and a standard deviation of 80.
# np.clip keeps the scores to real world values (300-850).
credit_score = np.clip(rng.normal(670, 80, N), 300, 850).round().astype(int)

# How old is the customer account, in days? (0 days to 10 years)
account_age_days = rng.integers(0, 3650, N)

# How many applications did this customer submit in the last 24 hours?
# Poisson is a good model for "how many times a rare event happen".
apps_last_24h = rng.poisson(0.3, N)

# Does the billing address differ from the shipping address? True for ~8% of rows.
address_mismatch = rng.random(N) < 0.08

# --- STEP 2: Build the fraud risk for each application ---
# Start at 1% base risk, then ADD risk for each warning sign.
# (channel == "online") is True/False, and True counts as 1, so the
# line adds 0.02 only when the application was online.
# These are the same red flags you looked for at Rogers.
risk = (
    0.01
    + 0.02 * (channel == "online")        # online orders are riskier
    + 0.015 * (amount >= 1400)            # expensive devices attract fraud
    + 0.03 * (account_age_days < 30)      # brand-new accounts
    + 0.04 * (apps_last_24h >= 2)         # several applications in one day
    + 0.08 * address_mismatch             # biggest single red flag
)

# Roll the dice for each application: if the random number is less than the risk, it's fraud.
is_fraud = rng.random(N) < risk

# ---STEP 3: Put everthing into one table (Pandas DataFrame) ---
df = pd.DataFrame(
    {
        # f-string builds the IDs like APP100000, APP100001, etc.
        "application_id" : [f"APP{100000 + i}" for i in range(N)],
        # Random date and time between January 1 and roughly late September 2026
        "applied_at" : pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 270 * 24 * 60, N), unit="m"),
        "channel" : channel,
        "device" : device,
        "device_price" : amount,
        "credit_score" : credit_score,
        "account_age_days" : account_age_days,
        "apps_last_24h" : apps_last_24h,
        "address_mismatch" : address_mismatch,
        "is_fraud" : is_fraud,
    }
)

# --- STEP 4: Save the table as CSV file ---
out = Path("data/raw/applications.csv")
out.parent.mkdir(parents=True, exist_ok=True) # create data/raw folder if it doesn't exist
df.to_csv(out, index=False) # if index=False, don't save the row numbers

# Print a quick summary too see if it worked
print(f"Saved {len(df):,} applications to {out}")
print(f"Overall fraud rate: {df['is_fraud'].mean():.2%}")  # mean of True/False = percentage