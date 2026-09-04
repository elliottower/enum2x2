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
from enum2x2 import (INFEASIBLE, INSUFFICIENT, SET, UNIQUE, Enum2x2Error,
                     InvalidInput, Table, recover, recover_many)

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


def test_giving_both_a_count_and_a_percentage_for_one_side_is_reported():
    r = recover(768, n_a=158, p_a="20.6", n_b=466, kappa="0.29",
                marginals_as_percent=True)
    assert r.status == INSUFFICIENT and "exactly one" in r.reason


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
    assert [r.status for r in out] == [UNIQUE, INSUFFICIENT, UNIQUE]
    assert "outside" in out[1].reason


def test_a_batch_returns_one_result_per_row_in_order():
    rows = [DELIRIUM] * 3
    assert len(recover_many(rows)) == 3


def test_the_status_is_always_one_of_the_four():
    out = recover_many([DELIRIUM,
                        dict(n=768, n_a=158, kappa="0.29"),
                        dict(n=768, n_a=158, n_b=466, kappa="0.95"),
                        dict(n=20306, n_a=866, n_b=1603, kappa="0.22")])
    assert {r.status for r in out} <= {UNIQUE, SET, INFEASIBLE, INSUFFICIENT}


# ------------------------------------------------------------------- repr

@pytest.mark.parametrize("call,expected", [
    (DELIRIUM, "unique"),
    (dict(n=20306, n_a=866, n_b=1603, kappa="0.22"), "11 tables"),
    (dict(n=768, n_a=158, n_b=466, kappa="0.95"), "infeasible"),
    (dict(n=768, n_a=158, kappa="0.29"), "insufficient"),
])
def test_the_repr_says_what_happened(call, expected):
    assert expected in repr(recover(**call))
