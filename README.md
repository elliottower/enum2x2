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
git clone https://github.com/elliottower/enum2x2 && cd enum2x2 && pip install -e .
```

Standard library only. Python 3.10+. `make compare` and `make crosscheck` need R and skip
cleanly without it.

## Use

```python
import enum2x2

r = enum2x2.recover(768, n_a=158, n_b=466, kappa="0.29")
r                     # <Recovery unique on N=768: Table(158, 0, 308, 302)>
r.status              # 'unique'
r.table.discordant    # (0, 308)   -- 308 patients one way, none the other
r.table.asymmetry     # 1.0

r = enum2x2.recover(20306, n_a=866, n_b=1603, kappa="0.22")
r                     # <Recovery 11 tables on N=20306: 320-330/536-546/...>
r.cell_ranges["n10"]  # (536, 546)

r = enum2x2.recover(370, n_a=165, n_b=160, kappa="0.48",
                    agreement="73", agreement_as_percent=True)
r.status              # 'infeasible'
r.reason              # 'the marginals and kappa admit 1 table(s); adding the
                      #  published agreement admits none'
```

**κ is passed as the string the source printed**, not as a float: `"0.10"` and `"0.1"`
imply different intervals and a float cannot tell them apart. Passing a float is refused
with that reason.

Four statuses, and they are kept apart: `unique`, `set`, `infeasible` (the published
figures admit no common table), `insufficient` (a required figure was never published).
An impossible *call* — a marginal above N, a κ outside [-1, 1], two marginals given for
one criterion — raises `InvalidInput`. An impossible *source* is reported, never raised.

`recover_many` cannot raise, so it carries a fifth status, `impossible`, for a row whose
figures could not describe any table. Counting those as `insufficient` would inflate how
many sources under-reported.

```bash
enum2x2 comparisons.csv       # a file of comparisons, one per row
make test                     # 62 tests
make compare                  # against metafor::conv.2x2, under rounding
make crosscheck               # this kappa against every R implementation installed
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

1. **Exhaustively, over the whole space.** The enumerator must agree, as a *set*, with a
   brute-force sweep over every integer table at N = 18 and N = 22 — 1,258 and 2,212 tables.
   Not a sample of them.
2. **Against a second implementation.** Written from the definitions in exact rational
   arithmetic, sharing no code with the enumerator, over every table at N = 16, 20 and 24.
   Agreement between two implementations that share helpers proves only that the helpers are
   consistent.
   Those sweeps run at small N, where the granularity of κ and of the marginals is coarser
   than the interval arithmetic being checked, so the rounding boundaries are stated as
   concrete cases instead: a κ of exactly 0.625 sitting on the endpoint of `"0.62"`, and a
   marginal printed `"0.512"` at N = 240 whose only valid count is lost to truncation.
3. **Against the established R implementations of κ itself.** The enumeration is only as
   good as the statistic it inverts, so `make crosscheck` computes κ for 600 integer tables
   with this module and with every R implementation present on the machine, and reports the
   largest disagreement. Against `irr::kappa2`, `psych::cohen.kappa`, `vcd::Kappa` and
   `DescTools::CohenKappa` the worst disagreement is 6 × 10⁻¹⁵ — floating-point
   representation, not arithmetic. `epiR::epi.kappa` cannot be installed here (its
   dependency chain wants GDAL) and is checked against its source instead, which is exact:
   its `(pO.p - pE.p)/(1 - pE.p)` with `pE.p <- sum(r.totals * c.totals)/n^2` is the same
   formula. Packages that are absent are named rather than silently skipped.

## The study this was built for

The delirium table above, and eight other published comparisons, are analysed in a
manuscript on what a published agreement statistic conceals. That work lives in its own
repository, with the corpus, the preregistration frozen before the enumeration was run, the
results, and the sentence each published figure was read from. This package carries only the
method.

## Citation

See `CITATION.cff`.

## License

MIT.
