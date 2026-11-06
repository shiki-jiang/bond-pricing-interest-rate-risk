# U.S. Treasury Bond Pricing & Interest-Rate Risk

**Market data date:** 2026-10-30  
**Assumed T+1 settlement:** 2026-11-02  
**Instruments:** Five real fixed-coupon Treasury CUSIPs; **positions are hypothetical** ($100 million face value).

## Model prices versus observed Treasury closes

| CUSIP | Observed clean | Model clean | Model − observed | Observed YTM | Model YTM |
|---|---:|---:|---:|---:|---:|
| 91282CRP8 | 100.313 | 100.301 | -0.012 | 4.575% | 4.582% |
| 91282CRN3 | 101.219 | 101.208 | -0.011 | 4.718% | 4.721% |
| 91282CRF0 | 97.656 | 97.540 | -0.116 | 4.929% | 4.944% |
| 912810UX4 | 97.406 | 97.791 | +0.385 | 5.338% | 5.306% |
| 912810UW6 | 97.188 | 96.899 | -0.289 | 5.314% | 5.333% |

All prices are **USD per $100 face**. The observations are dated end-of-day reference prices, not trades or executable bids. Positive price differences indicate model prices above the quoted close; they are **not trading profits**.

## Portfolio risk

- Observed-close **dirty** portfolio value: **$99,759,078**.
- Curve-implied dirty portfolio value: **$99,772,820**.
- Curve key-rate DV01 (six nodes): **$73,170 per bp**.
- Model P&L under a parallel +100 bp curve shock: **-$6,865,817**.
- Hypothetical zero-coupon STRIPS hedges neutralize 2Y/10Y/30Y nodes, leaving exposure at other tenors.

| Yield-curve shock | Original model P&L | With illustrative hedges |
|---|---:|---:|
| Parallel +100bp | -$6,865,817 | -$3,435,170 |
| Parallel -100bp | $7,826,108 | $3,922,353 |
| Steepener (-50bp short / +50bp long) | $649,019 | $289,858 |
| Flattener (+50bp short / -50bp long) | -$568,505 | -$276,340 |

## Data sources

- [Federal Reserve Gürkaynak–Sack–Wright nominal zero-coupon yield curve](https://www.federalreserve.gov/data/nominal-yield-curve.htm), SVENY rates for 2026-10-30.
- U.S. Treasury FedInvest end-of-day closing prices, reproduced on the following security pages:
- [91282CRP8](https://saferate.com/treasury/securities/91282CRP8) — Treasury security terms and Oct 30, 2026 closing price.
- [91282CRN3](https://saferate.com/treasury/securities/91282CRN3) — Treasury security terms and Oct 30, 2026 closing price.
- [91282CRF0](https://saferate.com/treasury/securities/91282CRF0) — Treasury security terms and Oct 30, 2026 closing price.
- [912810UX4](https://saferate.com/treasury/securities/912810UX4) — Treasury security terms and Oct 30, 2026 closing price.
- [912810UW6](https://saferate.com/treasury/securities/912810UW6) — Treasury security terms and Oct 30, 2026 closing price.

## Conventions and limitations

- Actual CUSIPs, coupons, dated dates and maturities; fixed semiannual coupons, **including end-of-month coupon schedules**. Accrued interest uses actual days / actual coupon period. Clean = dirty − accrued.
- Observed closes are **clean**, as published, converted to dirty using modeled accrual. YTMs are computed with semiannual compounding; the observed YTMs are **calculated from quotes**, not separately reported dealer yields.
- Curve pricing discounts scheduled cash flows with continuously compounded Fed SVENY zero rates, linearly interpolated at 1/2/5/10/20/30 years, flat extrapolated outside those nodes, with ACT/365.25 time. The curve was estimated for the market date; settlement is the following business day.
- Discrepancies can reflect curve interpolation and fitting, end-of-day price conventions, liquidity and timing. No executable arbitrage or alpha is established.
- Curve DV01 and shocks are **model** exposures, not mark-to-market backtests. Hedging uses **hypothetical** zero-coupon STRIPS, without quotes, financing, liquidity, costs or basis risk. Weekend/holiday cash-payment adjustments and market calendar automation are outside this dated demonstration.
