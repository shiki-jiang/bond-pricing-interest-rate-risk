"""Produce dated Treasury security valuations and scenario reports: python run.py."""

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from bond_engine import Bond, key_rate_dv01, price_curve, read_curve, solve_ytm, yield_risk

ROOT = Path(__file__).resolve().parent


def money(value):
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def analyze(output: Path):
    quote_date, curve = read_curve(ROOT / "data/fed_zero_curve.csv")
    positions = pd.read_csv(ROOT / "data/positions.csv")
    if (positions.cusip.duplicated().any() or (positions.face_usd <= 0).any()
            or (positions.observed_clean_price <= 0).any()
            or positions.quote_date.nunique() != 1 or positions.quote_date.iloc[0] != str(quote_date)
            or positions.settlement_date.nunique() != 1):
        raise ValueError("CUSIPs, market quotes, quote date, and settlement must be valid.")
    settlement = date.fromisoformat(positions.settlement_date.iloc[0])
    if settlement <= quote_date:
        raise ValueError("Settlement must follow the quoted market date.")

    bonds = [(Bond(r.cusip, date.fromisoformat(r.maturity), r.coupon_pct / 100,
                   date.fromisoformat(r.dated_date)), float(r.face_usd), float(r.observed_clean_price))
             for r in positions.itertuples(index=False)]
    valuations, cashflows, exposures = [], [], {}
    for bond, face, observed_clean in bonds:
        dates, years, _, flows, accrued = bond.cashflows(settlement)
        model_dirty = price_curve(bond, settlement, curve)
        model_ytm = solve_ytm(bond, settlement, model_dirty)
        market_ytm = solve_ytm(bond, settlement, observed_clean + accrued)
        duration, convexity = yield_risk(bond, settlement, model_ytm)
        exposures[bond.name] = key_rate_dv01(bond, settlement, curve, face)
        valuations.append({
            "cusip": bond.name, "maturity": bond.maturity, "coupon_pct": 100 * bond.coupon_rate,
            "face_usd": face, "observed_clean_price": observed_clean,
            "model_clean_price": model_dirty - accrued, "price_gap_per_100": model_dirty - accrued - observed_clean,
            "accrued_per_100": accrued, "observed_dirty_price": observed_clean + accrued,
            "model_dirty_price": model_dirty, "observed_ytm_pct": 100 * market_ytm,
            "model_ytm_pct": 100 * model_ytm, "ytm_gap_bp": 10_000 * (market_ytm - model_ytm),
            "modified_duration": duration, "yield_convexity": convexity,
            "observed_value_usd": face * (observed_clean + accrued) / 100,
            "model_value_usd": face * model_dirty / 100,
            "curve_dv01_usd": exposures[bond.name].sum(),
        })
        cashflows.extend({"cusip": bond.name, "payment_date": d, "years": t,
                          "cashflow_per_100": f} for d, t, f in zip(dates, years, flows))

    table = pd.DataFrame(valuations)
    krd = pd.DataFrame(exposures).T
    total_krd = krd.sum(axis=0)

    # Hypothetical STRIPS basis: hedge only 2Y, 10Y and 30Y key-rate risks.
    hedge_bonds = [Bond(f"STRIP_{t}Y", settlement + relativedelta(years=t), 0)
                   for t in (2, 10, 30)]
    basis = np.column_stack([key_rate_dv01(b, settlement, curve, 1_000_000).to_numpy()
                             for b in hedge_bonds])
    nodes = [curve.index.get_loc(t) for t in (2, 10, 30)]
    hedge_units = np.linalg.solve(basis[nodes], -total_krd.to_numpy()[nodes])
    hedge_faces = hedge_units * 1_000_000
    risk = pd.DataFrame({"before_hedge_usd_per_bp": total_krd,
                         "after_hedge_usd_per_bp": total_krd + pd.Series(basis @ hedge_units, index=curve.index)})
    risk.index.name = "tenor_years"

    shocks = {
        "Parallel +100bp": np.full(len(curve), 100.),
        "Parallel -100bp": np.full(len(curve), -100.),
        "Steepener (-50bp short / +50bp long)": np.interp(curve.index, [1, 30], [-50, 50]),
        "Flattener (+50bp short / -50bp long)": np.interp(curve.index, [1, 30], [50, -50]),
    }
    initial = [price_curve(b, settlement, curve) for b, *_ in bonds]
    initial_hedges = [price_curve(b, settlement, curve) for b in hedge_bonds]
    scenarios = []
    for name, bumps in shocks.items():
        changed = curve + bumps / 10_000
        pnl = sum(face / 100 * (price_curve(b, settlement, changed) - base)
                  for (b, face, _), base in zip(bonds, initial))
        hedge_pnl = sum(face / 100 * (price_curve(b, settlement, changed) - base)
                        for b, face, base in zip(hedge_bonds, hedge_faces, initial_hedges))
        scenarios.append({"scenario": name, "portfolio_pnl_usd": pnl,
                          "pnl_with_hedges_usd": pnl + hedge_pnl})

    output.mkdir(parents=True, exist_ok=True)
    for name, df in (
        ("bond_valuation.csv", table), ("cashflows.csv", pd.DataFrame(cashflows)),
        ("key_rate_dv01.csv", krd.rename_axis("cusip")),
        ("portfolio_key_rate_dv01.csv", risk),
        ("hedges.csv", pd.DataFrame({"instrument": [b.name for b in hedge_bonds],
                                     "signed_face_usd": hedge_faces})),
        ("scenarios.csv", pd.DataFrame(scenarios)),
    ):
        df.to_csv(output / name, index=name in ("key_rate_dv01.csv", "portfolio_key_rate_dv01.csv"))

    risk.rename(columns={"before_hedge_usd_per_bp": "Before hedge",
                         "after_hedge_usd_per_bp": "After selected-node hedge"}).plot(
        kind="bar", figsize=(9, 4), rot=0, title="Treasury key-rate DV01 and illustrative hedging")
    plt.xlabel("Yield curve tenor (years)")
    plt.ylabel("USD gain for a 1bp rate decrease")
    plt.tight_layout()
    plt.savefig(output / "key_rate_risk.png", dpi=160)
    plt.close()

    scenario_df = pd.DataFrame(scenarios)
    price_lines = "\n".join(
        f"| {r.cusip} | {r.observed_clean_price:.3f} | {r.model_clean_price:.3f} | "
        f"{r.price_gap_per_100:+.3f} | {r.observed_ytm_pct:.3f}% | {r.model_ytm_pct:.3f}% |"
        for r in table.itertuples(index=False)
    )
    scenario_lines = "\n".join(
        f"| {r.scenario} | {money(r.portfolio_pnl_usd)} | {money(r.pnl_with_hedges_usd)} |"
        for r in scenario_df.itertuples(index=False)
    )
    source_lines = "\n".join(
        f"- [{r.cusip}]({r.source_url}) — Treasury security terms and Oct 30, 2026 closing price."
        for r in positions.itertuples(index=False)
    )
    report = f"""# U.S. Treasury Bond Pricing & Interest-Rate Risk

**Market data date:** {quote_date}  
**Assumed T+1 settlement:** {settlement}  
**Instruments:** Five real fixed-coupon Treasury CUSIPs; **positions are hypothetical** (${positions.face_usd.sum()/1e6:,.0f} million face value).

## Model prices versus observed Treasury closes

| CUSIP | Observed clean | Model clean | Model − observed | Observed YTM | Model YTM |
|---|---:|---:|---:|---:|---:|
{price_lines}

All prices are **USD per $100 face**. The observations are dated end-of-day reference prices, not trades or executable bids. Positive price differences indicate model prices above the quoted close; they are **not trading profits**.

## Portfolio risk

- Observed-close **dirty** portfolio value: **{money(table.observed_value_usd.sum())}**.
- Curve-implied dirty portfolio value: **{money(table.model_value_usd.sum())}**.
- Curve key-rate DV01 (six nodes): **{money(total_krd.sum())} per bp**.
- Model P&L under a parallel +100 bp curve shock: **{money(scenario_df.iloc[0].portfolio_pnl_usd)}**.
- Hypothetical zero-coupon STRIPS hedges neutralize 2Y/10Y/30Y nodes, leaving exposure at other tenors.

| Yield-curve shock | Original model P&L | With illustrative hedges |
|---|---:|---:|
{scenario_lines}

## Data sources

- [Federal Reserve Gürkaynak–Sack–Wright nominal zero-coupon yield curve](https://www.federalreserve.gov/data/nominal-yield-curve.htm), SVENY rates for {quote_date}.
- U.S. Treasury FedInvest end-of-day closing prices, reproduced on the following security pages:
{source_lines}

## Conventions and limitations

- Actual CUSIPs, coupons, dated dates and maturities; fixed semiannual coupons, **including end-of-month coupon schedules**. Accrued interest uses actual days / actual coupon period. Clean = dirty − accrued.
- Observed closes are **clean**, as published, converted to dirty using modeled accrual. YTMs are computed with semiannual compounding; the observed YTMs are **calculated from quotes**, not separately reported dealer yields.
- Curve pricing discounts scheduled cash flows with continuously compounded Fed SVENY zero rates, linearly interpolated at 1/2/5/10/20/30 years, flat extrapolated outside those nodes, with ACT/365.25 time. The curve was estimated for the market date; settlement is the following business day.
- Discrepancies can reflect curve interpolation and fitting, end-of-day price conventions, liquidity and timing. No executable arbitrage or alpha is established.
- Curve DV01 and shocks are **model** exposures, not mark-to-market backtests. Hedging uses **hypothetical** zero-coupon STRIPS, without quotes, financing, liquidity, costs or basis risk. Weekend/holiday cash-payment adjustments and market calendar automation are outside this dated demonstration.
"""
    (output / "portfolio_review.md").write_text(report)
    print(f"Completed: quoted {quote_date}, settlement {settlement}; "
          f"observed dirty value {money(table.observed_value_usd.sum())}; output: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    analyze(parser.parse_args().output)
