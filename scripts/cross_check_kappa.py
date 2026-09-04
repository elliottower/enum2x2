"""Does this module's kappa agree with the established implementations?

The enumeration is only as trustworthy as the statistic it inverts. Cohen's kappa
has been implemented independently many times in R, by people who were not thinking
about this problem, and those implementations are the closest thing to an
authoritative reading of the definition.

This computes kappa for a sweep of integer 2x2 tables with this module and with
every R implementation available on the machine, and reports the largest
disagreement. Packages that are not installed are skipped and named, so the check
is honest about how much corroboration it actually got.

Where a package cannot be installed on this machine, its formula is checked by
reading its source instead, which is exact rather than numerical. epiR is in that
position: its dependency chain requires GDAL. Its kappa is

    pE.p    <- sum(r.totals * c.totals) / n^2
    kappa.p <- (pO.p - pE.p) / (1 - pE.p)

and for a 2x2 the first line expands to p_a*p_b + (1-p_a)(1-p_b), which is
expected_agreement here, while pO.p is sum(diag)/n. The formulas are the same, so a
numerical comparison would add nothing to the algebra.

    irr::kappa2            from two columns of ratings
    psych::cohen.kappa     from a table
    epiR::epi.kappa        from a table
    DescTools::CohenKappa  from a table
    vcd::Kappa             from a table
    metafor               (no kappa; conv.2x2 is compared separately)

Written to results/cross_check_kappa.json.
"""
from __future__ import annotations

import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from recover_tables import PROJECT_ROOT, kappa_from_cells

SEED = 20260904
DRAWS = 600

R_SCRIPT = r"""
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1])
have <- function(p) requireNamespace(p, quietly=TRUE)
out <- data.frame(id=d$id)
kap_irr <- kap_psych <- kap_epiR <- kap_desc <- kap_vcd <- rep(NA_real_, nrow(d))
for (i in seq_len(nrow(d))) {
  a <- d$n11[i]; b <- d$n10[i]; c <- d$n01[i]; e <- d$n00[i]
  m <- matrix(c(a, b, c, e), nrow=2, byrow=TRUE)
  if (have("psych")) {
    v <- try(psych::cohen.kappa(m)$kappa, silent=TRUE)
    if (!inherits(v, "try-error")) kap_psych[i] <- as.numeric(v)
  }
  if (have("epiR")) {
    v <- try(epiR::epi.kappa(m, method="fleiss")$kappa$est, silent=TRUE)
    if (!inherits(v, "try-error")) kap_epiR[i] <- as.numeric(v)
  }
  if (have("DescTools")) {
    v <- try(DescTools::CohenKappa(m), silent=TRUE)
    if (!inherits(v, "try-error")) kap_desc[i] <- as.numeric(v)
  }
  if (have("vcd")) {
    v <- try(vcd::Kappa(m)$Unweighted[1], silent=TRUE)
    if (!inherits(v, "try-error")) kap_vcd[i] <- as.numeric(v)
  }
  if (have("irr")) {
    r1 <- c(rep(1, a + b), rep(0, c + e))
    r2 <- c(rep(1, a), rep(0, b), rep(1, c), rep(0, e))
    v <- try(irr::kappa2(cbind(r1, r2))$value, silent=TRUE)
    if (!inherits(v, "try-error")) kap_irr[i] <- as.numeric(v)
  }
}
out$irr <- kap_irr; out$psych <- kap_psych; out$epiR <- kap_epiR
out$DescTools <- kap_desc; out$vcd <- kap_vcd
write.csv(out, args[2], row.names=FALSE)
cat(paste(c("psych","epiR","DescTools","vcd","irr")[
  sapply(c("psych","epiR","DescTools","vcd","irr"), have)], collapse=","))
"""


def draw(rng: random.Random) -> list[tuple[int, int, int, int]]:
    out = []
    while len(out) < DRAWS:
        n = rng.choice([20, 48, 97, 240, 768, 7328])
        n11 = rng.randint(0, n)
        n10 = rng.randint(0, n - n11)
        n01 = rng.randint(0, n - n11 - n10)
        n00 = n - n11 - n10 - n01
        p_a, p_b = (n11 + n10) / n, (n11 + n01) / n
        if p_a in (0.0, 1.0) or p_b in (0.0, 1.0):
            continue                       # kappa undefined; not a disagreement
        if abs(1.0 - (p_a * p_b + (1 - p_a) * (1 - p_b))) < 1e-12:
            continue
        out.append((n11, n10, n01, n00))
    return out


def main() -> int:
    if not shutil.which("Rscript"):
        print("  Rscript not found; skipping"); return 0
    tables = draw(random.Random(SEED))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        (tmp / "x.R").write_text(R_SCRIPT)
        with open(tmp / "in.csv", "w") as f:
            f.write("id,n11,n10,n01,n00\n")
            for i, t in enumerate(tables):
                f.write(f"{i},{t[0]},{t[1]},{t[2]},{t[3]}\n")
        proc = subprocess.run(["Rscript", str(tmp / "x.R"), str(tmp / "in.csv"),
                               str(tmp / "out.csv")], capture_output=True, text=True)
        if proc.returncode != 0:
            print("  R failed:", proc.stderr.strip().splitlines()[-1:]); return 1
        available = [p for p in proc.stdout.strip().split(",") if p]
        import csv as _csv
        rows = list(_csv.DictReader(open(tmp / "out.csv")))

    packages = ["irr", "psych", "epiR", "DescTools", "vcd"]
    worst = {p: 0.0 for p in packages}
    compared = {p: 0 for p in packages}
    for r, t in zip(rows, tables):
        mine = kappa_from_cells(*t)
        for p in packages:
            v = r.get(p, "NA")
            if v in ("NA", "", None):
                continue
            compared[p] += 1
            worst[p] = max(worst[p], abs(float(v) - mine))

    report = {"seed": SEED, "tables": len(tables),
              "available": available,
              "unavailable": [p for p in packages if p not in available],
              "verified_by_source_instead": {
                  "epiR": "kappa.p <- (pO.p - pE.p)/(1 - pE.p) with "
                          "pE.p <- sum(r.totals * c.totals)/n^2; algebraically "
                          "identical for a 2x2. Not run: its dependency chain "
                          "requires GDAL."},
              "largest_absolute_difference": {p: worst[p] for p in packages if compared[p]},
              "tables_compared": {p: compared[p] for p in packages if compared[p]}}
    out = PROJECT_ROOT / "results" / "cross_check_kappa.json"
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"  {len(tables)} integer tables, seed {SEED}")
    for p in packages:
        if compared[p]:
            print(f"    {p:12s} {compared[p]:4d} tables   largest |difference| {worst[p]:.2e}")
        else:
            print(f"    {p:12s}    -   not installed")
    print(f"  written to {out.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
