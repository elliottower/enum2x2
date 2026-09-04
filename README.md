# enum2x2

**Every 2×2 table a published summary statistic still allows.**

A study comparing two diagnostic criteria on one population computes its numbers from a
2×2 table, then publishes the numbers and not the table. The quantity a reader wants —
how many patients the two criteria classify differently, and *in which direction* — is
gone. It is usually still recoverable, because the same reports print the sample size and
both marginal totals, and those pin the table down.

## The problem, concretely

A pooled series of 768 patients, two readings of the DSM-5 delirium criteria, published as
**κ = 0.29**. That reads like two definitions that disagree a fair amount.

Here is the table underneath it:

|  | relaxed + | relaxed − |
|---|---:|---:|
| **strict +** | 158 | 0 |
| **strict −** | 308 | 302 |

They never disagree about a patient. Every patient the strict reading calls delirious, the
relaxed reading calls delirious too. One is simply three times wider: 308 people change
status in one direction and **zero** change back. Observed agreement is the highest these
two marginals permit — κ = 0.29 *is* the ceiling here, not a shortfall from it.

None of that is in "κ = 0.29", and κ = 0.29 is all the paper printed.

## Install

```bash
pip install enum2x2          # not yet on PyPI; for now:
git clone https://github.com/elliottower/enum2x2 && cd enum2x2
```

Standard library only. Python 3.10+. `make test` needs `pytest`; `make compare` needs R with
`metafor` and skips cleanly without it.

## Use

```bash
make recover      # enumerate every comparison in experiments/table_recovery/inputs.json
make diagnose     # why one comparison admits no table at all
make compare      # against metafor::conv.2x2, under rounding
make crosscheck   # our kappa against every R implementation installed
make test         # 32 tests
```

## Why rounding is the whole problem

With exact inputs the algebra is one line. For positive marginals p_A and p_B on N
observations,

    p_e  = p_A·p_B + (1 − p_A)(1 − p_B)
    p_o  = κ(1 − p_e) + p_e
    p_11 = (p_o + p_A + p_B − 1) / 2

But nobody prints exact inputs. A marginal printed `4.26%` and a κ printed `0.22` are
*intervals*, so the inputs identify a **set** of integer tables. This walks every
non-negative integer table summing to N whose statistics round back to the printed strings,
and reports the set. Where a source also prints raw agreement, a sensitivity, a specificity
or the cells themselves, those enter as further constraints and narrow it.

Four outcomes, deliberately kept apart:

| | |
|---|---|
| **uniquely identified** | one table survives — you know the answer exactly |
| **set-identified** | several do; cell ranges are reported across them |
| **infeasible** | none does; the published figures admit no common table |
| **insufficiently reported** | a required input was never published |

The last two are different findings and collapsing them would report a gap in the record as
a defect in the source.

## Against `metafor::conv.2x2`

`conv.2x2` **conv**erts a summary into a single table. This **enum**erates every table the
summary admits. The names are meant to sit next to each other.

It takes an odds ratio, a phi coefficient or a chi-square — not Cohen's κ, which is what
agreement studies report — and on rounding its documentation is candid:

> The calculations underlying the function are exact only for unrounded values … The present
> function uses optimization methods to reconstruct the table counts so that the discrepancy
> between the reported measures and the reconstructed ones are minimized. **This is not
> guaranteed to reconstruct the actual table exactly**, but should usually yield a close match.

`make compare` measures what "close" costs. On 1,200 known tables at N = 2,000, 9,170 and
20,306 with one statistic printed to two decimals — the sizes real papers actually report at:

| | `conv.2x2` point estimate | `enum2x2` |
|---|---|---|
| exactly right | **21.8%** | — |
| contains the true table | — | **100%** |
| largest cell error | median 2, 90th pct 8, **max 20** | — |
| uncertainty reported | none | the range itself |

`conv.2x2` is not broken; it does what it says. But it hands you one table and no indication
of how far off it is. When the claim is "540 patients were reclassified one way," an unstated
error of up to 20 patients *is* the claim.

## What it will not do

- It does not tell you which criterion is **correct**. Neither does the table.
- It does not separate disagreement *between* criteria from inconsistent *application* of
  either. That needs the same criterion applied twice to the same patients, which no
  aggregate report contains.
- An empty candidate set says the published figures admit no common table **under the
  definitions and rounding rules used here**. It does not say an error was made — a
  denominator, an analysis set, or a version of a variable may simply have gone unstated.
- Three or more categories are out of scope; the identity above is the binary case.

## Validation

1. **Against sources that print their own cells.** Five of the nine comparisons come from
   papers that published the table as well as the statistics. The reconstruction runs from
   the statistics alone and must return those cells. All five do.
2. **Exhaustively, over the whole space.** The enumerator must agree, as a *set*, with a
   brute-force sweep over every integer table at N = 18 and N = 22 — 1,258 and 2,212 tables.
   Not a sample of them.
3. **Against a second implementation.** Written from the definitions in exact rational
   arithmetic, sharing no code with the enumerator, over every table at N = 16, 20 and 24.
   Agreement between two implementations that share helpers proves only that the helpers are
   consistent.
4. **Against the established R implementations of κ itself.** The enumeration is only as
   good as the statistic it inverts, so `make crosscheck` computes κ for 600 integer tables
   with this module and with every R implementation present on the machine, and reports the
   largest disagreement. Against `irr::kappa2`, `psych::cohen.kappa`, `vcd::Kappa` and
   `DescTools::CohenKappa` the worst disagreement is 6 × 10⁻¹⁵ — floating-point
   representation, not arithmetic. `epiR::epi.kappa` cannot be installed here (its
   dependency chain wants GDAL) and is checked against its source instead, which is exact:
   its `(pO.p - pE.p)/(1 - pE.p)` with `pE.p <- sum(r.totals * c.totals)/n^2` is the same
   formula. Packages that are absent are named rather than silently skipped.

## Provenance

`experiments/table_recovery/PREREG.md` was frozen before the enumeration was ever run, and
records what had already been read, which rows were expected to recover, and every later
deviation. `experiments/table_recovery/inputs.json` carries, for every figure used, the
sentence it was read from. `docs/SOURCES.md` identifies each source article by the sha256 of
the text extraction its figures were read from; the articles themselves are not
redistributed.

## Citation

See `CITATION.cff`.

## License

MIT.
