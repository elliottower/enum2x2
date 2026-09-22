"""Regressions for faults found in a review before the first public release."""
import csv
import itertools
import json
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

import pytest

from enum2x2 import (INFEASIBLE, UNIQUE, InvalidInput, recover, recover_many)
from enum2x2.__main__ import main as cli_main
from enum2x2._core import mcnemar_p


def test_infeasible_agreement_without_kappa_is_reported_not_raised():
    r = recover(20, n_a=10, n_b=10, agreement="0.95")
    assert r.status == INFEASIBLE
    assert "kappa" not in r.reason


def test_infeasible_discordant_without_kappa_is_reported_not_raised():
    r = recover(20, n_a=10, n_b=4, discordant=1)
    assert r.status == INFEASIBLE


def test_infeasible_reason_does_not_blame_agreement_when_another_figure_excludes():
    # kappa and agreement both describe 158/0/308/302; the discordant count is wrong.
    r = recover(768, n_a=158, n_b=466, kappa="0.29", agreement="60",
                agreement_as_percent=True, discordant=100)
    assert r.status == INFEASIBLE
    assert "agreement admits none" not in r.reason


def test_infeasible_reason_for_kappa_and_agreement_is_unchanged():
    r = recover(370, p_a="44.6", p_b="43.2", kappa="0.48", agreement="73",
                marginals_as_percent=True, agreement_as_percent=True)
    assert r.status == INFEASIBLE
    assert r.reason == ("the marginals and kappa admit 1 table(s); "
                        "adding the published agreement admits none")


def test_recover_many_accepts_every_statistic_recover_accepts():
    row = {"n": 768, "n_a": 158, "n_b": 466, "pabak": "0.20"}
    batch = recover_many([row])[0]
    single = recover(768, n_a=158, n_b=466, pabak="0.20")
    assert batch.status == single.status == UNIQUE
    assert batch.tables == single.tables


def test_recover_many_passes_phi():
    batch = recover_many([{"n": 100, "n_a": 50, "n_b": 50, "phi": "-0.60"}])[0]
    assert [t.as_dict() for t in batch] == [{"n11": 10, "n10": 40, "n01": 40, "n00": 10}]


def test_phi_keeps_its_sign():
    pos = recover(100, n_a=50, n_b=50, phi="0.60")
    neg = recover(100, n_a=50, n_b=50, phi="-0.60")
    assert [t.as_dict() for t in pos] == [{"n11": 40, "n10": 10, "n01": 10, "n00": 40}]
    assert [t.as_dict() for t in neg] == [{"n11": 10, "n10": 40, "n01": 40, "n00": 10}]


def _printed_phi(n11: int, n10: int, n01: int, n00: int, places: int) -> str | None:
    """phi rounded half-up to `places`, computed to 60 digits; None where undefined."""
    den = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    if den == 0:
        return None
    num = n11 * n00 - n10 * n01
    with localcontext() as ctx:
        ctx.prec = 60
        mag = (Decimal(num * num) / Decimal(den)).sqrt()
        value = mag if num >= 0 else -mag
        q = Decimal(1).scaleb(-places)
        # Round half away from zero on the magnitude, which is what printing does.
        out = abs(value).quantize(q, rounding=ROUND_HALF_UP)
        return str(-out if value < 0 and out != 0 else out)


@pytest.mark.parametrize("n", [7, 12, 18])
@pytest.mark.parametrize("places", [1, 2])
def test_phi_recovers_exactly_the_brute_force_set(n, places):
    tables = [t for t in itertools.product(range(n + 1), repeat=4) if sum(t) == n]
    for n_a in range(1, n):
        for n_b in range(1, n):
            by_print: dict[str, set] = {}
            for t in tables:
                if t[0] + t[1] != n_a or t[0] + t[2] != n_b:
                    continue
                printed = _printed_phi(*t, places)
                if printed is not None:
                    by_print.setdefault(printed, set()).add(t)
            for printed, expected in by_print.items():
                got = {(x.n11, x.n10, x.n01, x.n00)
                       for x in recover(n, n_a=n_a, n_b=n_b, phi=printed)}
                assert got == expected, (n, n_a, n_b, printed)


def test_mcnemar_continuity_leaves_a_symmetric_table_at_p_one():
    # R's mcnemar.test applies Yates's correction only when the discordant cells differ.
    assert mcnemar_p(5, 5, "chisq_cc") == 1.0
    assert mcnemar_p(6, 5, "chisq_cc") == 1.0
    assert mcnemar_p(10, 3, "chisq_cc") == pytest.approx(0.0961, abs=1e-4)


@pytest.mark.parametrize("bad", [{"pabak": "abc"}, {"phi": "x"}, {"mcnemar": "NS"},
                                 {"mcnemar": "<abc"}])
def test_malformed_printed_figures_raise_invalid_input(bad):
    with pytest.raises(InvalidInput):
        recover(20, n_a=10, n_b=10, **bad)


def test_cli_reads_discordant_as_a_count_and_rejects_fractional_counts(tmp_path):
    path = tmp_path / "rows.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["n", "n_a", "n_b", "discordant"])
        w.writeheader()
        w.writerow({"n": 768, "n_a": 158, "n_b": 466, "discordant": 308})
        w.writerow({"n": 768, "n_a": "158.7", "n_b": 466, "discordant": 308})
    out = tmp_path / "out.json"
    assert cli_main([str(path), "--out", str(out)]) == 0
    first, second = json.loads(out.read_text())
    assert first["status"] == UNIQUE
    assert first["table"] == {"n11": 158, "n10": 0, "n01": 308, "n00": 302}
    assert second["status"] == "impossible"
    assert "integer" in second["reason"]


def test_an_impossible_batch_row_can_be_printed():
    r = recover_many([{"n": 100, "n_a": 150, "n_b": 50, "kappa": "0.1"}])[0]
    assert r.status == "impossible"
    assert "impossible" in repr(r)


@pytest.mark.parametrize("bad", [{"agreement": "1.20"}, {"positive_agreement": "64"},
                                 {"odds_ratio": "-1.0"}, {"mcnemar": "1.5"},
                                 {"odds_ratio": "inf"}, {"prevalence_index": "1.50"}])
def test_a_figure_outside_its_range_raises_invalid_input(bad):
    with pytest.raises(InvalidInput):
        recover(100, n_a=40, n_b=50, **bad)


def test_percent_agreement_is_bounded_by_one_hundred_not_one():
    assert recover(768, n_a=158, n_b=466, agreement="60", agreement_as_percent=True)
    with pytest.raises(InvalidInput):
        recover(768, n_a=158, n_b=466, agreement="160", agreement_as_percent=True)


@pytest.mark.parametrize("printed", ["p<0.001", "P < 0.001", "p≤0.001", " <0.001 "])
def test_common_printed_forms_of_a_p_value_read_alike(printed):
    reference = recover(113, n_a=39, n_b=83, mcnemar="<0.001")
    assert recover(113, n_a=39, n_b=83, mcnemar=printed).tables == reference.tables


def test_p_equals_form_reads_as_a_point_value():
    assert (recover(113, n_a=39, n_b=83, mcnemar="p = 0.03").tables
            == recover(113, n_a=39, n_b=83, mcnemar="0.03").tables)


def test_specific_agreement_is_named_for_what_it_computes():
    r = recover(100, n_a=40, n_b=50, positive_agreement="0.67")
    assert all(abs(2 * t.n11 / (2 * t.n11 + t.n10 + t.n01) - 0.67) <= 0.005 for t in r)
    with pytest.raises(InvalidInput):
        recover(100, n_a=40, n_b=50, ppa="0.67")
