"""Which published figure empties the candidate set for daghi2026?

`recover_tables.py` enumerates over the figures the plan registers: N, both
marginals and kappa, plus any published raw agreement. For `daghi2026` that set is
empty. This asks which figure is doing the excluding, and what the source's
remaining figures identify.

It is post hoc. Sensitivity and specificity are not registered inputs and are used
here only to diagnose the empty set. Nothing here feeds the registered analysis.

Two things are established rather than assumed:

  * every count is forced. Each printed rate is checked against every integer
    count on its denominator, and the diagnosis proceeds only where exactly one
    survives, so no cell is point-estimated by rounding a rate.
  * the direction is forced. The mirrored reading, in which the criterion rather
    than the clinician is the reference, would impeach a different figure. Every
    possible reference total is scanned, and only one reproduces the source's
    printed statistics, so which figure is the odd one out is not a choice.

Written to results/daghi_diagnosis.json.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from recover_tables import (PROJECT_ROOT, kappa_from_cells, kappa_max, kappa_min,
                            rounds_to)

N = 370
PUBLISHED_CRITERION_PREVALENCE = "44.6"
PUBLISHED_REFERENCE_PREVALENCE = "43.2"

# Table 2 gives agreement and kappa per combination; the sentence beneath it gives
# sensitivity and specificity for the same three.
COMBINATIONS = [
    {"name": "at least one criterion met", "sens": "95.6", "spec": "55.2",
     "agreement": "73", "kappa": "0.48"},
    {"name": "at least two criteria met", "sens": "90.6", "spec": "83.8",
     "agreement": "87", "kappa": "0.73"},
    {"name": "all three criteria met", "sens": "72.5", "spec": "91.9",
     "agreement": "84", "kappa": "0.66"},
]


def counts_matching(printed: str, denominator: int) -> list[int]:
    """Every integer count on this denominator whose rate rounds to the printed one."""
    if denominator <= 0:
        return []
    return [c for c in range(denominator + 1)
            if rounds_to(c / denominator, printed, as_percent=True)]


def table_for(combination: dict, n_ref: int) -> dict | None:
    """The 2x2 this combination's sensitivity and specificity force, if they force one."""
    positives = counts_matching(combination["sens"], n_ref)
    negatives = counts_matching(combination["spec"], N - n_ref)
    if len(positives) != 1 or len(negatives) != 1:
        return None
    n11, n00 = positives[0], negatives[0]
    n10, n01 = (N - n_ref) - n00, n_ref - n11
    return {"n11": n11, "n10": n10, "n01": n01, "n00": n00}


def reproduces(combination: dict, cells: dict) -> bool:
    p_o = (cells["n11"] + cells["n00"]) / N
    return (rounds_to(p_o, combination["agreement"], as_percent=True)
            and rounds_to(kappa_from_cells(**cells), combination["kappa"]))


def main() -> int:
    ref_candidates = counts_matching(PUBLISHED_REFERENCE_PREVALENCE, N)
    crit_candidates = counts_matching(PUBLISHED_CRITERION_PREVALENCE, N)
    assert len(ref_candidates) == 1 and len(crit_candidates) == 1
    n_ref, n_crit = ref_candidates[0], crit_candidates[0]

    # Which reference total can carry all three printed rows? Scanning every total
    # tests the mirrored reading too, in which the criterion would be the reference.
    surviving = []
    for d in range(1, N):
        tables = [table_for(c, d) for c in COMBINATIONS]
        if any(t is None for t in tables):
            continue
        if all(reproduces(c, t) for c, t in zip(COMBINATIONS, tables)):
            surviving.append(d)

    rows = []
    for c in COMBINATIONS:
        cells = table_for(c, n_ref)
        p_a, p_b = (cells["n11"] + cells["n10"]) / N, n_ref / N
        k = kappa_from_cells(**cells)
        rows.append({
            "combination": c["name"], "cells": cells,
            "counts_forced": {
                "positives_matching_sensitivity": counts_matching(c["sens"], n_ref),
                "negatives_matching_specificity": counts_matching(c["spec"], N - n_ref)},
            "reproduces": {
                "agreement": {"computed": (cells["n11"] + cells["n00"]) / N,
                              "published": c["agreement"]},
                "kappa": {"computed": k, "published": c["kappa"]}},
            "implied_criterion_prevalence": p_a,
            "kappa_max": kappa_max(p_a, p_b), "kappa_min": kappa_min(p_a, p_b),
            "kappa_over_kappa_max": k / kappa_max(p_a, p_b),
        })

    standard = rows[0]
    implied = standard["cells"]["n11"] + standard["cells"]["n10"]
    out = {
        "row": "daghi2026",
        "registered_result": "infeasible; no integer table reproduces N, both "
                             "published marginals, the published raw agreement and "
                             "kappa together",
        "post_hoc": True,
        "reference_total_scan": {
            "totals_tested": N - 1,
            "totals_reproducing_all_three_printed_rows": surviving,
            "reading": "Only one reference total carries the source's own printed "
                       "statistics, so the direction of the diagnosis is forced by "
                       "the figures rather than chosen. The mirrored reading, with "
                       "the criterion as reference, is not among the survivors.",
        },
        "combinations": rows,
        "conflict": {
            "published_criterion_prevalence": PUBLISHED_CRITERION_PREVALENCE,
            "count_published": n_crit,
            "count_implied_by_the_other_figures": implied,
            "prevalence_implied": implied / N,
            "reading": "N, the clinician marginal, sensitivity, specificity, raw "
                       "agreement and kappa are mutually consistent and determine "
                       "one table. The criterion prevalence printed alongside them "
                       "is not the marginal of that table. Which of the six "
                       "published figures is in error does not follow from the "
                       "arithmetic: the summaries may rest on different "
                       "denominators, on different versions of the classifying "
                       "variable, or on separate analysis sets, and the report "
                       "states none of these.",
        },
    }
    path = PROJECT_ROOT / "results" / "daghi_diagnosis.json"
    path.write_text(json.dumps(out, indent=2) + "\n")

    for r in rows:
        rep = r["reproduces"]; c = r["cells"]
        print(f"  {r['combination']:26s} {c['n11']:4d}/{c['n10']:3d}/{c['n01']:3d}/{c['n00']:4d}"
              f"   agree {rep['agreement']['computed']:6.2%} (printed {rep['agreement']['published']})"
              f"   kappa {rep['kappa']['computed']:.3f} (printed {rep['kappa']['published']})"
              f"   prevalence {r['implied_criterion_prevalence']:6.1%}")
    print(f"\n  reference totals reproducing all three rows: {surviving} of 1..{N-1}")
    print(f"  criterion positives published {n_crit}, implied {implied}"
          f"  ({n_crit / N:.1%} against {implied / N:.1%})")
    print(f"  written to {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
