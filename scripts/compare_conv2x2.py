"""How does a point reconstruction compare with an enumerated set under rounding?

`metafor::conv.2x2` reconstructs the cells of a 2x2 from a sample size, both
marginal counts and one further statistic -- an odds ratio, a phi coefficient or a
chi-square. Cohen's kappa is not among its inputs, but the structural question is
the same, and its documentation states the limit this module is built around:

    In practice, when such accuracy measures are reported, the values are typically
    rounded to some extent. This introduces inaccuracies into the reconstruction.
    The present function uses optimization methods to reconstruct the table counts
    so that the discrepancy between the reported measures and the reconstructed
    ones are minimized. This is not guaranteed to reconstruct the actual table
    exactly, but should usually yield a close match.

This script measures what "close" costs. The draw is seeded, because the figures it
returns are quoted in the manuscript and a quoted number has to be reproducible. It draws tables at the sample sizes the
paper's corpus actually contains, prints one statistic to two decimals as a journal
would, and asks each method what it recovers: conv.2x2 from the rounded phi, and
the enumeration here from the rounded kappa. Both receive the same sample size,
the same marginal counts and the same printed precision.

The comparison is between a point estimate and a set, not between phi and kappa.
Requires R with metafor; skips with a message if either is absent.

Written to results/conv2x2_comparison.json.
"""
from __future__ import annotations

import csv
import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from recover_tables import PROJECT_ROOT, enumerate_tables, kappa_from_cells

SAMPLE_SIZES = (2_000, 9_170, 20_306)   # the corpus contains 9,170 and 20,306
SEED = 20260904                          # fixed: the figures below are quoted in the paper
DRAWS_PER_SIZE = 400
DECIMALS = 2

R_SCRIPT = """suppressMessages(library(metafor))
a <- commandArgs(trailingOnly=TRUE)
d <- read.csv(a[1])
o <- conv.2x2(ri=d$phi, ni=d$ni, n1i=d$n1i, n2i=d$n2i, data=d)
write.csv(o[,c("id","ai","bi","ci","di")], a[2], row.names=FALSE)
"""


def phi(n11: int, n10: int, n01: int, n00: int) -> float:
    den = ((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)) ** 0.5
    return (n11 * n00 - n10 * n01) / den if den else float("nan")


def draw(rng: random.Random) -> list[tuple[int, tuple[int, int, int, int]]]:
    out, i = [], 0
    for n in SAMPLE_SIZES:
        for _ in range(DRAWS_PER_SIZE):
            n_a = rng.randint(int(0.01 * n), int(0.30 * n))
            n_b = rng.randint(int(0.01 * n), int(0.30 * n))
            n11 = rng.randint(max(0, n_a + n_b - n), min(n_a, n_b))
            n10, n01 = n_a - n11, n_b - n11
            n00 = n - n11 - n10 - n01
            if n00 < 0 or n_a in (0, n) or n_b in (0, n):
                continue
            if phi(n11, n10, n01, n00) != phi(n11, n10, n01, n00):
                continue
            i += 1
            out.append((i, (n11, n10, n01, n00)))
    return out


def main() -> int:
    if not shutil.which("Rscript"):
        print("  Rscript not found; skipping"); return 0
    probe = subprocess.run(["Rscript", "-e",
                            'cat(as.character(requireNamespace("metafor", quietly=TRUE)))'],
                           capture_output=True, text=True)
    if "TRUE" not in probe.stdout:
        print("  metafor not installed; skipping"); return 0

    tables = draw(random.Random(SEED))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "r.R").write_text(R_SCRIPT)
        with open(tmp / "in.csv", "w", newline="") as f:
            w = csv.DictWriter(f, ["id", "phi", "ni", "n1i", "n2i"]); w.writeheader()
            for i, (a, b, c, d) in tables:
                w.writerow({"id": i, "phi": round(phi(a, b, c, d), DECIMALS),
                            "ni": a + b + c + d, "n1i": a + b, "n2i": a + c})
        subprocess.run(["Rscript", str(tmp / "r.R"), str(tmp / "in.csv"),
                        str(tmp / "out.csv")], check=True, capture_output=True)
        got = {int(r["id"]): r for r in csv.DictReader(open(tmp / "out.csv"))}

    errors, widths, exact, unavailable, contains = [], [], 0, 0, 0
    for i, (a, b, c, d) in tables:
        r = got.get(i)
        if r is None or r["ai"] in ("NA", ""):
            unavailable += 1
        else:
            cells = [float(r[k]) for k in ("ai", "bi", "ci", "di")]
            errors.append(max(abs(v - t) for v, t in zip(cells, (a, b, c, d))))
            exact += all(abs(v - t) < 1e-9 for v, t in zip(cells, (a, b, c, d)))
        n = a + b + c + d
        cand = enumerate_tables({"N": n, "n_A": a + b, "n_B": a + c,
                                 "kappa": f"{kappa_from_cells(a, b, c, d):.{DECIMALS}f}"})
        n11s = [t["cells"]["n11"] for t in cand]
        widths.append(max(n11s) - min(n11s))
        contains += any(t["cells"] == {"n11": a, "n10": b, "n01": c, "n00": d} for t in cand)

    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    report = {
        "sample_sizes": list(SAMPLE_SIZES), "decimals_printed": DECIMALS, "seed": SEED,
        "tables": len(tables),
        "point_reconstruction": {
            "tool": "metafor::conv.2x2", "input_statistic": "phi",
            "reconstructed": len(errors), "unavailable": unavailable,
            "exact": exact, "exact_fraction": exact / len(tables),
            "largest_cell_error": {"median": q(errors, 0.5), "p90": q(errors, 0.9),
                                   "max": max(errors)},
            "within_1_count": sum(1 for e in errors if e <= 1) / len(errors),
            "within_5_counts": sum(1 for e in errors if e <= 5) / len(errors)},
        "enumeration": {
            "input_statistic": "unweighted Cohen kappa",
            "contains_true_table": contains,
            "contains_fraction": contains / len(tables),
            "n11_range_width": {"median": q(widths, 0.5), "p90": q(widths, 0.9),
                                "max": max(widths)},
            "uniquely_identified": sum(1 for w in widths if w == 0)},
    }
    out = PROJECT_ROOT / "results" / "conv2x2_comparison.json"
    out.write_text(json.dumps(report, indent=2) + "\n")

    pr, en = report["point_reconstruction"], report["enumeration"]
    print(f"  {len(tables)} tables at N = {', '.join(f'{n:,}' for n in SAMPLE_SIZES)}, "
          f"one statistic printed to {DECIMALS} decimals")
    print(f"  conv.2x2 point estimate: exact {pr['exact_fraction']:.1%}, "
          f"largest cell error median {pr['largest_cell_error']['median']:.0f}, "
          f"p90 {pr['largest_cell_error']['p90']:.0f}, max {pr['largest_cell_error']['max']:.0f}")
    print(f"  enumeration: contains the true table {en['contains_fraction']:.1%}, "
          f"n11 range width median {en['n11_range_width']['median']}, "
          f"max {en['n11_range_width']['max']}")
    print(f"  written to {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
