"""The public surface: what a caller touches, and how it fails.

The mathematics is covered by tests/test_recover_tables.py, which checks the
enumeration exhaustively and against an independent reimplementation. What follows
checks the API around it — that structure errors are raised, that source defects
are reported rather than raised, and that a batch survives a bad row.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from enum2x2 import (IMPOSSIBLE, INFEASIBLE, INSUFFICIENT, SET, UNIQUE,
                     Enum2x2Error, InvalidInput, Table, recover, recover_many)

DELIRIUM = dict(n=768, n_a=158, n_b=466, kappa="0.29")


# ------------------------------------------------------------------ raised
# A figure that cannot describe any table is a defect in the call.

def test_a_marginal_above_the_sample_is_refused():
    with pytest.raises(InvalidInput, match="outside"):
        recover(100, n_a=101, n_b=50, kappa="0.5")


def test_a_negative_marginal_is_refused():
    with pytest.raises(InvalidInput, match="outside"):
        recover(100, n_a=-1, n_b=50, kappa="0.5")


def test_a_kappa_beyond_one_is_refused():
    with pytest.raises(InvalidInput, match=r"\[-1, 1\]"):
        recover(100, n_a=50, n_b=50, kappa="1.4")


def test_a_nonpositive_sample_is_refused():
    with pytest.raises(InvalidInput, match="positive integer"):
        recover(0, n_a=0, n_b=0, kappa="0.5")


def test_a_float_where_a_printed_string_belongs_is_refused():
    # 0.10 and 0.1 are the same float and imply different intervals, so the
    # distinction cannot be recovered after coercion.
    with pytest.raises(InvalidInput, match="printed"):
        recover(768, n_a=158, n_b=466, kappa=0.29)


# ------------------------------------------------------------- not raised
# A source that reported too little, or reported figures that do not cohere, is
# described rather than treated as a programming error.

def test_a_missing_kappa_is_reported_not_raised():
    r = recover(768, n_a=158, n_b=466)
    assert r.status == INSUFFICIENT and "kappa" in r.reason


def test_a_missing_marginal_is_reported_not_raised():
    r = recover(768, n_a=158, kappa="0.29")
    assert r.status == INSUFFICIENT and "n_b" in r.reason


def test_giving_both_a_count_and_a_percentage_for_one_side_is_refused():
    # Two marginals for one criterion is a defect in the call, not a property of
    # the source, so it raises rather than being reported as under-reporting.
    with pytest.raises(InvalidInput, match="not both"):
        recover(768, n_a=158, p_a="20.6", n_b=466, kappa="0.29",
                marginals_as_percent=True)


def test_a_printed_marginal_outside_the_unit_interval_is_refused():
    with pytest.raises(InvalidInput, match=r"outside \[0, 1\]"):
        recover(100, p_a="150", p_b="50", kappa="0.5", marginals_as_percent=True)


def test_figures_that_admit_no_table_are_reported_with_the_figure_that_excludes():
    r = recover(370, n_a=165, n_b=160, kappa="0.48",
                agreement="73", agreement_as_percent=True)
    assert r.status == INFEASIBLE
    assert "agreement" in r.reason
    assert not r


def test_a_kappa_the_marginals_cannot_reach_names_the_range():
    r = recover(768, n_a=158, n_b=466, kappa="0.95")
    assert r.status == INFEASIBLE and "range these marginals permit" in r.reason


# ---------------------------------------------------------------- results

def test_a_determined_report_returns_one_table():
    r = recover(**DELIRIUM)
    assert r.status == UNIQUE and len(r) == 1
    assert r.table == Table(158, 0, 308, 302)


def test_an_underdetermined_report_returns_the_set_and_its_ranges():
    r = recover(20306, n_a=866, n_b=1603, kappa="0.22")
    assert r.status == SET and len(r) == 11
    assert r.cell_ranges["n11"] == (320, 330)
    assert all(t.n == 20306 for t in r)


def test_asking_a_set_for_the_table_says_so_rather_than_guessing():
    r = recover(20306, n_a=866, n_b=1603, kappa="0.22")
    with pytest.raises(Enum2x2Error, match="does not determine one table"):
        _ = r.table


def test_every_returned_table_reproduces_the_figures_it_was_recovered_from():
    for r in (recover(**DELIRIUM),
              recover(20306, n_a=866, n_b=1603, kappa="0.22"),
              recover(7328, n_a=174, n_b=175, kappa="0.668")):
        for t in r:
            assert round(t.kappa, len(r.published["kappa"].split(".")[1])) == \
                   float(r.published["kappa"])


def test_a_recovery_is_iterable_indexable_and_sized():
    r = recover(20306, n_a=866, n_b=1603, kappa="0.22")
    assert len(list(r)) == len(r) == 11
    assert r[0] in list(r)
    assert bool(r) is True
    assert bool(recover(370, n_a=165, n_b=160, kappa="0.48",
                        agreement="73", agreement_as_percent=True)) is False


def test_asymmetry_is_one_when_the_disagreement_runs_entirely_one_way():
    assert recover(**DELIRIUM).table.asymmetry == 1.0


def test_asymmetry_is_none_when_the_criteria_never_disagree():
    assert Table(10, 0, 0, 90).asymmetry is None


def test_percentage_marginals_agree_with_the_counts_they_stand_for():
    by_count = recover(768, n_a=510, n_b=158, kappa="0.22")
    by_pct = recover(768, p_a="66.4", p_b="20.6", kappa="0.22",
                     marginals_as_percent=True)
    assert [t.as_dict() for t in by_count] == [t.as_dict() for t in by_pct]


# ------------------------------------------------------------------ batch

def test_one_bad_row_does_not_stop_the_others():
    out = recover_many([DELIRIUM,
                        dict(n=100, n_a=101, n_b=50, kappa="0.5"),   # impossible
                        dict(n=7328, n_a=174, n_b=175, kappa="0.668")])
    assert [r.status for r in out] == [UNIQUE, IMPOSSIBLE, UNIQUE]
    assert "outside" in out[1].reason


def test_a_batch_survives_a_column_the_function_does_not_take():
    # A spreadsheet of published comparisons carries a label column.
    out = recover_many([dict(study="Meagher 2014", **DELIRIUM)])
    assert out[0].status == UNIQUE


def test_a_batch_survives_a_cell_that_is_not_a_number():
    # A cell that cannot be read is not the same as one the source left empty:
    # the first is a figure this code cannot use, the second is a figure the
    # source never published, and counting them together would misreport how much
    # of the literature under-reports.
    out = recover_many([DELIRIUM, dict(n=100, n_a=50, n_b=50, kappa="NA"), DELIRIUM])
    assert [r.status for r in out] == [UNIQUE, IMPOSSIBLE, UNIQUE]
    assert "not a decimal number" in out[1].reason


def test_an_impossible_figure_is_not_counted_as_an_under_reporting_source():
    # Counting these as 'insufficient' would inflate how many sources under-reported.
    out = recover_many([dict(n=370, n_a=500, n_b=160, kappa="0.48"),
                        dict(n=768, n_a=158, kappa="0.29")])
    assert [r.status for r in out] == [IMPOSSIBLE, INSUFFICIENT]


def test_a_batch_returns_one_result_per_row_in_order():
    rows = [DELIRIUM] * 3
    assert len(recover_many(rows)) == 3


def test_the_status_is_always_one_of_the_four():
    out = recover_many([DELIRIUM,
                        dict(n=768, n_a=158, kappa="0.29"),
                        dict(n=768, n_a=158, n_b=466, kappa="0.95"),
                        dict(n=20306, n_a=866, n_b=1603, kappa="0.22")])
    assert {r.status for r in out} <= {UNIQUE, SET, INFEASIBLE, INSUFFICIENT, IMPOSSIBLE}


# ------------------------------------------------------------------- repr

@pytest.mark.parametrize("call,expected", [
    (DELIRIUM, "unique"),
    (dict(n=20306, n_a=866, n_b=1603, kappa="0.22"), "11 tables"),
    (dict(n=768, n_a=158, n_b=466, kappa="0.95"), "infeasible"),
    (dict(n=768, n_a=158, kappa="0.29"), "insufficient"),
])
def test_the_repr_says_what_happened(call, expected):
    assert expected in repr(recover(**call))


# --------------------------------------------------------- rounding boundaries
#
# The exhaustive sweeps run at N <= 24, where the granularity of kappa and of the
# marginals is far coarser than the interval arithmetic being tested, so neither
# of these is reachable there. Both are stated as concrete cases instead.

def test_a_statistic_exactly_on_the_upper_endpoint_is_admitted():
    # The table (2, 0, 2, 20) at N = 24 has kappa exactly 0.625, which a source
    # prints as "0.62" under round-half-even and "0.63" under round-half-up. The
    # interval is closed at both ends because the convention is not stated, so the
    # table survives either printing. A strict inequality loses it under both.
    from enum2x2 import kappa_from_cells, rounds_to
    k = kappa_from_cells(2, 0, 2, 20)
    assert k == 0.625
    assert rounds_to(k, "0.62")
    assert rounds_to(k, "0.63")
    assert recover(24, n_a=2, n_b=4, kappa="0.62").table == Table(2, 0, 2, 20)
    assert recover(24, n_a=2, n_b=4, kappa="0.63").table == Table(2, 0, 2, 20)


def test_the_top_of_a_marginal_interval_is_not_truncated_away():
    # counts_rounding_to derives its upper bound with int(), which truncates. At
    # N = 240 a marginal printed "0.512" admits exactly one count, 123, and
    # int(0.5125 * 240) is 122 -- so without the +1 the only valid count is lost
    # and the row wrongly reports that no table exists.
    from enum2x2._core import counts_rounding_to
    assert counts_rounding_to("0.512", 240) == [123]
    assert counts_rounding_to("0.14", 200) == [27, 28, 29]
    assert 63 in counts_rounding_to("0.3", 180)


def test_a_marginal_whose_top_count_would_be_truncated_still_recovers():
    r = recover(240, p_a="0.512", n_b=100, kappa="0.18")
    assert r.status in (UNIQUE, SET)
    assert all(t.n11 + t.n10 == 123 for t in r)


# ------------------------------------------------------------- exact filtering
#
# Membership is decided on rationals. Both sides are exact -- a decimal string and
# a ratio of integers -- so there is no tolerance to choose, and a value outside
# the interval is outside it however small the margin.

def test_membership_admits_nothing_outside_the_declared_interval():
    from fractions import Fraction
    from enum2x2 import exact_interval, exactly_rounds_to
    lo, hi = exact_interval("0.000000000000")
    assert (lo, hi) == (Fraction(-5, 10**13), Fraction(5, 10**13))
    assert exactly_rounds_to(hi, "0.000000000000")           # closed at the end
    assert not exactly_rounds_to(hi + Fraction(1, 10**20), "0.000000000000")
    assert not exactly_rounds_to(Fraction(1, 10**12), "0.000000000000")


def test_the_exact_kappa_is_the_float_kappa_to_within_representation():
    from enum2x2 import exact_kappa, kappa_from_cells
    for cells in ((155, 355, 3, 255), (158, 0, 308, 302), (326, 540, 1277, 18163)):
        assert abs(float(exact_kappa(*cells)) - kappa_from_cells(*cells)) < 1e-12


def test_a_kappa_undefined_for_the_table_is_named_as_such():
    from enum2x2 import UndefinedStatistic, exact_kappa
    with pytest.raises(UndefinedStatistic):
        exact_kappa(100, 0, 0, 0)


def test_a_boolean_is_not_accepted_where_an_integer_is_required():
    with pytest.raises(InvalidInput, match="positive integer"):
        recover(True, n_a=1, n_b=1, kappa="0.5")
    with pytest.raises(InvalidInput, match="integer count"):
        recover(100, n_a=True, n_b=50, kappa="0.5")


@pytest.mark.parametrize("bad", ["abc", "", "1e400"])
def test_a_figure_that_is_not_a_decimal_number_is_refused(bad):
    with pytest.raises(InvalidInput, match="not a decimal number|outside"):
        recover(100, n_a=50, n_b=50, kappa=bad)


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "Infinity"])
def test_a_figure_that_is_not_finite_is_refused(bad):
    # Decimal accepts these, so the decimal parse alone does not catch them.
    with pytest.raises(InvalidInput, match="not a finite number"):
        recover(100, n_a=50, n_b=50, kappa=bad)
