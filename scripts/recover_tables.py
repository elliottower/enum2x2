"""What does a published agreement statistic identify about the joint table?

A study comparing two binary criteria on one population that reports only Cohen's
kappa has published more than it printed. With the sample size and both positive
marginals, the exact quantities determine the 2x2 through

    p_e  = p_A p_B + (1 - p_A)(1 - p_B)
    p_o  = kappa (1 - p_e) + p_e
    p_11 = (p_o + p_A + p_B - 1) / 2

But the exact quantities are not what gets printed. A marginal given as 4.26% and
a kappa given as 0.22 are intervals, and an interval of inputs is compatible with
a set of integer tables rather than one. This module therefore enumerates instead
of inverting: it walks every integer table whose marginals and kappa round back to
the published strings, and reports what survives.

Four outcomes per comparison:

    unique               exactly one integer table is compatible
    set_identified       several are; cell and statistic ranges are reported
    infeasible           none is, so the published figures are mutually inconsistent
    insufficient_inputs  a required quantity was not published

The distinction is the point. Reporting a single recovered table where the
published rounding leaves a set would assert precision the source does not carry.

Rounding is bounded and deterministic, not stochastic, so intervals are carried
exactly and never combined in quadrature. Precision is declared per value in
inputs.json and never inferred from a Python float, because 0.10 and 0.100 are
the same float and imply different intervals.

Plan: experiments/table_recovery/PREREG.md (frozen; deviations in its log).
Inputs: experiments/table_recovery/inputs.json.
Output: results/recovery.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from decimal import Decimal

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUTS = PROJECT_ROOT / "experiments" / "table_recovery" / "inputs.json"
RESULTS = PROJECT_ROOT / "results" / "recovery.json"


class RecoveryError(Exception):
    """The declared inputs are malformed."""


def rounding_interval(printed: str, as_percent: bool = False) -> tuple[float, float]:
    """The closed interval of exact values that round to a printed string.

    `printed` is the literal text of the source, so "0.10" and "0.1" give
    different intervals, which is the whole reason values are declared as strings.

    The interval is closed at both ends deliberately. A value falling exactly on a
    boundary rounds up under one convention and down under another, and published
    sources do not state which they used. Admitting both ends can only widen the
    candidate set, which understates what the source identifies; excluding one end
    can drop the true table, which asserts a precision the source does not carry.
    A binary table of 24 with cells 2, 0, 2, 20 has kappa exactly 0.625, printed
    as either "0.62" or "0.63", and a half-open interval loses it.
    """
    d = Decimal(printed)
    step = Decimal(1).scaleb(d.as_tuple().exponent)     # unit in the last place
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
        raise RecoveryError("empty table")
    p_o = (n11 + n00) / n
    p_e = expected_agreement((n11 + n10) / n, (n11 + n01) / n)
    if abs(1.0 - p_e) < 1e-12:
        raise RecoveryError("expected agreement is 1; kappa undefined")
    return (p_o - p_e) / (1.0 - p_e)


def kappa_max(p_a: float, p_b: float) -> float:
    """Largest kappa these marginals permit. Equivalently uses p_o_max = 1 - |p_A - p_B|."""
    p_e = expected_agreement(p_a, p_b)
    p_o_max = min(p_a, p_b) + min(1.0 - p_a, 1.0 - p_b)
    if abs(1.0 - p_e) < 1e-12:
        raise RecoveryError("expected agreement is 1; kappa_max undefined")
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
        raise RecoveryError("expected agreement is 1; kappa_min undefined")
    return (p_o_min - p_e) / (1.0 - p_e)


def _counts_rounding_to(printed: str, n: int, as_percent: bool) -> list[int]:
    lo, hi = rounding_interval(printed, as_percent)
    first, last = max(0, int(lo * n)), min(n, int(hi * n) + 1)
    return [c for c in range(first, last + 1) if lo - 1e-12 <= c / n <= hi + 1e-12]


def marginal_counts(row: dict, side: str, n: int) -> list[int]:
    """Positive counts compatible with what the source printed for one criterion.

    A source printing an exact count ("153 subjects") identifies one value; a
    source printing a percentage ("2.1%") identifies an interval. Converting a
    printed count into a percentage would discard that, and the plan requires the
    marginal to be used as printed, so counts are taken as counts.
    """
    exact = row.get(f"n_{side}")
    if exact is not None:
        if not 0 <= exact <= n:
            raise RecoveryError(f"n_{side} = {exact} outside [0, {n}]")
        return [int(exact)]
    return _counts_rounding_to(row[f"p_{side}"], n, row.get("marginals_as_percent", False))


def marginal_matches(row: dict, side: str, count: int, n: int) -> bool:
    """Does an integer count agree with the marginal the source printed?"""
    exact = row.get(f"n_{side}")
    if exact is not None:
        return count == exact
    return rounds_to(count / n, row[f"p_{side}"], row.get("marginals_as_percent", False))


def enumerate_tables(row: dict) -> list[dict]:
    """Every integer table consistent with every published figure."""
    n = row["N"]
    a_counts = marginal_counts(row, "A", n)
    b_counts = marginal_counts(row, "B", n)
    kappa_printed = row["kappa"]
    p_o_printed = row.get("p_o")
    p_o_pct = row.get("p_o_as_percent", False)

    out = []
    for n_a in a_counts:
        for n_b in b_counts:
            lo = max(0, n_a + n_b - n)
            hi = min(n_a, n_b)
            for n11 in range(lo, hi + 1):
                n10, n01 = n_a - n11, n_b - n11
                n00 = n - n11 - n10 - n01
                if n00 < 0:
                    continue
                # A candidate pair can make expected agreement exactly 1, which
                # leaves kappa undefined. That pair contributes no table; it is not
                # a reason to abandon the row, so it is skipped rather than raised.
                if n * n == n_a * n_b + (n - n_a) * (n - n_b):
                    continue
                k = kappa_from_cells(n11, n10, n01, n00)
                if not rounds_to(k, kappa_printed):
                    continue
                p_o = (n11 + n00) / n
                if p_o_printed is not None and not rounds_to(p_o, p_o_printed, p_o_pct):
                    continue
                out.append({
                    "cells": {"n11": n11, "n10": n10, "n01": n01, "n00": n00},
                    "kappa": k,
                    "p_o": p_o,
                    "discordance": 1.0 - p_o,
                    "d_A_pos_B_neg": n10 / n,
                    "d_A_neg_B_pos": n01 / n,
                    "kappa_max": kappa_max(n_a / n, n_b / n),
                    "kappa_min": kappa_min(n_a / n, n_b / n),
                })
    return out


def _span(values: list[float]) -> dict:
    return {"min": min(values), "max": max(values)}


ELIGIBLE_DENOMINATORS = {"explicit_same", "inferred"}

# Figures a source may or may not print. A row is enumerated over whichever are
# present; when the set is empty, each is dropped in turn to find which excludes.
OPTIONAL_CONSTRAINTS = ("p_o",)


def ineligibility(row: dict) -> str | None:
    """Why a row is outside the method, decided before any table is enumerated."""
    if row.get("kappa_variant") != "unweighted Cohen":
        return f"kappa variant is {row.get('kappa_variant')!r}; the identity holds for unweighted Cohen"
    if row.get("denominator_status") not in ELIGIBLE_DENOMINATORS:
        return f"denominator_status is {row.get('denominator_status')!r}"
    for field in ("N", "kappa"):
        if row.get(field) is None:
            return f"{field} not reported"
    for side in ("A", "B"):
        if row.get(f"n_{side}") is None and row.get(f"p_{side}") is None:
            return f"neither n_{side} nor p_{side} reported"
    return None


def analyse(key: str, row: dict) -> dict:
    tables = enumerate_tables(row)
    result = {
        "key": key,
        "condition": row["condition"],
        "criteria": row["criteria"],
        "crossing": row["crossing"],
        "N": row["N"],
        "published": {k: row[k] for k in ("n_A", "n_B", "p_A", "p_B", "kappa")
                      if row.get(k) is not None},
        "candidate_count": len(tables),
        "source_artifact": row["source_artifact"],
        "quote": row["quote"],
    }
    if row.get("p_o") is not None:
        result["published"]["p_o"] = row["p_o"]
    if row.get("kappa_provenance"):
        result["kappa_provenance"] = row["kappa_provenance"]

    if not tables:
        result["status"] = "infeasible"
        # Distinguish a kappa the marginals cannot produce from one they could,
        # which fails for the finer reason that no integer table lands on it.
        k_lo, k_hi = rounding_interval(row["kappa"])
        spans = []
        for n_a in marginal_counts(row, "A", row["N"]):
            for n_b in marginal_counts(row, "B", row["N"]):
                p_a, p_b = n_a / row["N"], n_b / row["N"]
                spans.append((kappa_min(p_a, p_b), kappa_max(p_a, p_b)))
        if spans:
            feasible = (min(lo for lo, _ in spans), max(hi for _, hi in spans))
            result["feasible_kappa_range"] = {"min": feasible[0], "max": feasible[1]}
            if k_hi < feasible[0] or k_lo > feasible[1]:
                result["reason"] = ("the published kappa lies outside the range "
                                    "these marginals permit")
                return result
            # The marginals permit this kappa, so some other published figure is
            # doing the excluding. Drop each optional constraint in turn and name
            # the one whose removal admits a table, rather than reporting that no
            # table attains the kappa when one does.
            binding = {}
            for optional in OPTIONAL_CONSTRAINTS:
                if row.get(optional) is None:
                    continue
                without = {k: v for k, v in row.items() if k != optional}
                admitted = enumerate_tables(without)
                if admitted:
                    binding[optional] = {
                        "candidate_count": len(admitted),
                        "example_cells": admitted[0]["cells"],
                        "example_value": admitted[0]["p_o"] if optional == "p_o" else None,
                    }
            result["binding_constraints"] = binding
            result["reason"] = (
                "no integer table satisfies every published figure at once; "
                + "; ".join(f"dropping {k} admits {v['candidate_count']}"
                            for k, v in binding.items())
                if binding else
                "the marginals permit this kappa, but no integer table attains it")
        return result
    result["status"] = "unique" if len(tables) == 1 else "set_identified"

    for name, get in (("n11", lambda t: t["cells"]["n11"]),
                      ("n10", lambda t: t["cells"]["n10"]),
                      ("n01", lambda t: t["cells"]["n01"]),
                      ("n00", lambda t: t["cells"]["n00"])):
        result.setdefault("cell_ranges", {})[name] = _span([get(t) for t in tables])
    result["raw_agreement"] = _span([t["p_o"] for t in tables])
    result["total_discordance"] = _span([t["discordance"] for t in tables])
    result["directional_discordance"] = {
        "A_positive_B_negative": _span([t["d_A_pos_B_neg"] for t in tables]),
        "A_negative_B_positive": _span([t["d_A_neg_B_pos"] for t in tables]),
    }
    result["kappa_max"] = _span([t["kappa_max"] for t in tables])
    result["kappa_min"] = _span([t["kappa_min"] for t in tables])
    result["kappa_over_kappa_max"] = _span(
        [t["kappa"] / t["kappa_max"] for t in tables if abs(t["kappa_max"]) > 1e-9])
    if len(tables) == 1:
        result["table"] = tables[0]["cells"]

    # A source that prints its own cells is a test of the method, not an input to it.
    if row.get("published_cells"):
        pub = row["published_cells"]
        n = row["N"]
        k_pub = kappa_from_cells(pub["n11"], pub["n10"], pub["n01"], pub["n00"])
        result["self_test"] = {
            "published_cells": pub,
            # (a) do the printed cells reproduce the printed summaries?
            "cells_reproduce_summaries": {
                "p_A": marginal_matches(row, "A", pub["n11"] + pub["n10"], n),
                "p_B": marginal_matches(row, "B", pub["n11"] + pub["n01"], n),
                "kappa": rounds_to(k_pub, row["kappa"]),
                "kappa_from_published_cells": k_pub,
                "cells_sum_to_N": sum(pub.values()) == n,
            },
            # (b) does enumeration from the summaries alone contain them?
            "in_candidate_set": any(t["cells"] == pub for t in tables),
            # A source that printed no agreement statistic of its own supplies a
            # kappa this analysis computed from the very cells being recovered, so
            # the round trip is circular and shows only that it is a superset.
            "circular": row.get("kappa_provenance") == "derived by this analysis",
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Enumerate tables compatible with published figures.")
    ap.add_argument("--inputs", default=str(INPUTS))
    ap.add_argument("--out", default=str(RESULTS))
    a = ap.parse_args()

    rows = {k: v for k, v in json.loads(pathlib.Path(a.inputs).read_text()).items()
            if k != "_README"}
    # The gate is applied to every row, not only to those hand-marked for
    # recovery, so that the eligible denominator is computed from the declared
    # inputs rather than restated from the hand marking.
    eligible = {k: ineligibility(r) is None for k, r in rows.items()}

    analysed, skipped = [], []
    for key, row in rows.items():
        if row["status"] != "recover":
            entry = {"key": key, "condition": row["condition"],
                     "status": "insufficient_inputs", "reason": row["reason"]}
            if eligible[key]:
                entry["gate_disagrees"] = ("declared not_attempted, but the row "
                                           "carries every input the gate requires")
            skipped.append(entry)
            continue
        why = ineligibility(row)
        if why is not None:
            skipped.append({"key": key, "condition": row["condition"],
                            "status": "ineligible", "reason": why})
            continue
        analysed.append(analyse(key, row))

    by = lambda s: [r for r in analysed if r["status"] == s]
    report = {
        "plan": "experiments/table_recovery/PREREG.md",
        "method": ("integer tables enumerated over the rounding intervals of every "
                   "published figure; no point estimate is formed"),
        "counts": {"rows_total": len(rows), "attempted": len(analysed),
                   "unique": len(by("unique")),
                   "set_identified": len(by("set_identified")),
                   "infeasible": len(by("infeasible")),
                   "insufficient_inputs": len(skipped),
                   "eligible_denominator": sum(eligible.values()),
                   "gate_disagreements": sum(
                       1 for e in skipped if e.get("gate_disagrees"))},
        "results": analysed,
        "insufficient_inputs": skipped,
    }
    out = pathlib.Path(a.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    for r in analysed:
        line = f"  {r['status']:16s} {r['key']:16s} {r['candidate_count']:>6d} candidates"
        if "self_test" in r:
            line += f"   published cells in set: {r['self_test']['in_candidate_set']}"
        print(line)
    c = report["counts"]
    print(f"  unique {c['unique']}, set-identified {c['set_identified']}, "
          f"infeasible {c['infeasible']}, not attempted {c['insufficient_inputs']}")
    try:
        shown = out.relative_to(PROJECT_ROOT)
    except ValueError:
        shown = out
    print(f"  written to {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
