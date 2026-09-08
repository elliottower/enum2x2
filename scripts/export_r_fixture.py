"""Export this package's behaviour as a fixture the R port is checked against.

The R implementation in ../enum2x2-r must reproduce this one exactly, so the
Python package is used as the oracle: every case below is run through `recover`
and the outcome -- status, reason, and the surviving tables in the order they were
enumerated -- is written out. The R test suite reads the two files and asserts
equality; nothing in R regenerates them.

Cases come from three places. Every determinate case in tests/test_api.py and
tests/test_enumeration.py is listed by hand under `named_cases`. The exhaustive
sweeps those tests run are reproduced as `sweep_cases`, one case per integer table
at the sample sizes and printed precisions the sweeps use, so the R port is
checked over the same finite state space rather than over the examples alone.
Calls that raise are recorded with status 'error' and the message, because the
distinction between a defect in the call and a property of the source is part of
what the port has to reproduce.

Nothing here is random: the fixture is a function of the package, not of a seed.

    python3 scripts/export_r_fixture.py [outdir]

An absent figure is written as ABSENT rather than as an empty field, so that a
figure a source printed as an empty string stays distinguishable from one it
never printed at all.

Writes cases.csv.gz and tables.csv.gz.
"""
from __future__ import annotations

import csv
import gzip
import itertools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from enum2x2 import (Enum2x2Error, InvalidInput, expected_agreement,  # noqa: E402
                     kappa_from_cells, kappa_max, recover)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT.parent / "enum2x2-r" / "tests" / "testthat" / "fixtures"

CASE_FIELDS = ["id", "group", "n", "n_a", "n_b", "p_a", "p_b", "kappa",
               "agreement", "marginals_as_percent", "agreement_as_percent",
               "status", "ntables", "reason", "exception"]
TABLE_FIELDS = ["id", "k", "ai", "bi", "ci", "di"]
ABSENT = "<none>"


def printed(x: float, dp: int) -> str:
    return f"{x:.{dp}f}"


def as_printed_row(cells: tuple[int, int, int, int], dp_marg: int, dp_kappa: int,
                   agreement_dp: int | None = None) -> dict:
    """What a paper reporting this table would print, as a call to `recover`."""
    n11, n10, n01, n00 = cells
    n = sum(cells)
    call = {"n": n,
            "p_a": printed((n11 + n10) / n, dp_marg),
            "p_b": printed((n11 + n01) / n, dp_marg),
            "kappa": printed(kappa_from_cells(*cells), dp_kappa)}
    if agreement_dp is not None:
        call["agreement"] = printed((n11 + n00) / n, agreement_dp)
    return call


def all_tables(n: int):
    for n11, n10, n01 in itertools.product(range(n + 1), repeat=3):
        n00 = n - n11 - n10 - n01
        if n00 >= 0:
            yield n11, n10, n01, n00


def non_degenerate(cells: tuple[int, int, int, int]) -> bool:
    """Tables for which kappa is defined: neither marginal at 0 or N, and expected
    agreement below 1. The sweeps in tests/ skip the rest, so the fixture does too."""
    n11, n10, n01, n00 = cells
    n = sum(cells)
    p_a, p_b = (n11 + n10) / n, (n11 + n01) / n
    if p_a in (0.0, 1.0) or p_b in (0.0, 1.0):
        return False
    return abs(1.0 - expected_agreement(p_a, p_b)) >= 1e-12


def named_cases() -> list[tuple[str, dict]]:
    """Every determinate case the Python test suite states by hand."""
    delirium = dict(n=768, n_a=158, n_b=466, kappa="0.29")
    k_reachable = f"{kappa_max(0.200, 0.400):.2f}"
    cases: list[tuple[str, dict]] = [
        # --- results, from tests/test_api.py
        ("delirium_unique", delirium),
        ("delirium_with_agreement", dict(n=768, n_a=158, n_b=466, kappa="0.29",
                                         agreement="0.60")),
        ("delirium_agreement_percent", dict(n=768, n_a=158, n_b=466, kappa="0.29",
                                            agreement="60", agreement_as_percent=True)),
        ("set_of_eleven", dict(n=20306, n_a=866, n_b=1603, kappa="0.22")),
        ("unique_7328", dict(n=7328, n_a=174, n_b=175, kappa="0.668")),
        ("infeasible_agreement", dict(n=370, n_a=165, n_b=160, kappa="0.48",
                                      agreement="73", agreement_as_percent=True)),
        ("infeasible_out_of_range", dict(n=768, n_a=158, n_b=466, kappa="0.95")),
        ("counts_768", dict(n=768, n_a=510, n_b=158, kappa="0.22")),
        ("percent_768", dict(n=768, p_a="66.4", p_b="20.6", kappa="0.22",
                             marginals_as_percent=True)),
        # --- insufficient inputs
        ("insufficient_no_kappa", dict(n=768, n_a=158, n_b=466)),
        ("insufficient_no_b", dict(n=768, n_a=158, kappa="0.29")),
        ("insufficient_no_a", dict(n=768, n_b=466, kappa="0.29")),
        ("insufficient_neither", dict(n=768, kappa="0.29")),
        # --- rounding boundaries
        ("boundary_062", dict(n=24, n_a=2, n_b=4, kappa="0.62")),
        ("boundary_063", dict(n=24, n_a=2, n_b=4, kappa="0.63")),
        ("truncation_240", dict(n=240, p_a="0.512", n_b=100, kappa="0.18")),
        ("zero_marginal_24", dict(n=24, p_a="0.0", p_b="0.0", kappa="0.00",
                                  marginals_as_percent=False)),
        # --- feasibility
        ("infeasible_2pct_90pct", dict(n=1000, p_a="0.0200", p_b="0.9000",
                                       kappa="0.99")),
        ("infeasible_kappa_one", dict(n=1000, p_a="0.200", p_b="0.400",
                                      kappa="1.00")),
        ("reachable_kappa_max", dict(n=1000, p_a="0.200", p_b="0.400",
                                     kappa=k_reachable)),
        ("large_n_percent", dict(n=20306, p_a="4.26", p_b="7.89", kappa="0.22",
                                 marginals_as_percent=True)),
        # --- counts against percentages, from test_enumeration.py
        ("pct_7328", dict(n=7328, p_a="2.1", p_b="2.4",
                          kappa=printed(kappa_from_cells(125, 28, 49, 7126), 3),
                          marginals_as_percent=True)),
        ("cnt_7328", dict(n=7328, n_a=153, n_b=174,
                          kappa=printed(kappa_from_cells(125, 28, 49, 7126), 3))),
        ("pct_768_664", dict(n=768, p_a="66.4", p_b="20.6",
                             kappa=printed(kappa_from_cells(155, 355, 3, 255), 2),
                             marginals_as_percent=True)),
        ("cnt_768_510", dict(n=768, n_a=510, n_b=158,
                             kappa=printed(kappa_from_cells(155, 355, 3, 255), 2))),
        # --- precision, coarse against fine, with and without agreement
        ("coarse_200", as_printed_row((40, 15, 10, 135), 2, 1)),
        ("fine_200", as_printed_row((40, 15, 10, 135), 6, 6)),
        ("coarse_200_with_agreement",
         dict(as_printed_row((40, 15, 10, 135), 2, 1), agreement="0.8750")),
        ("swap_forward", as_printed_row((100, 90, 10, 800), 6, 6)),
        ("swap_reverse", as_printed_row((100, 10, 90, 800), 6, 6)),
        ("asymmetric_precisions", dict(n=768, p_a="0.2", p_b="0.6068",
                                       kappa="0.29")),
        ("negative_kappa", dict(n=200, n_a=100, n_b=100, kappa="-0.20")),
        ("negative_kappa_fine", dict(n=200, n_a=100, n_b=100, kappa="-0.200")),
        ("kappa_zero", dict(n=200, n_a=100, n_b=100, kappa="0.00")),
        ("wide_kappa_interval", dict(n=768, n_a=158, n_b=466, kappa="0.3")),
        ("twelve_decimal_kappa",
         dict(n=768, n_a=158, n_b=466,
              kappa=printed(kappa_from_cells(158, 0, 308, 302), 12))),
        # --- calls that raise
        ("err_marginal_above_n", dict(n=100, n_a=101, n_b=50, kappa="0.5")),
        ("err_negative_marginal", dict(n=100, n_a=-1, n_b=50, kappa="0.5")),
        ("err_kappa_above_one", dict(n=100, n_a=50, n_b=50, kappa="1.4")),
        ("err_kappa_below_minus_one", dict(n=100, n_a=50, n_b=50, kappa="-1.4")),
        ("err_zero_sample", dict(n=0, n_a=0, n_b=0, kappa="0.5")),
        ("err_negative_sample", dict(n=-5, n_a=0, n_b=0, kappa="0.5")),
        ("err_both_a", dict(n=768, n_a=158, p_a="20.6", n_b=466, kappa="0.29",
                            marginals_as_percent=True)),
        ("err_both_b", dict(n=768, n_a=158, n_b=466, p_b="60.7", kappa="0.29",
                            marginals_as_percent=True)),
        ("err_pct_above_one", dict(n=100, p_a="150", p_b="50", kappa="0.5",
                                   marginals_as_percent=True)),
        ("err_pct_below_zero", dict(n=100, p_a="-50", p_b="50", kappa="0.5",
                                    marginals_as_percent=True)),
        ("err_kappa_abc", dict(n=100, n_a=50, n_b=50, kappa="abc")),
        ("err_kappa_empty", dict(n=100, n_a=50, n_b=50, kappa="")),
        ("err_kappa_1e400", dict(n=100, n_a=50, n_b=50, kappa="1e400")),
        ("err_kappa_nan", dict(n=100, n_a=50, n_b=50, kappa="nan")),
        ("err_kappa_inf", dict(n=100, n_a=50, n_b=50, kappa="inf")),
        ("err_kappa_neg_inf", dict(n=100, n_a=50, n_b=50, kappa="-inf")),
        ("err_kappa_infinity", dict(n=100, n_a=50, n_b=50, kappa="Infinity")),
        ("err_agreement_abc", dict(n=100, n_a=50, n_b=50, kappa="0.5",
                                   agreement="abc")),
        ("err_pa_abc", dict(n=100, p_a="abc", n_b=50, kappa="0.5")),
        ("err_pa_1e400", dict(n=100, p_a="1e400", n_b=50, kappa="0.5")),
        ("err_pb_1e400", dict(n=100, n_a=50, p_b="1e400", kappa="0.5")),
        ("err_pa_huge", dict(n=100, p_a="2", p_b="0.5", kappa="0.5")),
    ]
    return cases


def sweep_cases() -> list[tuple[str, dict]]:
    """One case per integer table, at the sample sizes and precisions the
    exhaustive sweeps in tests/ use. These are the sweeps, restated as data."""
    out: list[tuple[str, dict]] = []
    plans = [
        # (n, dp_marg, dp_kappa, agreement_dp) -- the first three reproduce
        # test_every_table_of_size_n_is_in_its_own_candidate_set; the next two
        # reproduce test_the_candidate_set_is_exactly_the_compatible_set; the
        # last three reproduce test_a_reimplementation_...returns_the_same_set.
        (12, 4, 2, None),
        (17, 4, 2, None),
        (18, 2, 1, None),
        (20, 2, 2, None),
        (22, 3, 2, None),
        (24, 3, 2, None),
        (16, 2, 1, 2),
    ]
    for n, dp_marg, dp_kappa, agreement_dp in plans:
        for cells in all_tables(n):
            if not non_degenerate(cells):
                continue
            tag = f"sweep_{n}_{dp_marg}_{dp_kappa}_{'_'.join(map(str, cells))}"
            out.append((tag, as_printed_row(cells, dp_marg, dp_kappa, agreement_dp)))
    return out


def grid_cases() -> list[tuple[str, dict]]:
    """Cases at the sample sizes real reports use, where coarse printing leaves a
    set rather than one table. The exhaustive sweeps run at N <= 24, where almost
    every printed marginal pins its count exactly; a port that only reproduced
    those would be checked mostly on the unique outcome."""
    out: list[tuple[str, dict]] = []
    for n in (200, 768, 2000):
        n_as = [round(n * f) for f in (0.05, 0.21, 0.42, 0.66)]
        n_bs = [round(n * f) for f in (0.09, 0.20, 0.53)]
        for na in n_as:
            for nb in n_bs:
                lo, hi = max(0, na + nb - n), min(na, nb)
                if hi < lo:
                    continue
                for frac in (0.0, 0.35, 0.7, 1.0):
                    n11 = lo + round(frac * (hi - lo))
                    cells = (n11, na - n11, nb - n11, n - na - nb + n11)
                    if not non_degenerate(cells):
                        continue
                    k2 = printed(kappa_from_cells(*cells), 2)
                    tag = f"grid_{n}_{na}_{nb}_{n11}"
                    out.append((f"{tag}_counts", dict(n=n, n_a=na, n_b=nb, kappa=k2)))
                    out.append((f"{tag}_counts_agreement",
                                dict(n=n, n_a=na, n_b=nb, kappa=k2,
                                     agreement=printed((cells[0] + cells[3]) / n, 2))))
                    out.append((f"{tag}_pct",
                                dict(n=n, p_a=printed(100 * na / n, 1),
                                     p_b=printed(100 * nb / n, 1), kappa=k2,
                                     marginals_as_percent=True)))
                    out.append((f"{tag}_prop3",
                                dict(n=n, p_a=printed(na / n, 3),
                                     p_b=printed(nb / n, 3), kappa=k2)))
                    # A kappa displaced well outside what these marginals permit,
                    # so the fixture carries infeasible outcomes at realistic sizes.
                    out.append((f"{tag}_infeasible",
                                dict(n=n, n_a=na, n_b=nb, kappa="0.99")))
                    # An agreement that does not cohere with the kappa.
                    out.append((f"{tag}_bad_agreement",
                                dict(n=n, n_a=na, n_b=nb, kappa=k2,
                                     agreement="0.01")))
    return out


def run(call: dict) -> dict:
    n = call.pop("n")
    try:
        r = recover(n, **call)
    except InvalidInput as exc:
        return {"status": "error", "reason": str(exc), "exception": "InvalidInput",
                "tables": []}
    except Enum2x2Error as exc:
        return {"status": "error", "reason": str(exc), "exception": type(exc).__name__,
                "tables": []}
    return {"status": r.status, "reason": r.reason or "", "exception": "",
            "tables": [(t.n11, t.n10, t.n01, t.n00) for t in r]}


def main(argv: list[str]) -> int:
    outdir = pathlib.Path(argv[1]) if len(argv) > 1 else DEFAULT_OUT
    outdir.mkdir(parents=True, exist_ok=True)

    cases = named_cases() + grid_cases() + sweep_cases()
    case_rows, table_rows = [], []
    for i, (group, call) in enumerate(cases, start=1):
        call = dict(call)
        n = call["n"]
        result = run(dict(call))
        case_rows.append({
            "id": i, "group": group, "n": n,
            "n_a": call.get("n_a", ABSENT), "n_b": call.get("n_b", ABSENT),
            "p_a": call.get("p_a", ABSENT), "p_b": call.get("p_b", ABSENT),
            "kappa": call.get("kappa", ABSENT),
            "agreement": call.get("agreement", ABSENT),
            "marginals_as_percent": str(call.get("marginals_as_percent", False)).upper(),
            "agreement_as_percent": str(call.get("agreement_as_percent", False)).upper(),
            "status": result["status"], "ntables": len(result["tables"]),
            "reason": result["reason"], "exception": result["exception"]})
        for k, t in enumerate(result["tables"], start=1):
            table_rows.append({"id": i, "k": k, "ai": t[0], "bi": t[1],
                               "ci": t[2], "di": t[3]})

    for name, fields, rows in (("cases.csv.gz", CASE_FIELDS, case_rows),
                               ("tables.csv.gz", TABLE_FIELDS, table_rows)):
        with gzip.open(outdir / name, "wt", newline="", compresslevel=9) as f:
            w = csv.DictWriter(f, fields)
            w.writeheader()
            w.writerows(rows)

    counts: dict[str, int] = {}
    for r in case_rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"  {len(case_rows)} cases, {len(table_rows)} tables -> {outdir}")
    print("  " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    for name in ("cases.csv.gz", "tables.csv.gz"):
        print(f"  {name}: {(outdir / name).stat().st_size / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
