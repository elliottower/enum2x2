"""Did the registered hypotheses hold?

The plan in experiments/table_recovery/PREREG.md registers three hypotheses and a
threshold for each. Their outcomes were recorded in the plan's own log and nowhere
else, so a reader could not check them against the results without recomputing.
This writes them to a file.

H1  at least 8 of the eligible comparisons recover
H2  directional asymmetry D = |n10 - n01| / (n10 + n01) exceeds 1/3 in at least
    half of the recovered comparisons
H3  kappa_max under the observed marginals is below 0.9 in at least half

Written to results/hypothesis_outcomes.json.
"""
from __future__ import annotations

import json
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

RECOVERED = ("unique", "set_identified")


def span_bounds(row: dict, key: str) -> tuple[float, float]:
    d = row[key]
    return d["min"], d["max"]


def main() -> int:
    results = json.loads((PROJECT_ROOT / "results" / "recovery.json").read_text())
    rows = results["results"]
    recovered = [r for r in rows if r["status"] in RECOVERED]
    eligible = results["counts"]["eligible_denominator"]

    h1 = {"hypothesis": "at least 8 of the eligible comparisons recover",
          "threshold": 8, "eligible": eligible, "recovered": len(recovered),
          "holds": len(recovered) >= 8}

    asym = {}
    for r in recovered:
        lo10, hi10 = span_bounds(r, "cell_ranges")["n10"] if False else (
            r["cell_ranges"]["n10"]["min"], r["cell_ranges"]["n10"]["max"])
        lo01, hi01 = r["cell_ranges"]["n01"]["min"], r["cell_ranges"]["n01"]["max"]
        # Smallest asymmetry the candidate set admits, so the count is conservative.
        ds = [abs(a - b) / (a + b) for a in (lo10, hi10) for b in (lo01, hi01) if a + b]
        asym[r["key"]] = min(ds) if ds else None
    h2_hits = [k for k, v in asym.items() if v is not None and v > 1 / 3]
    h2 = {"hypothesis": "directional asymmetry above one third in at least half",
          "statistic": "D = |n10 - n01| / (n10 + n01), smallest value the candidate set admits",
          "threshold": len(recovered) / 2, "of": len(recovered),
          "hits": len(h2_hits), "which": sorted(h2_hits),
          "per_comparison": asym, "holds": len(h2_hits) >= len(recovered) / 2}

    kmax = {r["key"]: r["kappa_max"]["max"] for r in recovered}
    h3_hits = [k for k, v in kmax.items() if v < 0.9]
    h3 = {"hypothesis": "kappa_max below 0.9 in at least half",
          "threshold": len(recovered) / 2, "of": len(recovered),
          "hits": len(h3_hits), "which": sorted(h3_hits),
          "per_comparison": kmax, "holds": len(h3_hits) >= len(recovered) / 2}

    out = {"plan": "experiments/table_recovery/PREREG.md",
           "note": "H2 and H3 are void if H1 fails, per the plan.",
           "H1": h1, "H2": h2, "H3": h3}
    path = PROJECT_ROOT / "results" / "hypothesis_outcomes.json"
    path.write_text(json.dumps(out, indent=2) + "\n")

    for name, h in (("H1", h1), ("H2", h2), ("H3", h3)):
        got = h.get("recovered", h.get("hits"))
        of = h.get("eligible", h.get("of"))
        print(f"  {name}  {got} of {of}, threshold {h['threshold']:g}"
              f"   {'HOLDS' if h['holds'] else 'FAILS'}")
    print(f"  written to {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
