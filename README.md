# FinTech & Risk Operations Engine

A fraud and credit-risk analytics dashboard for device-financing applications, built with Python, DuckDB SQL, and Streamlit.

## Why I built this
I spent 4 years at Rogers investigating device-financing fraud. This project turns that domain experience into a working analytics tool: it detects risky applications, quantifies fraud rates, and presents the findings in a live dashboard.

## Tech stack
- Python (pandas, numpy)
- DuckDB (SQL analytics)
- Streamlit + Plotly (dashboard)

## Documentation
See the full [Project Architecture](docs/architecture.md) for the problem statement, data dictionary, risk rules, results and validation checks.

## Roadmap
- [x] Synthetic data generator
- [x] SQL fraud analysis (by channel, device, account age)
- [x] Rule-based risk scoring
- [x] Streamlit dashboard
- [ ] Deployed live demo

## Dashboard preview
![Dashboard v1](docs/images/dashboard-v1.png)
![Dashboard v2](docs/images/dashboard-v2.png)

## Status
In active development (started October 2026).

## Key findings (synthetic data)
- A rule-based risk score ranks fraud correctly: High-tier applications are 4.8x as likely to be fraud as Low-tier ones.
- Reviewing the riskiest 30% of applications catches 56% of fraud.
- Address mismatch is the strongest red flag (3.7x lift). Credit score, which the data generator ignores, shows no detectable relationship, a check that the analysis doesn't invent patterns.

## Run the tests
```bash
python src/generate_data.py
python src/risk_score.py
python -m pytest
```
The tests check the generated data, the scoring rules (including that the Python rules agree with the SQL) and the dashboard's calculations.

## Author
Samin Yasar Rahman, https://www.linkedin.com/in/saminrahman/
