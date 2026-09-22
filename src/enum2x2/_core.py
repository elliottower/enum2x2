"""The arithmetic, unchanged.

These functions are the part of the package with evidence behind them: they agree
as a set with an exhaustive sweep over every integer table at N = 18 and N = 22,
with a second implementation written from the definitions in exact rational
arithmetic, and — for kappa itself — with four independent R implementations to
within 6e-15. Nothing here is rewritten without re-earning that.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
from math import ceil, comb, erfc, floor, sqrt


class Enum2x2Error(Exception):
    """Base class for every error this package raises."""


class InvalidInput(Enum2x2Error):
    """A declared figure is impossible: a negative count, a marginal above N, a
    kappa outside [-1, 1]. Raised, because it is a defect in the call rather than
    a property of the source."""


class UndefinedStatistic(Enum2x2Error):
    """A quantity is undefined for the table given, such as kappa where expected
    agreement is exactly one."""


# How a source turned an exact value into the figure it printed. Sources round and
# sources truncate, and a paper says which about as often as it says which tie rule
# it used, so the convention is an input with a conservative union available.
CONVENTIONS = ("half_up", "truncate", "any")


def _interval_bounds(printed: str,
                     convention: str) -> tuple[Decimal, Decimal, bool, bool]:
    """What a printed figure stands for: (lo, hi, lo_closed, hi_closed).

    One unit in the last printed place is the step, read off the literal text, so
    "3.3" and "3.30" give different bounds.

    'truncate' runs one step from the printed value away from zero -- [p, p+step)
    for a positive figure, (p-step, p] for a negative one -- because a source that
    truncates drops digits from the decimal representation and keeps the sign, and
    -0.0537 printed that way gives "-0.05" rather than "-0.06". It is closed at
    the printed value and open at the far end: a value a whole step away truncates
    to the next figure, not to this one. A figure printed as zero is the exception,
    since dropping the digits of -0.004 drops the sign with them.

    'any' is the union of the two. Where the source does not say which it used,
    the union is the only reading that cannot drop the true table.
    """
    d = Decimal(printed)
    step = Decimal(1).scaleb(d.as_tuple().exponent)
    if convention == "half_up":
        return d - step / 2, d + step / 2, True, True
    if convention == "truncate":
        if d > 0:
            return d, d + step, True, False
        if d < 0:
            return d - step, d, False, True
        # A figure printed as zero has lost its sign: -0.004 and 0.004 are both
        # "0.00" once the digits are dropped, so the interval runs either way.
        return -step, step, False, False
    if convention == "any":
        if d > 0:
            return d - step / 2, d + step, True, False
        if d < 0:
            return d - step, d + step / 2, False, True
        return -step, step, False, False
    raise InvalidInput(
        f"convention must be one of {CONVENTIONS}, got {convention!r}")


def _exact_bounds(printed: str, as_percent: bool,
                  convention: str) -> tuple[Fraction, Fraction, bool, bool]:
    """`_interval_bounds` as exact rationals, scaled where the figure is a percent."""
    lo, hi, lo_closed, hi_closed = _interval_bounds(printed, convention)
    lo, hi = Fraction(lo), Fraction(hi)
    if as_percent:
        lo, hi = lo / 100, hi / 100
    return lo, hi, lo_closed, hi_closed


def exact_interval(printed: str, as_percent: bool = False,
                   convention: str = "half_up") -> tuple[Fraction, Fraction]:
    """The interval of `rounding_interval`, in exact rationals.

    Membership is decided on these, not on their float images. A printed figure is
    a decimal string and a table's statistic is a ratio of integers, so both are
    rational and the comparison is exact; a tolerance would be admitting values the
    source excludes.

    The two bounds do not carry which ends belong to the interval: under
    'truncate' and 'any' the far end is excluded. Decide membership with
    `exactly_rounds_to`, which applies the comparison the convention calls for.
    """
    lo, hi, _, _ = _exact_bounds(printed, as_percent, convention)
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


def exactly_rounds_to(value: Fraction, printed: str, as_percent: bool = False,
                      convention: str = "half_up") -> bool:
    lo, hi, lo_closed, hi_closed = _exact_bounds(printed, as_percent, convention)
    return ((lo <= value if lo_closed else lo < value)
            and (value <= hi if hi_closed else value < hi))


def rounding_interval(printed: str, as_percent: bool = False,
                      convention: str = "half_up") -> tuple[float, float]:
    """The interval of exact values a printed string stands for.

    `printed` is the literal text of the source, so "0.10" and "0.1" give
    different intervals, which is why values are declared as strings.

    Under 'half_up', the default, the interval is closed at both ends
    deliberately. A value falling exactly on a boundary rounds up under one
    convention and down under another, and published sources do not state which
    they used. Admitting both ends can only widen the candidate set, which
    understates what the source identifies; excluding one end can drop the true
    table, which asserts a precision the source does not carry. A binary table of
    24 with cells 2, 0, 2, 20 has kappa exactly 0.625, printed as either "0.62" or
    "0.63", and a half-open interval loses it.

    The same argument runs across conventions. Sources truncate as well as round,
    and a printed figure that could only have been truncated falls outside the
    half-up interval, so assuming one convention drops tables the source admits.
    'truncate' reads the figure as [p, p+step) and 'any' as the union of the two,
    which is the reading to use where the source does not say. Under those two the
    far end is excluded; `rounds_to` applies the comparison the convention calls
    for, and the bounds alone do not carry it.
    """
    lo, hi, _, _ = _interval_bounds(printed, convention)
    if as_percent:
        lo, hi = lo / 100, hi / 100
    return float(lo), float(hi)


def rounds_to(value: float, printed: str, as_percent: bool = False,
              convention: str = "half_up") -> bool:
    """The float image of `exactly_rounds_to`.

    A tolerance absorbs representation error at a closed end. An open end takes
    none: the excluded point is a single rational, and widening past it would
    admit values the convention excludes for a reason that is not arithmetic.
    """
    lo, hi, lo_closed, hi_closed = _exact_bounds(printed, as_percent, convention)
    lo, hi = float(lo), float(hi)
    return ((lo - 1e-12 <= value if lo_closed else lo < value)
            and (value <= hi + 1e-12 if hi_closed else value < hi))


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


def counts_rounding_to(printed: str, n: int, as_percent: bool = False,
                       convention: str = "half_up") -> list[int]:
    """Every integer count on n whose proportion matches the printed string.

    Exact throughout: the bounds are rational, so the range is the ceiling of the
    lower bound to the floor of the upper, with no truncation to guard against and
    no tolerance to choose. A count landing exactly on an open end is dropped,
    which is where a truncating source parts from a rounding one.
    """
    lo, hi, lo_closed, hi_closed = _exact_bounds(printed, as_percent, convention)
    first, last = ceil(lo * n), floor(hi * n)
    if not lo_closed and first == lo * n:
        first += 1
    if not hi_closed and last == hi * n:
        last -= 1
    first, last = max(0, first), min(n, last)
    return list(range(first, last + 1)) if last >= first else []

# ------------------------------------------------------------------ McNemar
#
# McNemar's test looks only at the two discordant cells. Its statistic is
# therefore a function of n10 and n01 alone, which is why a published McNemar
# result closes a table whose marginals are already printed: the marginals fix
# n10 - n01, and the statistic fixes n10 + n01.
#
# The exact (binomial) variant is a ratio of integers, so membership in a
# printed interval is decided exactly, as it is for kappa. The chi-square
# variants are not: the statistic is rational but the tail probability is not,
# so those are computed in double precision and say so.


def mcnemar_exact_p(n10: int, n01: int) -> Fraction:
    """Two-sided exact McNemar p: a sign test on the discordant pairs.

    Exact, as a Fraction. With no discordant pairs the test has nothing to
    decide and the p is 1.
    """
    m = n10 + n01
    if m == 0:
        return Fraction(1)
    k = max(n10, n01)
    tail = sum(comb(m, i) for i in range(k, m + 1))
    return min(Fraction(1), Fraction(2 * tail, 2 ** m))



def mcnemar_midp(n10: int, n01: int) -> Fraction:
    """Two-sided mid-p McNemar, exactly, as a Fraction.

    Fagerland, Lydersen and Laake (2013) give it as the two-sided exact p less
    the point probability of the observed discordant count, with a separate form
    when the two discordant cells are equal:

        mid-p = two-sided p - f(n12 | n)
        mid-p = 1 - f(n12 | n) / 2                 when n12 == n21

    where f is the binomial point probability at n = n12 + n21, p = 1/2. Mid-p
    sits between the conservative exact test and the asymptotic one; a source
    that used it and a reader who assumes the exact test will disagree, which is
    why the variant has to be an input rather than a default.
    """
    m = n10 + n01
    if m == 0:
        return Fraction(1)
    point = Fraction(comb(m, min(n10, n01)), 2 ** m)
    if n10 == n01:
        return 1 - point / 2
    return mcnemar_exact_p(n10, n01) - point


def mcnemar_chisq(n10: int, n01: int, continuity: bool = False) -> Fraction:
    """McNemar's chi-square statistic, exactly, with or without Yates's correction.

    Undefined when the two criteria never disagree, since the statistic divides
    by the discordant total.
    """
    m = n10 + n01
    if m == 0:
        raise UndefinedStatistic(
            "no discordant pairs, so McNemar's chi-square divides by zero")
    d = abs(n10 - n01)
    num = (d - 1) ** 2 if continuity else d * d
    if continuity and d == 0:
        num = 1
    return Fraction(num, m)


def chisq1_sf(x: float) -> float:
    """Upper tail of chi-square on 1 df. Double precision, not exact."""
    if x <= 0:
        return 1.0
    return erfc(sqrt(x / 2.0))


def mcnemar_p(n10: int, n01: int, test: str = "exact") -> Fraction | float:
    """The p a given McNemar variant reports for one pair of discordant cells.

    'exact' returns a Fraction and is decided exactly. 'chisq' and 'chisq_cc'
    return floats: the statistic is rational, its tail probability is not.
    """
    if test == "exact":
        return mcnemar_exact_p(n10, n01)
    if test == "midp":
        return mcnemar_midp(n10, n01)
    if test in ("chisq", "chisq_cc"):
        try:
            return chisq1_sf(float(mcnemar_chisq(n10, n01, continuity=(test == "chisq_cc"))))
        except UndefinedStatistic:
            return 1.0
    raise InvalidInput(
        f"test must be 'exact', 'midp', 'chisq' or 'chisq_cc', got {test!r}")


def satisfies_printed_p(value, printed: str, test: str,
                        convention: str = "half_up") -> bool:
    """Does a candidate table's p match what a source printed?

    A source prints either a bound ('<0.001') or a rounded point value
    ('0.0002'). A bound is a strict inequality; a point value is the rounding
    interval used everywhere else in this package.
    """
    text = printed.strip().replace(" ", "")
    for op in ("<=", ">=", "<", ">"):
        if text.startswith(op):
            rest = text[len(op):]
            try:
                bound = Fraction(Decimal(rest))
            except (InvalidOperation, ValueError) as exc:
                raise InvalidInput(f"{printed!r} is not a number after {op!r}") from exc
            v = value if isinstance(value, Fraction) else Fraction(value).limit_denominator(10**12)
            return {"<": v < bound, "<=": v <= bound,
                    ">": v > bound, ">=": v >= bound}[op]
    if isinstance(value, Fraction):
        return exactly_rounds_to(value, text, convention=convention)
    return rounds_to(float(value), text, convention=convention)

# ------------------------------------------------- other closing statistics
#
# With N and both marginals fixed a 2x2 has one degree of freedom left, so any
# statistic that varies with the table closes it. These are the ones a paper
# comparing two criteria on one population is likely to have printed. Each is
# exact: a ratio of integers, compared against the printed string's rounding
# interval in exact rational arithmetic, as kappa is.
#
# Each raises UndefinedStatistic where its denominator vanishes, which is a
# property of that candidate table and not a reason to abandon the enumeration.


def _f(num: int, den: int) -> Fraction:
    if den == 0:
        raise UndefinedStatistic("the statistic divides by zero on this table")
    return Fraction(num, den)


def observed_agreement(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    return _f(n11 + n00, n11 + n10 + n01 + n00)


def positive_agreement(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """PPA. The FDA's concordance measure for a test against a comparator."""
    return _f(2 * n11, 2 * n11 + n10 + n01)


def negative_agreement(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """NPA, the same measure on the negatives."""
    return _f(2 * n00, 2 * n00 + n10 + n01)


def jaccard(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Overlap among the cases either criterion identifies. Ignores n00."""
    return _f(n11, n11 + n10 + n01)


def pabak(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Prevalence-adjusted bias-adjusted kappa: 2*po - 1."""
    return 2 * observed_agreement(n11, n10, n01, n00) - 1


def scott_pi(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Like kappa, but chance agreement uses the pooled marginal."""
    n = n11 + n10 + n01 + n00
    po = _f(n11 + n00, n)
    pbar = Fraction(2 * n11 + n10 + n01, 2 * n)
    pe = pbar ** 2 + (1 - pbar) ** 2
    if pe == 1:
        raise UndefinedStatistic("chance agreement is 1, so Scott's pi is undefined")
    return (po - pe) / (1 - pe)


def gwet_ac1(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Gwet's AC1, proposed because kappa falls when prevalence is extreme."""
    n = n11 + n10 + n01 + n00
    po = _f(n11 + n00, n)
    pbar = Fraction(2 * n11 + n10 + n01, 2 * n)
    pe = 2 * pbar * (1 - pbar)
    if pe == 1:
        raise UndefinedStatistic("chance agreement is 1, so AC1 is undefined")
    return (po - pe) / (1 - pe)


def prevalence_index(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Byrt's prevalence index, (n11 - n00) / N.

    Determined by the marginals: n00 = N - nA - nB + n11, so n11 - n00 reduces to
    nA + nB - N and the index to (nA + nB - N)/N. Like the bias index it closes
    nothing on its own, and is offered for checking a source against itself.
    """
    return _f(n11 - n00, n11 + n10 + n01 + n00)


def bias_index(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Byrt's bias index, (n10 - n01) / N.

    Reduces to (nA - nB)/N, so like the prevalence index it is fixed by the
    marginals and closes nothing on its own.
    """
    return _f(n10 - n01, n11 + n10 + n01 + n00)


def odds_ratio(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Cross-product ratio."""
    return _f(n11 * n00, n10 * n01)


def mcnemar_odds_ratio(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """The paired odds ratio, n10 / n01, which McNemar's test is about."""
    return _f(n10, n01)


def phi(n11: int, n10: int, n01: int, n00: int) -> Fraction:
    """Phi squared, exactly. Phi itself is generally irrational, so the
    comparison is made on the square and the printed value squared."""
    num = (n11 * n00 - n10 * n01) ** 2
    den = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    return _f(num, den)


# name -> (function, human description). Every one is exact.
# Accepted as constraints, but functions of the marginals alone, so neither can
# be the one further quantity that closes the table. Passing only one of these is
# insufficient reporting, not a recovery.
MARGINAL_DETERMINED = frozenset({"prevalence_index", "bias_index"})

CLOSING_STATISTICS = {
    "ppa": (positive_agreement, "positive agreement, 2*n11/(2*n11+n10+n01)"),
    "npa": (negative_agreement, "negative agreement, 2*n00/(2*n00+n10+n01)"),
    "jaccard": (jaccard, "overlap among cases either criterion identifies"),
    "pabak": (pabak, "prevalence-adjusted bias-adjusted kappa, 2*po-1"),
    "scott_pi": (scott_pi, "Scott's pi"),
    "gwet_ac1": (gwet_ac1, "Gwet's AC1"),
    "prevalence_index": (prevalence_index, "Byrt's prevalence index; fixed by the marginals"),
    "bias_index": (bias_index, "Byrt's bias index; fixed by the marginals"),
    "odds_ratio": (odds_ratio, "cross-product odds ratio"),
    "mcnemar_odds_ratio": (mcnemar_odds_ratio, "paired odds ratio, n10/n01"),
    "phi_squared": (phi, "phi squared"),
}
