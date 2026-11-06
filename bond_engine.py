"""Fixed-rate Treasury pricing and curve risk; prices are per $100 face."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from scipy.optimize import brentq


@dataclass(frozen=True)
class Bond:
    name: str  # CUSIP for issued securities; identifier for hypothetical STRIPS.
    maturity: date
    coupon_rate: float  # Annual decimal rate, paid semiannually.
    dated_date: date | None = None  # Start of coupon accrual for issued Treasuries.

    def cashflows(self, settlement: date):
        """Scheduled coupons, time in years, yield periods, cash flows, and accrued."""
        if (settlement >= self.maturity or not 0 <= self.coupon_rate <= 1
                or (self.dated_date is not None and settlement < self.dated_date)):
            raise ValueError("Invalid settlement, maturity, coupon, or dated date.")

        def coupon_date(k):
            d = self.maturity - relativedelta(months=6 * k)
            if self.maturity.day == monthrange(self.maturity.year, self.maturity.month)[1]:
                d = d.replace(day=monthrange(d.year, d.month)[1])
            return d

        dates, k = [], 0
        while (payment := coupon_date(k)) > settlement:
            dates.append(payment)
            k += 1
        dates.reverse()
        previous = coupon_date(k)
        if self.dated_date is not None and previous < self.dated_date:
            raise ValueError("Coupon schedule precedes the Treasury dated date.")
        fraction = (settlement - previous).days / (dates[0] - previous).days
        coupon = 100 * self.coupon_rate / 2
        flows = np.full(len(dates), coupon)
        flows[-1] += 100
        periods = np.arange(1, len(dates) + 1) - fraction
        years = np.array([(d - settlement).days / 365.25 for d in dates])
        return dates, years, periods, flows, coupon * fraction


def price_yield(bond: Bond, settlement: date, ytm: float) -> float:
    """Dirty price using a semiannual bond-equivalent yield."""
    if ytm <= -2:
        raise ValueError("Yield must exceed -200%.")
    _, _, periods, flows, _ = bond.cashflows(settlement)
    return float(np.sum(flows * (1 + ytm / 2) ** (-periods)))


def solve_ytm(bond: Bond, settlement: date, dirty_price: float) -> float:
    """Semiannual bond-equivalent yield from dirty price."""
    if dirty_price <= 0:
        raise ValueError("Dirty price must be positive.")
    return float(brentq(lambda y: price_yield(bond, settlement, y) - dirty_price,
                        -0.99, 2.0, xtol=1e-13))


def yield_risk(bond: Bond, settlement: date, ytm: float) -> tuple[float, float]:
    """Yield-based modified duration and convexity."""
    _, _, periods, flows, _ = bond.cashflows(settlement)
    base = 1 + ytm / 2
    pv = flows * base ** (-periods)
    dirty = pv.sum()
    return (float((periods @ pv) / (2 * base * dirty)),
            float(((periods * (periods + 1)) @ pv) / (4 * base**2 * dirty)))


def price_curve(bond: Bond, settlement: date, curve: pd.Series) -> float:
    """Dirty price from continuously compounded zero-coupon yields."""
    _, years, _, flows, _ = bond.cashflows(settlement)
    rates = np.interp(years, curve.index.to_numpy(dtype=float), curve.to_numpy())
    return float(np.sum(flows * np.exp(-rates * years)))


def key_rate_dv01(bond: Bond, settlement: date, curve: pd.Series,
                  face_usd: float, bump: float = 0.0001) -> pd.Series:
    """USD gain for a 1bp fall at each curve node; symmetric differences."""
    exposure = {}
    for tenor in curve.index:
        higher, lower = curve.copy(), curve.copy()
        higher.loc[tenor] += bump
        lower.loc[tenor] -= bump
        exposure[tenor] = face_usd / 200 * (
            price_curve(bond, settlement, lower) - price_curve(bond, settlement, higher)
        )
    return pd.Series(exposure, name=bond.name)


def read_curve(path) -> tuple[date, pd.Series]:
    """Dated Fed GSW SVENY zero yields in percent at six maturities."""
    raw = pd.read_csv(path)
    if raw["as_of"].nunique() != 1:
        raise ValueError("Curve observations must share an as-of date.")
    rates = raw.set_index("tenor_years")["zero_rate_pct"].sort_index() / 100
    if (list(rates.index) != [1, 2, 5, 10, 20, 30] or rates.isna().any()
            or not rates.between(-0.5, 1).all()):
        raise ValueError("Expected valid SVENY nodes at 1, 2, 5, 10, 20, 30 years.")
    return date.fromisoformat(raw["as_of"].iloc[0]), rates
