"""Tests for the table recovery.

The exhaustive test is the one that matters: for every integer table up to a
small N, print what a paper would print, enumerate from that alone, and require
the original table to be among the survivors. It establishes correctness over a
finite state space rather than over samples.
"""
from __future__ import annotations

import itertools
import pathlib
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from recover_tables import (RecoveryError, enumerate_tables, expected_agreement,
                            analyse, ineligibility, kappa_min, marginal_counts,
                            kappa_from_cells, kappa_max, rounding_interval,
                            rounds_to)


def _printed(x: float, dp: int) -> str:
    return f"{x:.{dp}f}"


def _row(n11, n10, n01, n00, dp_marg=4, dp_kappa=2, p_o=None):
    """What a paper reporting this table would print."""
    n = n11 + n10 + n01 + n00
    row = {"N": n,
           "p_A": _printed((n11 + n10) / n, dp_marg),
           "p_B": _printed((n11 + n01) / n, dp_marg),
           "kappa": _printed(kappa_from_cells(n11, n10, n01, n00), dp_kappa),
           "marginals_as_percent": False}
    if p_o is not None:
        row["p_o"] = p_o
    return row


# ---------------------------------------------------------------- intervals

def test_printed_digits_fix_the_interval_not_the_float_value():
    assert rounding_interval("0.1") == pytest.approx((0.05, 0.15))
    assert rounding_interval("0.10") == pytest.approx((0.095, 0.105))
    assert rounding_interval("0.100") == pytest.approx((0.0995, 0.1005))


def test_percent_intervals_are_scaled_not_reinterpreted():
    lo, hi = rounding_interval("4.26", as_percent=True)
    assert (lo, hi) == pytest.approx((0.04255, 0.04265))
    assert rounds_to(866 / 20306, "4.26", as_percent=True)


def test_boundary_values_are_admitted_under_either_convention():
    # 0.105 rounds to 0.10 under half-even and 0.11 under half-up; the source does
    # not say which, so both ends are admitted rather than one being guessed.
    assert rounds_to(0.105, "0.10")
    assert rounds_to(0.105, "0.11")
    assert not rounds_to(0.12, "0.10")


# ---------------------------------------------------------------- exhaustive

@pytest.mark.parametrize("n", [12, 17, 24])
def test_every_table_of_size_n_is_in_its_own_candidate_set(n):
    checked = 0
    for n11, n10, n01 in itertools.product(range(n + 1), repeat=3):
        n00 = n - n11 - n10 - n01
        if n00 < 0:
            continue
        p_a, p_b = (n11 + n10) / n, (n11 + n01) / n
        if p_a in (0.0, 1.0) or p_b in (0.0, 1.0):
            continue                      # kappa undefined at a degenerate margin
        if abs(1.0 - expected_agreement(p_a, p_b)) < 1e-12:
            continue
        cells = {"n11": n11, "n10": n10, "n01": n01, "n00": n00}
        found = enumerate_tables(dict(_row(n11, n10, n01, n00),
                                      condition="", criteria="", crossing="",
                                      source_artifact="", quote=""))
        assert any(t["cells"] == cells for t in found), cells
        checked += 1
    assert checked > 100


def test_coarse_reporting_leaves_a_set_and_fine_reporting_narrows_it():
    cells = (40, 15, 10, 135)
    coarse = enumerate_tables(_row(*cells, dp_marg=2, dp_kappa=1))
    fine = enumerate_tables(_row(*cells, dp_marg=6, dp_kappa=6))
    assert len(coarse) > len(fine)
    assert len(fine) >= 1


def test_an_extra_published_statistic_narrows_the_set():
    cells = (40, 15, 10, 135)
    without = enumerate_tables(_row(*cells, dp_marg=2, dp_kappa=1))
    n = sum(cells)
    p_o = f"{(cells[0] + cells[3]) / n:.4f}"
    with_po = enumerate_tables(_row(*cells, dp_marg=2, dp_kappa=1, p_o=p_o))
    assert len(with_po) <= len(without)
    assert len(with_po) >= 1


def test_mutually_inconsistent_figures_yield_no_table():
    # marginals 2% and 90% cannot support kappa 0.99
    row = {"N": 1000, "p_A": "0.0200", "p_B": "0.9000", "kappa": "0.99",
           "marginals_as_percent": False}
    assert enumerate_tables(row) == []


# ---------------------------------------------------------------- invariants

def test_swapping_the_two_criteria_swaps_the_directional_discordances():
    n11, n10, n01, n00 = 100, 90, 10, 800
    fwd = enumerate_tables(_row(n11, n10, n01, n00, dp_marg=6, dp_kappa=6))
    rev = enumerate_tables(_row(n11, n01, n10, n00, dp_marg=6, dp_kappa=6))
    assert fwd[0]["d_A_pos_B_neg"] == pytest.approx(rev[0]["d_A_neg_B_pos"])
    assert fwd[0]["p_o"] == pytest.approx(rev[0]["p_o"])


def test_reversing_both_labels_preserves_kappa():
    a = kappa_from_cells(100, 90, 10, 800)
    b = kappa_from_cells(800, 10, 90, 100)      # positives and negatives exchanged
    assert a == pytest.approx(b)


def test_kappa_max_is_one_exactly_when_the_marginals_agree():
    assert kappa_max(0.3, 0.3) == pytest.approx(1.0)
    assert kappa_max(0.0426, 0.0789) < 1.0
    assert kappa_max(0.5, 0.5) == pytest.approx(1.0)


def test_kappa_max_matches_the_closed_form():
    for p_a, p_b in [(0.0426, 0.0789), (0.011, 0.017), (0.446, 0.432), (0.7, 0.2)]:
        p_e = expected_agreement(p_a, p_b)
        assert kappa_max(p_a, p_b) == pytest.approx(
            ((1 - abs(p_a - p_b)) - p_e) / (1 - p_e))


def test_a_degenerate_margin_is_refused_not_returned():
    with pytest.raises(RecoveryError):
        kappa_from_cells(0, 0, 0, 0)
    with pytest.raises(RecoveryError):
        kappa_from_cells(100, 0, 0, 0)          # p_e is 1; kappa undefined


def test_every_candidate_table_sums_to_the_sample_and_is_non_negative():
    for t in enumerate_tables(_row(40, 15, 10, 135, dp_marg=2, dp_kappa=1)):
        c = t["cells"]
        assert sum(c.values()) == 200
        assert min(c.values()) >= 0


# ------------------------------------------------- completeness and feasibility

def _all_tables(n):
    for n11, n10, n01 in itertools.product(range(n + 1), repeat=3):
        n00 = n - n11 - n10 - n01
        if n00 >= 0:
            yield n11, n10, n01, n00


@pytest.mark.parametrize("n,dp_marg,dp_kappa", [(18, 2, 1), (22, 3, 2)])
def test_the_candidate_set_is_exactly_the_compatible_set(n, dp_marg, dp_kappa):
    """Soundness and completeness: nothing compatible is dropped, nothing else kept.

    Brute force every table of size n, keep those whose printed summaries match the
    row's, and require that set to equal what the enumerator returns. A test that
    only checks the true table survives cannot catch over-exclusion of its rivals.
    """
    everything = list(_all_tables(n))
    seen = 0
    for cells in everything:
        n11, n10, n01, n00 = cells
        p_a, p_b = (n11 + n10) / n, (n11 + n01) / n
        if p_a in (0.0, 1.0) or p_b in (0.0, 1.0):
            continue
        if abs(1.0 - expected_agreement(p_a, p_b)) < 1e-12:
            continue
        row = _row(*cells, dp_marg=dp_marg, dp_kappa=dp_kappa)
        brute = {c for c in everything
                 if c[0] + c[1] > 0 and c[0] + c[2] > 0
                 and c[2] + c[3] > 0 and c[1] + c[3] > 0
                 and rounds_to((c[0] + c[1]) / n, row["p_A"])
                 and rounds_to((c[0] + c[2]) / n, row["p_B"])
                 and rounds_to(kappa_from_cells(*c), row["kappa"])}
        got = {(t["cells"]["n11"], t["cells"]["n10"],
                t["cells"]["n01"], t["cells"]["n00"])
               for t in enumerate_tables(row)}
        assert got == brute, (cells, sorted(brute - got), sorted(got - brute))
        seen += 1
    assert seen == sum(1 for c in everything
                       if 0 < c[0] + c[1] < n and 0 < c[0] + c[2] < n)


def test_kappa_min_is_the_floor_the_marginals_impose():
    for p_a, p_b in [(0.3, 0.3), (0.0426, 0.0789), (0.7, 0.2), (0.9, 0.9)]:
        k_lo, k_hi = kappa_min(p_a, p_b), kappa_max(p_a, p_b)
        assert k_lo <= 0.0 <= k_hi
        assert k_lo < k_hi


def test_kappa_min_matches_a_table_built_to_minimise_agreement():
    n, p_a, p_b = 1000, 0.3, 0.4
    n_a, n_b = int(p_a * n), int(p_b * n)
    n11 = max(0, n_a + n_b - n)                     # as little overlap as possible
    k = kappa_from_cells(n11, n_a - n11, n_b - n11, n - n_a - n_b + n11)
    assert k == pytest.approx(kappa_min(p_a, p_b), abs=1e-9)


def test_unequal_marginals_with_kappa_one_is_infeasible():
    row = {"N": 1000, "p_A": "0.200", "p_B": "0.400", "kappa": "1.00",
           "marginals_as_percent": False}
    assert enumerate_tables(row) == []


def test_a_kappa_just_inside_the_feasible_range_survives():
    p_a, p_b = 0.200, 0.400
    k = kappa_max(p_a, p_b)
    row = {"N": 1000, "p_A": "0.200", "p_B": "0.400",
           "kappa": f"{k:.2f}", "marginals_as_percent": False}
    assert enumerate_tables(row)


def test_large_n_enumerates_without_blowing_up():
    row = {"N": 20306, "p_A": "4.26", "p_B": "7.89", "kappa": "0.22",
           "marginals_as_percent": True}
    tables = enumerate_tables(row)
    assert tables
    assert all(sum(t["cells"].values()) == 20306 for t in tables)


# ------------------------------------------------------- exact-count marginals

def test_an_exact_count_marginal_is_used_verbatim():
    assert marginal_counts({"N": 7328, "n_A": 153}, "A", 7328) == [153]


def test_an_exact_count_outside_the_sample_is_refused():
    with pytest.raises(RecoveryError):
        marginal_counts({"N": 100, "n_A": 101}, "A", 100)


def test_a_printed_count_identifies_what_a_printed_percentage_leaves_open():
    n11, n10, n01, n00 = 125, 28, 49, 7126
    n = n11 + n10 + n01 + n00
    kappa = _printed(kappa_from_cells(n11, n10, n01, n00), 3)

    as_percent = {"N": n, "p_A": "2.1", "p_B": "2.4", "kappa": kappa,
                  "marginals_as_percent": True}
    as_counts = {"N": n, "n_A": n11 + n10, "n_B": n11 + n01, "kappa": kappa}

    loose, tight = enumerate_tables(as_percent), enumerate_tables(as_counts)
    truth = {"n11": n11, "n10": n10, "n01": n01, "n00": n00}

    assert truth in [t["cells"] for t in loose]
    assert [t["cells"] for t in tight] == [truth]
    assert len(tight) < len(loose)


def test_exact_counts_and_percentages_agree_where_the_percentage_pins_one_count():
    n11, n10, n01, n00 = 155, 355, 3, 255
    n = n11 + n10 + n01 + n00
    kappa = _printed(kappa_from_cells(n11, n10, n01, n00), 2)
    by_pct = enumerate_tables({"N": n, "p_A": "66.4", "p_B": "20.6", "kappa": kappa,
                               "marginals_as_percent": True})
    by_cnt = enumerate_tables({"N": n, "n_A": n11 + n10, "n_B": n11 + n01,
                               "kappa": kappa})
    assert [t["cells"] for t in by_cnt] == [t["cells"] for t in by_pct]


def test_a_row_giving_neither_count_nor_percentage_is_ineligible():
    row = {"N": 100, "kappa": "0.5", "kappa_variant": "unweighted Cohen",
           "denominator_status": "explicit_same", "n_A": 40}
    assert "n_B" in ineligibility(row)


def test_a_marginal_interval_reaching_zero_returns_tables_rather_than_raising():
    # A printed marginal of "0.0" admits a candidate pair whose expected agreement
    # is exactly 1, leaving kappa undefined for that pair alone. The row still has
    # compatible tables and must return them.
    row = {"N": 24, "p_A": "0.0", "p_B": "0.0", "kappa": "0.00",
           "marginals_as_percent": False}
    assert {(t["cells"]["n11"], t["cells"]["n10"], t["cells"]["n01"], t["cells"]["n00"])
            for t in enumerate_tables(row)} == {(0, 0, 1, 23), (0, 1, 0, 23)}


def test_an_infeasible_row_names_the_figure_that_excludes_rather_than_the_kappa():
    # Marginals and kappa alone admit a table; adding the published raw agreement
    # empties the set. The reported reason must not blame the kappa.
    n11, n10, n01, n00 = 115, 50, 45, 160
    n = n11 + n10 + n01 + n00
    row = {"N": n, "n_A": n11 + n10, "n_B": n11 + n01,
           "kappa": _printed(kappa_from_cells(n11, n10, n01, n00), 2),
           "p_o": "73", "p_o_as_percent": True,
           "kappa_variant": "unweighted Cohen", "denominator_status": "explicit_same",
           "condition": "x", "criteria": "x", "crossing": "x",
           "source_artifact": "x", "quote": "x"}
    assert enumerate_tables(row) == []
    assert enumerate_tables({k: v for k, v in row.items() if k != "p_o"})
    result = analyse("row", row)
    assert result["status"] == "infeasible"
    assert "p_o" in result["binding_constraints"]
    assert "no integer table attains it" not in result["reason"]


# ------------------------------------------------- independent reimplementation
#
# The sweep above shares kappa_from_cells and rounds_to with the module it checks,
# so it establishes internal consistency rather than correctness. What follows
# reimplements both from the definitions, in exact rational arithmetic, importing
# nothing from recover_tables. Agreement between the two is then evidence about
# the method rather than about one shared helper.

def _independent_interval(printed: str) -> tuple[Fraction, Fraction]:
    """Values that round to a decimal string, from its digits alone."""
    neg = printed.startswith("-")
    digits = printed.lstrip("-")
    whole, _, frac = digits.partition(".")
    scale = Fraction(10) ** len(frac)
    value = Fraction(int(whole + frac), scale)
    if neg:
        value = -value
    half = Fraction(1, 2) / scale
    return value - half, value + half


def _independent_kappa(n11, n10, n01, n00) -> Fraction:
    n = Fraction(n11 + n10 + n01 + n00)
    agree = Fraction(n11 + n00) / n
    row, col = Fraction(n11 + n10) / n, Fraction(n11 + n01) / n
    chance = row * col + (1 - row) * (1 - col)
    return (agree - chance) / (1 - chance)


def _independent_compatible(n, p_a_str, p_b_str, kappa_str):
    lo_a, hi_a = _independent_interval(p_a_str)
    lo_b, hi_b = _independent_interval(p_b_str)
    lo_k, hi_k = _independent_interval(kappa_str)
    out = set()
    for n11 in range(n + 1):
        for n10 in range(n - n11 + 1):
            for n01 in range(n - n11 - n10 + 1):
                n00 = n - n11 - n10 - n01
                row, col = Fraction(n11 + n10, n), Fraction(n11 + n01, n)
                if not (lo_a <= row <= hi_a and lo_b <= col <= hi_b):
                    continue
                if row * col + (1 - row) * (1 - col) == 1:
                    continue
                if lo_k <= _independent_kappa(n11, n10, n01, n00) <= hi_k:
                    out.add((n11, n10, n01, n00))
    return out


@pytest.mark.parametrize("n,dp_marg,dp_kappa", [(16, 2, 1), (20, 2, 2), (24, 3, 2)])
def test_a_reimplementation_from_the_definitions_returns_the_same_set(n, dp_marg, dp_kappa):
    checked = 0
    for cells in _all_tables(n):
        n11, n10, n01, n00 = cells
        p_a, p_b = (n11 + n10) / n, (n11 + n01) / n
        if p_a in (0.0, 1.0) or p_b in (0.0, 1.0):
            continue
        row = _row(*cells, dp_marg=dp_marg, dp_kappa=dp_kappa)
        mine = _independent_compatible(n, row["p_A"], row["p_B"], row["kappa"])
        theirs = {(t["cells"]["n11"], t["cells"]["n10"], t["cells"]["n01"], t["cells"]["n00"])
                  for t in enumerate_tables(row)}
        assert theirs == mine, (cells, sorted(mine - theirs), sorted(theirs - mine))
        assert cells in mine
        checked += 1
    assert checked > 0
