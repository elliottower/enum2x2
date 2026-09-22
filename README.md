# enum2x2

**Every 2×2 table a published summary statistic still allows.**

[![PyPI](https://img.shields.io/pypi/v/enum2x2)](https://pypi.org/project/enum2x2/)
[![Tests](https://github.com/elliottower/enum2x2/actions/workflows/test.yml/badge.svg)](https://github.com/elliottower/enum2x2/actions/workflows/test.yml)
[![Python](https://img.shields.io/pypi/pyversions/enum2x2)](https://pypi.org/project/enum2x2/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

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

They never cross-classify. No patient is strict-positive and relaxed-negative; the 308 they
differ on all fall the same way, relaxed-positive and strict-negative. One reading is simply
three times wider than the other. Observed agreement is the highest these
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

### What can close the table

A 2×2 with N fixed has three degrees of freedom and the two marginals use two, so
**one** further quantity closes it. Any of these will do, and each is passed as the string
the source printed:

```python
enum2x2.recover(113, n_a=39, n_b=83, kappa="0.32")        # agreement coefficient
enum2x2.recover(113, n_a=39, n_b=83, agreement="0.61")    # raw observed agreement
enum2x2.recover(113, n_a=39, n_b=83, mcnemar="<0.001")    # a printed McNemar result
enum2x2.recover(113, n_a=39, n_b=83, discordant=44)       # the discordant total itself
enum2x2.recover(113, n_a=39, n_b=83, ppa="0.64")          # positive agreement
```

| input | what it is | notes |
|---|---|---|
| `kappa` | Cohen's κ | |
| `agreement` | observed agreement, (n11+n00)/N | `agreement_as_percent` for "61" |
| `mcnemar` | a printed p, point (`"0.0002"`) or bound (`"<0.001"`) | `mcnemar_test`: `exact` (default), `chisq`, `chisq_cc` |
| `discordant` | n10 + n01, the count classified differently | an integer, not a string |
| `ppa` / `npa` | positive / negative agreement | the FDA's concordance measures |
| `jaccard` | overlap among cases either criterion identifies | ignores n00 |
| `pabak` | prevalence-adjusted bias-adjusted κ | |
| `scott_pi` / `gwet_ac1` | Scott's π, Gwet's AC1 | proposed where κ's prevalence dependence bites |
| `prevalence_index` / `bias_index` | Byrt's indices | `bias_index` is fixed by the marginals, so it closes nothing alone |
| `odds_ratio` / `mcnemar_odds_ratio` | cross-product, and the paired n10/n01 | |
| `phi_squared` | φ², squared because φ is generally irrational | |

**McNemar is the one worth spelling out.** It looks only at the two discordant cells, and
the marginals already fix their *difference*, so the statistic fixes their *sum* and the
table follows. A paper printing a McNemar result printed the table without saying so. The
exact (binomial) variant is a ratio of integers and is decided exactly; the chi-square
variants compute a tail probability that is not rational, and say so.

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
make test                     # 147 tests
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
and reports the set. Where a source also prints its raw agreement, that enters as a further constraint and
narrows the set.

### Rounding conventions

Which interval a printed figure stands for depends on how the source got from the exact
value to the digits. The default reading is round-half-up, so `14.7` stands for
[14.65, 14.75]. A source that truncates prints `14.7` for everything in [14.7, 14.8),
which shares only its lower end with the first.

| `convention` | a printed `p` means | |
|---|---|---|
| `half_up` | [p − u/2, p + u/2] | the default; closed at both ends, because the tie rule is not stated either |
| `truncate` | [p, p + u) | the digits dropped and the sign kept |
| `any` | the union of the two | cannot drop a table either convention admits |

`u` is one unit in the last printed place, read off the literal string, so `"3.3"` and
`"3.30"` differ here as they do everywhere else.

```python
enum2x2.recover(353, n_a=84, n_b=46, kappa="0.648", convention="any")
```

Goyal et al. (2025) print a kappa and a disagreement percentage for each of the 55
pairwise comparisons of eleven gestational-diabetes criteria on 353 women. Held against
the table its own kappa identifies, each printed disagreement is consistent with either
convention (33 of them), with truncation alone (15), or with rounding alone (7). Read as
rounded throughout, 15 of the 55 comparisons return no compatible table; under `any` all
55 are uniquely identified.

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

## Where this sits among neighbouring packages

| package | direction | framing | takes | returns |
|---|---|---|---|---|
| `metafor::conv.2x2` | reverse | unpaired, group × outcome | OR, φ, χ², sens/spec/PPV/NPV | one table, by optimization |
| `irr`, `psych` | forward | paired agreement | raw ratings | κ, π, AC1, Bhapkar, Stuart–Maxwell |
| `exact2x2`, `DTComPair` | forward | paired | raw counts | tests and intervals |
| `scrutiny` (GRIM, GRIMMER, DEBIT) | reverse | means, SDs, binary means | reported summaries | whether the summary is attainable |
| **`enum2x2`** | **reverse** | **paired agreement** | **κ, agreement, McNemar, and the rest above** | **every table the figures admit** |

Nothing else runs the paired-agreement framing backwards, and nothing else reports a *set*.
`scrutiny` is the closest in spirit — it asks what could have produced a printed number —
but it asks it of means and standard deviations rather than of a table.

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
   brute-force sweep over every non-degenerate integer table at N = 18 and N = 22 — 1,258
   and 2,212 of them, being every table for which κ is defined. Not a sample.
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
