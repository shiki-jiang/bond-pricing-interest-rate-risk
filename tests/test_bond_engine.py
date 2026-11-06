"""Run offline: python -m pytest -q"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bond_engine import Bond, key_rate_dv01, price_curve, price_yield, read_curve, solve_ytm, yield_risk
from run import analyze

SETTLE = date(2026, 10, 30)
BOND = Bond("Test 5Y", date(2031, 10, 31), 0.04)
CURVE = pd.Series([0.043, 0.045, 0.046, 0.048, 0.051, 0.052], index=[1, 2, 5, 10, 20, 30])


def test_coupon_schedule_and_accrued_interest():
    dates, years, periods, flows, accrued = BOND.cashflows(SETTLE)
    assert dates[0] == date(2026, 10, 31)
    assert dates[-1] == BOND.maturity
    assert len(dates) == 11
    assert flows[-1] == pytest.approx(102)
    assert flows[:-1].sum() == pytest.approx(20)
    assert 0 < periods[0] < 0.01
    assert accrued == pytest.approx(2 * 183 / 184)
    assert years[-1] > 5


def test_price_yield_clean_dirty_and_inverse():
    p = price_yield(BOND, SETTLE, 0.05)
    accrued = BOND.cashflows(SETTLE)[-1]
    assert p > accrued
    assert p - accrued < p
    assert solve_ytm(BOND, SETTLE, p) == pytest.approx(0.05, abs=1e-11)


def test_duration_and_convexity_match_finite_differences():
    y, delta = 0.05, 0.0005
    base = price_yield(BOND, SETTLE, y)
    upper = price_yield(BOND, SETTLE, y + delta)
    lower = price_yield(BOND, SETTLE, y - delta)
    duration, convexity = yield_risk(BOND, SETTLE, y)
    assert duration == pytest.approx((lower - upper) / (2 * base * delta), rel=5e-5)
    assert convexity == pytest.approx((upper + lower - 2 * base) / (base * delta**2), rel=5e-5)


def test_zero_coupon_and_curve_direction():
    zero = Bond("Zero", date(2031, 10, 30), 0)
    assert zero.cashflows(SETTLE)[-1] == 0
    assert price_yield(zero, SETTLE, 0.05) > price_yield(zero, SETTLE, 0.06)
    assert price_curve(zero, SETTLE, CURVE + 0.01) < price_curve(zero, SETTLE, CURVE)


def test_key_rate_dv01_adds_to_parallel_dv01():
    base = key_rate_dv01(BOND, SETTLE, CURVE, 10_000_000).sum()
    parallel = 10_000_000 / 200 * (
        price_curve(BOND, SETTLE, CURVE - 0.0001) -
        price_curve(BOND, SETTLE, CURVE + 0.0001)
    )
    assert base == pytest.approx(parallel, rel=1e-7)


def test_curve_input_is_dated_and_has_correct_nodes():
    path = Path(__file__).resolve().parents[1] / "data" / "fed_zero_curve.csv"
    asof, curve = read_curve(path)
    assert asof == SETTLE
    assert curve.index.tolist() == [1, 2, 5, 10, 20, 30]
    assert curve.loc[10] == pytest.approx(0.049324)


def test_full_project_exports_and_hedge(tmp_path):
    analyze(tmp_path)
    needed = ("bond_valuation.csv", "cashflows.csv", "key_rate_dv01.csv",
              "portfolio_key_rate_dv01.csv", "hedges.csv", "scenarios.csv",
              "key_rate_risk.png", "portfolio_review.md")
    assert all((tmp_path / name).exists() for name in needed)
    risk = pd.read_csv(tmp_path / "portfolio_key_rate_dv01.csv", index_col=0)
    assert np.allclose(risk.loc[[2, 10, 30], "after_hedge_usd_per_bp"], 0, atol=1e-5)
    valuations = pd.read_csv(tmp_path / "bond_valuation.csv")
    assert valuations.shape[0] == 5
    np.testing.assert_allclose(
        valuations.observed_dirty_price,
        valuations.observed_clean_price + valuations.accrued_per_100,
    )
    assert pd.read_csv(tmp_path / "scenarios.csv").shape[0] == 4


def test_real_treasury_dates_and_month_end_coupon():
    from bond_engine import Bond

    short = Bond("91282CRP8", date(2028, 9, 30), 0.0475, date(2026, 9, 30))
    payments, _, _, _, accrued = short.cashflows(date(2026, 11, 2))
    assert payments[:2] == [date(2027, 3, 31), date(2027, 9, 30)]
    assert accrued == pytest.approx(2.375 * 33 / 182)
    with pytest.raises(ValueError):
        short.cashflows(date(2026, 9, 29))


def test_actual_quotes_match_pricing_input(tmp_path):
    analyze(tmp_path)
    positions = pd.read_csv(Path(__file__).resolve().parents[1] / "data/positions.csv")
    priced = pd.read_csv(tmp_path / "bond_valuation.csv")
    assert set(priced.cusip) == set(positions.cusip)
    assert set(positions.quote_date) == {"2026-10-30"}
    assert set(positions.settlement_date) == {"2026-11-02"}
    for row in priced.itertuples(index=False):
        bond = Bond(row.cusip, date.fromisoformat(str(row.maturity)), row.coupon_pct / 100)
        dirty = row.observed_clean_price + row.accrued_per_100
        assert 100 * solve_ytm(bond, date(2026, 11, 2), dirty) == pytest.approx(row.observed_ytm_pct)
        assert row.price_gap_per_100 == pytest.approx(row.model_clean_price - row.observed_clean_price)
    assert (pd.read_csv(tmp_path / "scenarios.csv").iloc[0].portfolio_pnl_usd < 0)
