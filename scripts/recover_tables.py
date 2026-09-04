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
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
INPUTS = PROJECT_ROOT / "experiments" / "table_recovery" / "inputs.json"
RESULTS = PROJECT_ROOT / "results" / "recovery.json"


# The primitives live in the package. They are imported rather than repeated so
# that the exhaustive tests below, which exercise this module, exercise the shipped
# library too: two copies of the arithmetic means the tested one need not be the
# one a user installs.
from enum2x2 import (Enum2x2Error, InvalidInput, UndefinedStatistic,
                     expected_agreement, kappa_from_cells, kappa_max, kappa_min,
                     recover, rounding_interval, rounds_to)
from enum2x2._core import counts_rounding_to as _counts_rounding_to

# Kept as the name this module has always raised. It is the base class, so it
# still names both an impossible input and an undefined statistic.
RecoveryError = Enum2x2Error


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
    """Every integer table consistent with every published figure.

    A thin adapter over `enum2x2.recover`, so this module and the shipped library
    run one enumeration rather than two. The corpus schema uses `N`, `p_A`/`n_A`
    and `p_o`; the library uses `n`, `p_a`/`n_a` and `agreement`.
    """
    n = row["N"]
    call = {"n": n, "kappa": row["kappa"],
            "marginals_as_percent": row.get("marginals_as_percent", False)}
    for lib, corpus in (("a", "A"), ("b", "B")):
        if row.get(f"n_{corpus}") is not None:
            call[f"n_{lib}"] = row[f"n_{corpus}"]
        else:
            call[f"p_{lib}"] = row[f"p_{corpus}"]
    if row.get("p_o") is not None:
        call["agreement"] = row["p_o"]
        call["agreement_as_percent"] = row.get("p_o_as_percent", False)

    out = []
    for t in recover(**call):
        p_a, p_b = (t.n11 + t.n10) / n, (t.n11 + t.n01) / n
        out.append({
            "cells": t.as_dict(),
            "kappa": t.kappa,
            "p_o": t.agreement,
            "discordance": 1.0 - t.agreement,
            "d_A_pos_B_neg": t.n10 / n,
            "d_A_neg_B_pos": t.n01 / n,
            "kappa_max": kappa_max(p_a, p_b),
            "kappa_min": kappa_min(p_a, p_b),
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
