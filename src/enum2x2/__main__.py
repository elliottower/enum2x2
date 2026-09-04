"""Recover tables from a CSV or JSON of published comparisons.

    enum2x2 comparisons.csv
    enum2x2 comparisons.json --format json

Each row gives one comparison. Columns: n, and then either n_a/n_b (exact counts)
or p_a/p_b (the strings the source printed), plus kappa, and optionally agreement.
Strings are read as printed, so a marginal of "2.10" keeps its precision.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

from ._recover import INFEASIBLE, INSUFFICIENT, UNIQUE, recover_many

INT_FIELDS = {"n", "n_a", "n_b"}
BOOL_FIELDS = {"marginals_as_percent", "agreement_as_percent"}


def _row(raw: dict) -> dict:
    out = {}
    for k, v in raw.items():
        if v is None or v == "":
            continue
        k = k.strip()
        if k in INT_FIELDS:
            out[k] = int(float(v))
        elif k in BOOL_FIELDS:
            out[k] = str(v).strip().lower() in ("1", "true", "yes", "y")
        else:
            out[k] = str(v).strip()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="enum2x2", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="CSV or JSON file of comparisons")
    ap.add_argument("--format", choices=("csv", "json"), default=None,
                    help="input format (default: from the file extension)")
    ap.add_argument("--out", default=None, help="write results as JSON here")
    a = ap.parse_args(argv)

    fmt = a.format or ("json" if a.path.lower().endswith(".json") else "csv")
    with open(a.path) as f:
        raw = json.load(f) if fmt == "json" else list(csv.DictReader(f))
    if isinstance(raw, dict):
        raw = list(raw.values())

    results = recover_many([_row(r) for r in raw])

    report = []
    for src, r in zip(raw, results):
        entry = {"status": r.status, "n": r.n, "candidates": len(r),
                 "published": r.published}
        if r.reason:
            entry["reason"] = r.reason
        if r.status == UNIQUE:
            entry["table"] = r.table.as_dict()
            entry["asymmetry"] = r.table.asymmetry
        elif r.tables:
            entry["cell_ranges"] = {k: list(v) for k, v in r.cell_ranges.items()}
        report.append(entry)

    if a.out:
        with open(a.out, "w") as f:
            json.dump(report, f, indent=2)

    width = max((len(str(e.get("published", {}))) for e in report), default=0)
    for e in report:
        line = f"  {e['status']:12s} N={str(e['n']):>7s}  {e['candidates']:>4d} table(s)"
        if e["status"] == UNIQUE:
            t = e["table"]
            line += f"   {t['n11']}/{t['n10']}/{t['n01']}/{t['n00']}"
        elif e["status"] in (INFEASIBLE, INSUFFICIENT):
            line += f"   {e.get('reason','')}"
        print(line)
    counts = {s: sum(1 for e in report if e["status"] == s) for s in
              {e["status"] for e in report}}
    print("  " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    if a.out:
        print(f"  written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
