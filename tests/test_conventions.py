"""What a printed figure means when the source truncated rather than rounded.

A published figure stands for an interval, and which interval depends on how the
source got from the exact value to the digits it printed. Assuming one convention
is not free: a figure that could only have been truncated lies outside the
round-half-up interval, so the table that produced it is excluded and the
comparison comes back with no compatible table at all.

The default is 'half_up' and stays there. These check that it is untouched, that
the other two readings are right at their endpoints, and that 'any' admits
everything either of the others does.
"""
from __future__ import annotations

import random
import pathlib
import sys
from decimal import Decimal
from fractions import Fraction
from math import floor

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from enum2x2 import (CONVENTIONS, INFEASIBLE, UNIQUE, InvalidInput,
                     exact_interval, exact_kappa, exactly_rounds_to, recover,
                     rounding_interval, rounds_to)
from enum2x2._core import counts_rounding_to


def _printed(value: Fraction, dp: int, how: str) -> str:
    """The figure a source using `how` would print for this exact value."""
    scaled = value * 10 ** dp
    n = floor(scaled + Fraction(1, 2)) if how == "half_up" else int(scaled)
    return f"{Decimal(n).scaleb(-dp):.{dp}f}"


def _rational(rng: random.Random) -> Fraction:
    den = rng.randrange(1, 10_000)
    return Fraction(rng.randrange(-2 * den, 2 * den), den)


def _table(rng: random.Random) -> tuple[int, int, int, int]:
    """A random table with both marginals strictly inside (0, N), so kappa exists."""
    while True:
        n = rng.randrange(60, 500)
        n11 = rng.randrange(0, n + 1)
        n10 = rng.randrange(0, n - n11 + 1)
        n01 = rng.randrange(0, n - n11 - n10 + 1)
        n00 = n - n11 - n10 - n01
        if 0 < n11 + n10 < n and 0 < n11 + n01 < n:
            return n11, n10, n01, n00


# ------------------------------------------------------------- the default

def test_the_default_is_half_up_and_half_up_is_the_interval_it_always_was():
    rng = random.Random()
    for _ in range(500):
        dp = rng.randrange(0, 5)
        p = _printed(_rational(rng), dp, "half_up")
        base, half = Fraction(Decimal(p)), Fraction(1, 2 * 10 ** dp)
        assert exact_interval(p) == (base - half, base + half)
        assert exact_interval(p) == exact_interval(p, convention="half_up")
        assert rounding_interval(p) == rounding_interval(p, convention="half_up")
        assert exactly_rounds_to(base - half, p) and exactly_rounds_to(base + half, p)


def test_the_default_recovery_is_the_half_up_recovery():
    for call in (dict(n=768, n_a=158, n_b=466, kappa="0.29"),
                 dict(n=20306, n_a=866, n_b=1603, kappa="0.22"),
                 dict(n=240, p_a="0.512", n_b=100, kappa="0.18"),
                 dict(n=370, n_a=165, n_b=160, kappa="0.48", agreement="73",
                      agreement_as_percent=True)):
        a, b = recover(**call), recover(**call, convention="half_up")
        assert a.status == b.status
        assert [t.as_dict() for t in a] == [t.as_dict() for t in b]
        assert "convention" not in a.published


# ------------------------------------------------- the value that was printed

@pytest.mark.parametrize("how", ["half_up", "truncate"])
def test_the_interval_contains_the_value_that_produced_the_figure(how):
    rng = random.Random()
    for _ in range(3000):
        value, dp = _rational(rng), rng.randrange(0, 5)
        p = _printed(value, dp, how)
        assert exactly_rounds_to(value, p, convention=how), (value, p)
        assert exactly_rounds_to(value, p, convention="any"), (value, p)


def test_any_is_exactly_the_union_of_the_two_conventions():
    rng = random.Random()
    for _ in range(1000):
        dp = rng.randrange(0, 5)
        p = _printed(_rational(rng), dp, "half_up")
        base, step = Fraction(Decimal(p)), Fraction(1, 10 ** dp)
        probes = [base + step * Fraction(rng.randrange(-30, 31), 10) for _ in range(8)]
        probes += [base, base - step, base + step,
                   base - step / 2, base + step / 2]
        for v in probes:
            union = (exactly_rounds_to(v, p, convention="half_up")
                     or exactly_rounds_to(v, p, convention="truncate"))
            assert exactly_rounds_to(v, p, convention="any") is union, (v, p)


def test_the_far_end_of_a_truncated_figure_belongs_to_the_next_figure():
    # A source that truncates prints "3.3" for everything in [3.3, 3.4). 3.4 itself
    # prints as "3.4", so admitting it would admit a value the source excludes.
    assert exact_interval("3.3", convention="truncate") == (Fraction(33, 10),
                                                            Fraction(17, 5))
    assert exactly_rounds_to(Fraction(33, 10), "3.3", convention="truncate")
    assert exactly_rounds_to(Fraction(3399, 1000), "3.3", convention="truncate")
    assert not exactly_rounds_to(Fraction(34, 10), "3.3", convention="truncate")
    assert not exactly_rounds_to(Fraction(3299, 1000), "3.3", convention="truncate")
    # Half-up keeps both ends, and 'any' keeps the low end and drops the high one.
    assert exactly_rounds_to(Fraction(3299, 1000), "3.3", convention="any")
    assert not exactly_rounds_to(Fraction(34, 10), "3.3", convention="any")


def test_a_figure_printed_as_zero_keeps_both_sides_under_truncation():
    # Dropping the digits of -0.004 drops its sign too, so a truncating source
    # prints "0.00" for it. Reading that as [0, 0.01) would exclude every table
    # whose kappa is a little below zero, which is a reading the printed figure
    # cannot be told apart from a little above.
    assert exact_interval("0.00", convention="truncate") == (Fraction(-1, 100),
                                                             Fraction(1, 100))
    assert exactly_rounds_to(Fraction(-4, 1000), "0.00", convention="truncate")
    assert exactly_rounds_to(Fraction(4, 1000), "0.00", convention="truncate")
    assert not exactly_rounds_to(Fraction(-1, 100), "0.00", convention="truncate")
    assert not exactly_rounds_to(Fraction(1, 100), "0.00", convention="truncate")
    assert exact_interval("0.00") == (Fraction(-1, 200), Fraction(1, 200))


@pytest.mark.parametrize("convention", CONVENTIONS)
def test_a_negative_figure_mirrors_the_positive_one(convention):
    # Truncation drops digits and keeps the sign, so -0.0537 prints as "-0.05" and
    # not "-0.06". The interval mirrors with the ends exchanged; a floor-truncation
    # would put -0.05 and 0.05 on different sides of their printed figures.
    rng = random.Random()
    for _ in range(500):
        value, dp = abs(_rational(rng)), rng.randrange(0, 5)
        p = _printed(value, dp, "truncate")
        if Decimal(p) == 0:
            continue
        lo, hi = exact_interval(p, convention=convention)
        assert exact_interval("-" + p, convention=convention) == (-hi, -lo)
        assert (exactly_rounds_to(-value, "-" + p, convention=convention)
                is exactly_rounds_to(value, p, convention=convention))


@pytest.mark.parametrize("convention", CONVENTIONS)
def test_a_percentage_is_the_same_interval_scaled(convention):
    rng = random.Random()
    for _ in range(500):
        value, dp = _rational(rng), rng.randrange(0, 4)
        p = _printed(value, dp, "truncate")
        lo, hi = exact_interval(p, convention=convention)
        assert exact_interval(p, as_percent=True,
                              convention=convention) == (lo / 100, hi / 100)
        assert (exactly_rounds_to(value / 100, p, True, convention)
                is exactly_rounds_to(value, p, False, convention))


@pytest.mark.parametrize("convention", CONVENTIONS)
def test_the_float_path_agrees_with_the_exact_one_away_from_the_endpoints(convention):
    # rounds_to is the float image of exactly_rounds_to, with a tolerance at each
    # closed end; the two must not disagree anywhere that tolerance is not in play.
    rng = random.Random()
    for _ in range(1000):
        dp = rng.randrange(0, 4)
        p = _printed(_rational(rng), dp, "half_up")
        base, step = Fraction(Decimal(p)), Fraction(1, 10 ** dp)
        lo, hi = exact_interval(p, convention=convention)
        for _ in range(6):
            v = base + step * Fraction(rng.randrange(-30, 31), 10)
            if min(abs(v - lo), abs(v - hi)) < Fraction(1, 10 ** 6):
                continue
            assert (rounds_to(float(v), p, convention=convention)
                    is exactly_rounds_to(v, p, convention=convention)), (v, p)


# ----------------------------------------------------------------- counts

@pytest.mark.parametrize("convention", CONVENTIONS)
def test_the_counts_are_exactly_those_whose_proportion_matches(convention):
    rng = random.Random()
    for _ in range(400):
        n = rng.randrange(1, 400)
        dp = rng.randrange(0, 4)
        as_percent = rng.random() < 0.5
        value = Fraction(rng.randrange(0, n + 1), n)
        p = _printed(value * 100 if as_percent else value, dp,
                     rng.choice(("half_up", "truncate")))
        assert counts_rounding_to(p, n, as_percent, convention) == [
            c for c in range(n + 1)
            if exactly_rounds_to(Fraction(c, n), p, as_percent, convention)]


def test_a_count_landing_on_the_far_end_belongs_to_the_next_figure():
    # 12/20 is 0.6 exactly, which a truncating source prints as "0.6" and not
    # "0.5"; a closed upper end would let one count match two printed figures.
    assert counts_rounding_to("0.5", 20, convention="truncate") == [10, 11]
    assert counts_rounding_to("0.5", 20) == [9, 10, 11]
    assert counts_rounding_to("0.5", 20, convention="any") == [9, 10, 11]


# ---------------------------------------------------------------- recovery

def test_a_table_whose_figures_were_truncated_survives_under_truncate_and_any():
    rng = random.Random()
    checked = lost_to_half_up = 0
    for _ in range(300):
        n11, n10, n01, n00 = _table(rng)
        n = n11 + n10 + n01 + n00
        kappa = exact_kappa(n11, n10, n01, n00)
        agreement = Fraction(n11 + n00, n) * 100
        k, a = _printed(kappa, 2, "truncate"), _printed(agreement, 1, "truncate")
        if not -1 <= Decimal(k) <= 1:
            continue
        call = dict(n=n, n_a=n11 + n10, n_b=n11 + n01, kappa=k, agreement=a,
                    agreement_as_percent=True)
        truth = {"n11": n11, "n10": n10, "n01": n01, "n00": n00}
        for convention in ("truncate", "any"):
            assert truth in [t.as_dict() for t in recover(**call,
                                                          convention=convention)], \
                (truth, k, a, convention)
        checked += 1
        lost_to_half_up += truth not in [t.as_dict() for t in recover(**call)]
    assert checked > 200
    # Truncated figures are not a hypothetical: reading them as rounded loses the
    # table that produced them often enough to empty a whole published comparison.
    assert lost_to_half_up > 0


def test_any_returns_every_table_either_convention_returns():
    rng = random.Random()
    for _ in range(200):
        n11, n10, n01, n00 = _table(rng)
        n = n11 + n10 + n01 + n00
        kappa = exact_kappa(n11, n10, n01, n00)
        k = _printed(kappa, rng.randrange(2, 4), rng.choice(("half_up", "truncate")))
        if not -1 <= Decimal(k) <= 1:
            continue
        call = dict(n=n, p_a=_printed(Fraction(n11 + n10, n) * 100, 1, "half_up"),
                    p_b=_printed(Fraction(n11 + n01, n) * 100, 1, "truncate"),
                    kappa=k, marginals_as_percent=True)
        sets = {c: {(t.n11, t.n10, t.n01, t.n00)
                    for t in recover(**call, convention=c)} for c in CONVENTIONS}
        assert sets["half_up"] | sets["truncate"] <= sets["any"], call


def test_a_figure_the_source_truncated_falls_outside_the_half_up_interval():
    # Goyal et al. 2025 compare two criteria for gestational diabetes on 353
    # women, printing kappa 0.648 and a disagreement of 10.7%. The marginals and
    # kappa determine one table, whose 38 discordant cases are 10.765% of 353 --
    # a figure a truncating source prints as "10.7" and a rounding one as "10.8".
    # Read as rounded, the printed disagreement rejects the only table its own
    # kappa admits.
    r = recover(353, n_a=84, n_b=46, kappa="0.648")
    assert r.status == UNIQUE
    assert r.table.as_dict() == {"n11": 46, "n10": 38, "n01": 0, "n00": 269}
    discordant = Fraction(r.table.n_discordant, 353)
    assert not exactly_rounds_to(discordant, "10.7", as_percent=True)
    assert exactly_rounds_to(discordant, "10.7", as_percent=True,
                             convention="truncate")
    assert exactly_rounds_to(discordant, "10.7", as_percent=True, convention="any")


def test_a_marginal_no_integer_count_can_produce_names_that_marginal():
    # 44.6% of 370 is between 165 (44.59%) and 166 (44.86%), so under truncation
    # no count prints as "44.6" at all. The kappa is not what excluded.
    r = recover(370, p_a="44.6", p_b="43.2", kappa="0.48",
                marginals_as_percent=True, convention="truncate")
    assert r.status == INFEASIBLE
    assert "no integer count on 370" in r.reason and "p_a" in r.reason


def test_the_convention_used_travels_with_the_result():
    r = recover(768, n_a=158, n_b=466, kappa="0.29", convention="any")
    assert r.published["convention"] == "any"


# ---------------------------------------------------------------- refused

@pytest.mark.parametrize("call", [
    dict(n=768, n_a=158, n_b=466, kappa="0.29"),
    dict(n=113, n_a=39, n_b=83, discordant=44),        # nothing printed to parse
])
def test_an_unknown_convention_is_refused(call):
    with pytest.raises(InvalidInput, match="convention"):
        recover(**call, convention="half_even")


def test_an_unknown_convention_is_refused_by_the_interval_arithmetic():
    with pytest.raises(InvalidInput, match="convention"):
        exact_interval("0.29", convention="half_even")
    with pytest.raises(InvalidInput, match="convention"):
        rounding_interval("0.29", convention="banker")
