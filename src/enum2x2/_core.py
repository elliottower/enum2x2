"""The arithmetic, unchanged.

These functions are the part of the package with evidence behind them: they agree
as a set with an exhaustive sweep over every integer table at N = 18 and N = 22,
with a second implementation written from the definitions in exact rational
arithmetic, and — for kappa itself — with four independent R implementations to
within 6e-15. Nothing here is rewritten without re-earning that.
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction


class Enum2x2Error(Exception):
    """Base class for every error this package raises."""


class InvalidInput(Enum2x2Error):
    """A declared figure is impossible: a negative count, a marginal above N, a
    kappa outside [-1, 1]. Raised, because it is a defect in the call rather than
    a property of the source."""


class UndefinedStatistic(Enum2x2Error):
    """A quantity is undefined for the table given, such as kappa where expected
    agreement is exactly one."""


def exact_interval(printed: str, as_percent: bool = False) -> tuple[Fraction, Fraction]:
    """The interval of `rounding_interval`, in exact rationals.

    Membership is decided on these, not on their float images. A printed figure is
    a decimal string and a table's statistic is a ratio of integers, so both are
    rational and the comparison is exact; a tolerance would be admitting values the
    source excludes.
    """
    d = Decimal(printed)
    step = Decimal(1).scaleb(d.as_tuple().exponent)
    lo, hi = Fraction(d - step / 2), Fraction(d + step / 2)
    if as_percent:
        lo, hi = lo / 100, hi / 100
    return lo, hi


def exact_kappa(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Cohen's kappa as a rational, for comparison against an exact interval."""
    n = n11 + n10 + n01 + n00
    if n <= 0:
        raise InvalidInput("the table is empty")
    p_o = Fraction(n11 + n00, n)
    p_e = Fraction((n11 + n10) * (n11 + n01) + (n01 + n00) * (n10 + n00), n * n)
    if p_e == 1:
        raise UndefinedStatistic("expected agreement is 1, so kappa is undefined")
    return (p_o - p_e) / (1 - p_e)


def exactly_rounds_to(value: Fraction, printed: str, as_percent: bool = False) -> bool:
    lo, hi = exact_interval(printed, as_percent)
    return lo <= value <= hi


def rounding_interval(printed: str, as_percent: bool = False) -> tuple[float, float]:
    """The closed interval of exact values that round to a printed string.

    `printed` is the literal text of the source, so "0.10" and "0.1" give
    different intervals, which is why values are declared as strings.

    The interval is closed at both ends deliberately. A value falling exactly on a
    boundary rounds up under one convention and down under another, and published
    sources do not state which they used. Admitting both ends can only widen the
    candidate set, which understates what the source identifies; excluding one end
    can drop the true table, which asserts a precision the source does not carry.
    A binary table of 24 with cells 2, 0, 2, 20 has kappa exactly 0.625, printed
    as either "0.62" or "0.63", and a half-open interval loses it.
    """
    d = Decimal(printed)
    step = Decimal(1).scaleb(d.as_tuple().exponent)
    lo, hi = d - step / 2, d + step / 2
    if as_percent:
        lo, hi = lo / 100, hi / 100
    return float(lo), float(hi)


def rounds_to(value: float, printed: str, as_percent: bool = False) -> bool:
    lo, hi = rounding_interval(printed, as_percent)
    return lo - 1e-12 <= value <= hi + 1e-12


def expected_agreement(p_a: float, p_b: float) -> float:
    return p_a * p_b + (1.0 - p_a) * (1.0 - p_b)


def kappa_from_cells(n11: int, n10: int, n01: int, n00: int) -> float:
    n = n11 + n10 + n01 + n00
    if n <= 0:
        raise InvalidInput("the table is empty")
    p_o = (n11 + n00) / n
    p_e = expected_agreement((n11 + n10) / n, (n11 + n01) / n)
    if abs(1.0 - p_e) < 1e-12:
        raise UndefinedStatistic("expected agreement is 1, so kappa is undefined")
    return (p_o - p_e) / (1.0 - p_e)


def kappa_max(p_a: float, p_b: float) -> float:
    """Largest kappa these marginals permit, using p_o_max = 1 - |p_A - p_B|."""
    p_e = expected_agreement(p_a, p_b)
    p_o_max = min(p_a, p_b) + min(1.0 - p_a, 1.0 - p_b)
    if abs(1.0 - p_e) < 1e-12:
        raise UndefinedStatistic("expected agreement is 1, so kappa_max is undefined")
    return (p_o_max - p_e) / (1.0 - p_e)


def kappa_min(p_a: float, p_b: float) -> float:
    """Smallest kappa these marginals permit.

    Marginals bound kappa from below as well as above. A published kappa outside
    [kappa_min, kappa_max] cannot have come from a table with these marginals, and
    saying so is more informative than reporting that no table survived.
    """
    p_e = expected_agreement(p_a, p_b)
    p_o_min = max(0.0, 1.0 - p_a - p_b) + max(0.0, p_a + p_b - 1.0)
    if abs(1.0 - p_e) < 1e-12:
        raise UndefinedStatistic("expected agreement is 1, so kappa_min is undefined")
    return (p_o_min - p_e) / (1.0 - p_e)


def counts_rounding_to(printed: str, n: int, as_percent: bool = False) -> list[int]:
    """Every integer count on n whose proportion rounds to the printed string.

    Exact throughout: the bounds are rational, so the range is the ceiling of the
    lower bound to the floor of the upper, with no truncation to guard against and
    no tolerance to choose.
    """
    lo, hi = exact_interval(printed, as_percent)
    first = max(0, -((-lo * n).__ceil__()) if False else (lo * n).__ceil__())
    last = min(n, (hi * n).__floor__())
    return list(range(first, last + 1)) if last >= first else []
