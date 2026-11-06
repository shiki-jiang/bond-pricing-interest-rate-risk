# Bond Pricing & Interest-Rate Risk Analytics

A reproducible Python case study pricing **five real U.S. Treasury coupon securities** against a Federal Reserve zero-coupon curve, comparing model values with observed end-of-day reference prices, and analyzing rate shocks and illustrative hedges. Positions ($100 million in aggregate face value) are hypothetical.

## Run in PyCharm on macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python run.py
```

The included October 30, 2026 data snapshot runs **offline**; no API key or Bloomberg subscription is needed. All results are recreated in `reports/`. Change `data/positions.csv` and `data/fed_zero_curve.csv` together to study another quoted date and bond set, including a correct settlement date and verified market quotes.

## Inputs

- **Curve:** [Federal Reserve Gürkaynak–Sack–Wright nominal zero yields](https://www.federalreserve.gov/data/nominal-yield-curve.htm), October 30, 2026, `SVENY01/02/05/10/20/30` (continuously compounded annual percentages).
- **Securities:** Treasury CUSIPs with actual coupons, dated dates and maturities; each instrument's terms and observed closing price are linked in [`data/positions.csv`](data/positions.csv). Closing reference marks are from the [U.S. Treasury FedInvest daily pricing file](https://www.treasurydirect.gov/GA-FI/FedInvest/selectSecurityPriceDate), reproduced on the linked security pages. **These are not executed trade prices.**
- **Dates:** Quotes and yield curve from **Friday, October 30, 2026**; assumed regular-way **T+1 settlement Monday, November 2, 2026**. Coupon schedules include end-of-month payments.
- **Portfolio:** Fixed, hypothetical face values of $20m/$25m/$25m/$20m/$10m across approximately 2/5/10/20/30 years remaining contractual maturities.

| CUSIP | Coupon | Maturity | Observed Oct 30 clean close, per $100 face |
|---|---:|---|---:|
| 91282CRP8 | 4.750% | 2028-09-30 | 100.313 |
| 91282CRN3 | 5.000% | 2031-09-30 | 101.219 |
| 91282CRF0 | 4.625% | 2036-08-15 | 97.656 |
| 912810UX4 | 5.125% | 2046-08-15 | 97.406 |
| 912810UW6 | 5.125% | 2056-08-15 | 97.188 |

## Methodology

- Generate Treasury fixed-rate coupon schedules, semiannual interest payments and **actual/actual coupon-period accrued interest**; price in dollars per $100 face, distinguishing **clean** (quote) and **dirty** (including accrued) prices.
- Discount cash flows using the Federal Reserve continuously compounded *zero* rates, with linear interpolation at 1/2/5/10/20/30-year tenors, flat extrapolation at shorter/longer maturities, and ACT/365.25 timing. **Treasury par yields are not substituted for zero yields.**
- Compute market-implied and model-implied yield to maturity from *dirty* prices using semiannual bond-equivalent compounding. Report price differences and both YTMs without calling them returns or arbitrage profits.
- Calculate analytical modified duration and convexity; calculate key-rate DV01 by symmetric ±1-basis-point repricing. Stress-test parallel and slope shocks using full cash-flow repricing.
- Illustrate a **non-executable** hedge with hypothetical 2-, 10-, and 30-year zero-coupon STRIPS, neutralizing those three curve nodes while showing remaining exposure at other tenors.

## Outputs

| File | Content |
|---|---|
| `reports/bond_valuation.csv` | Observed and model clean/dirty prices, price differences, YTMs, duration, convexity, values, DV01 |
| `reports/cashflows.csv` | Scheduled coupons and principal by CUSIP |
| `reports/key_rate_dv01.csv` | Dollar exposures by security and curve tenor |
| `reports/portfolio_key_rate_dv01.csv` | Portfolio key-rate exposures before/after illustrative hedge |
| `reports/hedges.csv` | Signed hypothetical STRIPS positions |
| `reports/scenarios.csv` | Full repricing P&L for four curve shocks |
| `reports/key_rate_risk.png` | Key-rate exposure chart |
| `reports/portfolio_review.md` | Reproducible dated research summary with quotes and sources |

## Limitations

Observed marks and Fed fitted zero yields can differ because of pricing conventions, Treasury-specific liquidity, curve fit and data timing. This is **a cross-sectional valuation exercise, not a backtest**. The zero curve is interpolated from six nodes and the snapshot assumes the supplied T+1 settlement date; there is no automated holiday/payment-day calendar or historical return forecast. The STRIPS are hypothetical and the hedge ignores financing, execution, transaction costs and basis risk. The analysis does not manage money or recommend trades.

The implementation is intentionally small: `bond_engine.py` holds pricing/risk functions, `run.py` handles data, scenarios and reporting, and `tests/` contains deterministic validations. No company-specific application wording is included.
