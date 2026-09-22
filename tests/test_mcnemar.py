"""McNemar and the discordant total as closing statistics.

A 2x2 with N fixed has three degrees of freedom and the two marginals use two,
so one further quantity closes it. kappa and observed agreement were already
accepted; these are the other two a paired-criteria paper is likely to print.

The mathematics being checked: McNemar depends only on the two discordant
cells, and the marginals already fix their difference, so the statistic fixes
their sum and the table follows.
"""
from __future__ import annotations

import pathlib
import random
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from enum2x2 import INSUFFICIENT, SET, UNIQUE, InvalidInput, recover
from enum2x2._core import mcnemar_chisq, mcnemar_exact_p, mcnemar_p


def tables(k, n_max=400):
    out = []
    while len(out) < k:
        n = random.randint(8, n_max)
        cut = sorted(random.sample(range(n + 1), 3))
        cells = (cut[0], cut[1] - cut[0], cut[2] - cut[1], n - cut[2])
        if sum(cells) == n:
            out.append(cells)
    return out


# ------------------------------------------------------- the statistic itself

def test_exact_p_is_a_fraction_and_never_exceeds_one():
    for n10, n01 in [(0, 0), (1, 0), (44, 0), (5, 5), (30, 12), (1, 200)]:
        p = mcnemar_exact_p(n10, n01)
        assert isinstance(p, Fraction)
        assert 0 < p <= 1


def test_exact_p_is_symmetric_in_the_two_discordant_cells():
    for _, n10, n01, _ in tables(200):
        assert mcnemar_exact_p(n10, n01) == mcnemar_exact_p(n01, n10)


def test_exact_p_falls_as_the_split_becomes_more_lopsided():
    m = 40
    ps = [mcnemar_exact_p(m - c, c) for c in range(0, m // 2 + 1)]
    assert ps == sorted(ps)


def test_chisquare_matches_its_definition():
    for _, n10, n01, _ in tables(200):
        if n10 + n01 == 0:
            continue
        assert mcnemar_chisq(n10, n01) == Fraction((n10 - n01) ** 2, n10 + n01)


def test_chisquare_is_undefined_without_discordant_pairs():
    from enum2x2._core import UndefinedStatistic
    with pytest.raises(UndefinedStatistic):
        mcnemar_chisq(0, 0)


def test_no_discordant_pairs_gives_a_p_of_one():
    assert mcnemar_exact_p(0, 0) == 1
    assert mcnemar_p(0, 0, "chisq") == 1.0


# ------------------------------------------------------------- as an input

def test_the_discordant_total_alone_identifies_the_table():
    for cells in tables(300):
        n11, n10, n01, n00 = cells
        n = sum(cells)
        r = recover(n, n_a=n11 + n10, n_b=n11 + n01, discordant=n10 + n01)
        assert r.status == UNIQUE
        assert (r.table.n11, r.table.n10, r.table.n01, r.table.n00) == cells


def test_a_tables_own_exact_p_recovers_it_or_a_set_containing_it():
    kept = 0
    for cells in tables(300, n_max=120):
        n11, n10, n01, n00 = cells
        if n10 + n01 == 0:
            continue
        n = sum(cells)
        printed = f"{float(mcnemar_exact_p(n10, n01)):.4f}"
        if printed == "0.0000":
            continue
        r = recover(n, n_a=n11 + n10, n_b=n11 + n01, mcnemar=printed)
        assert r.status in (UNIQUE, SET)
        assert cells in [(t.n11, t.n10, t.n01, t.n00) for t in r]
        kept += 1
    assert kept > 100


def test_a_printed_bound_keeps_every_table_whose_p_clears_it():
    r = recover(113, n_a=39, n_b=83, mcnemar="<0.001")
    assert r.status in (UNIQUE, SET)
    for t in r:
        assert mcnemar_exact_p(t.n10, t.n01) < Fraction(1, 1000)
    assert (39, 0, 44, 30) in [(t.n11, t.n10, t.n01, t.n00) for t in r]


def test_a_tighter_bound_never_admits_more_tables():
    loose = recover(215, n_a=181, n_b=201, mcnemar="<0.01")
    tight = recover(215, n_a=181, n_b=201, mcnemar="<0.0001")
    assert len(tight) <= len(loose)
    assert set(tight.tables) <= set(loose.tables)


def test_observed_agreement_alone_now_closes_the_table():
    r = recover(768, n_a=158, n_b=466, agreement="0.60")
    assert r.status in (UNIQUE, SET)
    assert (158, 0, 308, 302) in [(t.n11, t.n10, t.n01, t.n00) for t in r]


def test_no_closing_statistic_is_insufficient_and_names_the_options():
    r = recover(768, n_a=158, n_b=466)
    assert r.status == INSUFFICIENT
    for name in ("kappa", "agreement", "mcnemar", "discordant"):
        assert name in r.reason


def test_two_closing_statistics_agree_or_narrow():
    for cells in tables(120, n_max=150):
        n11, n10, n01, n00 = cells
        if n10 + n01 == 0:
            continue
        n = sum(cells)
        a, b = n11 + n10, n11 + n01
        one = recover(n, n_a=a, n_b=b, discordant=n10 + n01)
        both = recover(n, n_a=a, n_b=b, discordant=n10 + n01,
                       mcnemar=f"{float(mcnemar_exact_p(n10, n01)):.4f}")
        assert set(both.tables) <= set(one.tables)


# ---------------------------------------------------------------- refusals

def test_an_unknown_test_variant_is_refused():
    with pytest.raises(InvalidInput, match="mcnemar_test"):
        recover(100, n_a=50, n_b=50, mcnemar="<0.05", mcnemar_test="fisher")


def test_a_discordant_count_above_the_sample_is_refused():
    with pytest.raises(InvalidInput, match="outside"):
        recover(100, n_a=50, n_b=50, discordant=101)


def test_a_float_mcnemar_is_refused_like_a_float_kappa():
    with pytest.raises(InvalidInput, match="string"):
        recover(100, n_a=50, n_b=50, mcnemar=0.05)


def test_the_published_record_carries_the_variant():
    r = recover(215, n_a=181, n_b=201, mcnemar="<0.0001", mcnemar_test="chisq")
    assert r.published["mcnemar_test"] == "chisq"
    assert r.published["mcnemar"] == "<0.0001"


# ------------------------------------------------- the other agreement statistics

from enum2x2._core import CLOSING_STATISTICS, UndefinedStatistic


@pytest.mark.parametrize("name", sorted(set(CLOSING_STATISTICS) - {"prevalence_index", "bias_index"}))
def test_each_statistic_recovers_the_table_that_produced_it(name):
    fn = CLOSING_STATISTICS[name][0]
    checked = 0
    for cells in tables(120, n_max=200):
        try:
            value = fn(*cells)
        except UndefinedStatistic:
            continue
        printed = f"{float(value):.4f}"
        r = recover(sum(cells), n_a=cells[0] + cells[1], n_b=cells[0] + cells[2],
                    **{name: printed})
        assert r.status in (UNIQUE, SET), (name, cells, printed, r.reason)
        assert cells in [(t.n11, t.n10, t.n01, t.n00) for t in r], (name, cells, printed)
        checked += 1
    assert checked > 40, f"{name}: too few defined cases to be a real check"


@pytest.mark.parametrize("name", sorted(CLOSING_STATISTICS))
def test_every_statistic_is_exact_rational(name):
    fn = CLOSING_STATISTICS[name][0]
    for cells in tables(60):
        try:
            assert isinstance(fn(*cells), Fraction)
        except UndefinedStatistic:
            continue


def test_bias_index_is_fixed_by_the_marginals_so_closes_nothing():
    # n10 - n01 = n_a - n_b, so every candidate table shares it and it cannot narrow.
    from enum2x2._core import bias_index
    n, a, b = 200, 60, 90
    seen = {bias_index(n11, a - n11, b - n11, n - a - b + n11)
            for n11 in range(max(0, a + b - n), min(a, b) + 1)}
    assert len(seen) == 1


def test_an_unknown_statistic_name_is_refused_and_lists_the_known_ones():
    with pytest.raises(InvalidInput, match="unknown statistic"):
        recover(100, n_a=50, n_b=50, banana="0.5")


# --------------------------------------------------------------- mid-p variant

from enum2x2._core import mcnemar_midp


def test_midp_is_never_larger_than_the_exact_p():
    for _, n10, n01, _ in tables(300, n_max=150):
        assert mcnemar_midp(n10, n01) <= mcnemar_exact_p(n10, n01)


def test_midp_subtracts_the_point_probability():
    from math import comb
    for _, n10, n01, _ in tables(200, n_max=120):
        m = n10 + n01
        if m == 0 or n10 == n01:
            continue
        point = Fraction(comb(m, min(n10, n01)), 2 ** m)
        assert mcnemar_midp(n10, n01) == mcnemar_exact_p(n10, n01) - point


def test_midp_uses_its_own_form_when_the_discordant_cells_are_equal():
    from math import comb
    for k in (1, 3, 8, 20):
        point = Fraction(comb(2 * k, k), 2 ** (2 * k))
        assert mcnemar_midp(k, k) == 1 - point / 2


def test_midp_is_accepted_as_a_variant_and_can_change_the_recovered_set():
    r = recover(215, n_a=181, n_b=201, mcnemar="<0.0001", mcnemar_test="midp")
    assert r.status in (UNIQUE, SET)
    for t in r:
        assert mcnemar_midp(t.n10, t.n01) < Fraction(1, 10000)


def test_neither_byrt_index_closes_the_table():
    # Both reduce to functions of the marginals: (nA - nB)/N and (nA + nB - N)/N.
    from enum2x2._core import prevalence_index, bias_index, MARGINAL_DETERMINED
    from fractions import Fraction
    assert MARGINAL_DETERMINED == {"prevalence_index", "bias_index"}
    for cells in tables(300):
        n11, n10, n01, n00 = cells
        n, a, b = sum(cells), n11 + n10, n11 + n01
        assert bias_index(*cells) == Fraction(a - b, n)
        assert prevalence_index(*cells) == Fraction(a + b - n, n)


@pytest.mark.parametrize("name", ["prevalence_index", "bias_index"])
def test_a_marginal_determined_index_alone_is_insufficient(name):
    r = recover(200, n_a=60, n_b=90, **{name: "0.10"})
    assert r.status == INSUFFICIENT
    assert "closing statistic" in r.reason
