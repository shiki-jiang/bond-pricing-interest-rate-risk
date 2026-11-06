# Fixed-income bond pricing project — specification v2.0

**Purpose:** standalone, reproducible Treasury security-level pricing and curve-risk analysis with concise Python modules. No employer-specific framing.

1. Real Treasury CUSIPs and verifiable October 30, 2026 end-of-day clean reference prices for five securities (2/5/10/20/30-year original terms); hypothetical $100m aggregate face holdings.
2. Fed GSW continuously compounded nominal zero curve, six tenors as of the quote date. Assume regular-way settlement on November 2, 2026.
3. Correct semiannual contractual dates, including month-end coupons, and actual/actual accrued interest. Compare observed and model clean/dirty prices; compute observed- and model-implied YTMs, duration and convexity.
4. Compute curve key-rate DV01, four shock scenarios, and purely illustrative STRIPS hedges. Separate model-risk P&L from observed portfolio value.
5. Regenerate CSVs, chart and Markdown report from included offline inputs; pass deterministic automated tests.

**Out of scope:** forecasts and trading, callable securities, auction prices as secondary-market closes, automated settlement/holiday calendars, financing, historical ETF data, and extrapolating observed prices into fictitious trades.

Inputs: `data/positions.csv`, `data/fed_zero_curve.csv`. Implementation: `bond_engine.py`, `run.py`, `tests/test_bond_engine.py`.
