# criterion-table-recovery

Recovering the joint classification table from a published agreement statistic.

A study comparing two diagnostic criteria on one population computes its statistics from a
2×2 table and then, usually, publishes the statistics instead of the table. The quantity a
reader wants — how many patients each criterion classifies differently, and in which
direction — is not recoverable from a scalar. It is often recoverable from the scalar plus
the two marginals and the sample size, all of which the same reports do print.

1. **Rounding is a constraint, not noise.** A marginal printed as `4.26%` and a κ printed as
   `0.22` stand for intervals. The inputs therefore identify a *set* of integer tables, and
   this returns the set rather than a point inside it.
2. **Four outcomes, kept apart.** *Uniquely identified*, *set-identified*, *infeasible* —
   the published figures admit no common table — and *insufficiently reported*. Collapsing
   the last two would report a gap in the record as a defect in the source.
3. **Validated two ways.** Five of the nine comparisons come from sources that print their
   own cells; the reconstruction runs from the summaries alone and must return those cells.
   And the enumerator must agree, as a set, with a second implementation written from the
   definitions in exact rational arithmetic that shares no code with it.
4. **An empty set is not an error found.** It says the published figures admit no common
   table under the definitions and rounding rules used here. A denominator, an analysis set
   or a version of a variable may have gone unstated.

```bash
make test        # 32 tests, including an exhaustive sweep at N = 16, 18, 20, 22, 24
make recover     # enumerate; writes results/recovery.json
make diagnose    # why one comparison admits no table; writes results/daghi_diagnosis.json
make compare     # against metafor::conv.2x2; needs R, skips cleanly without it
```

Standard library only. No dependencies beyond Python 3.10+; `make test` uses `pytest`,
`make compare` uses R with `metafor` and skips with a message if either is absent.

## What is here

| path | |
|---|---|
| `scripts/recover_tables.py` | the enumeration |
| `scripts/daghi_diagnosis.py` | which published figure excludes a table, where none survives |
| `scripts/compare_conv2x2.py` | point reconstruction against set identification, under rounding |
| `tests/` | including the independent reimplementation |
| `experiments/table_recovery/PREREG.md` | the plan, frozen before the enumeration ran, with its deviation log |
| `experiments/table_recovery/inputs.json` | every published figure used, with the sentence it was read from |
| `results/` | what the scripts wrote |
| `docs/SOURCES.md` | each source article by sha256 of the text it was read from |

## The identity

For a binary comparison with positive marginals p_A and p_B on N observations,

    p_e  = p_A·p_B + (1 − p_A)(1 − p_B)
    p_o  = κ(1 − p_e) + p_e
    p_11 = (p_o + p_A + p_B − 1) / 2

so exact inputs determine the table. Published inputs are rounded, and the enumeration walks
every non-negative integer table summing to N whose statistics round back to the printed
strings. Where a source also prints raw agreement, a sensitivity, a specificity, or the cells
themselves, those enter as further constraints.

## Registration

`experiments/table_recovery/PREREG.md` was frozen before the enumeration was run and records
what had already been read, which rows were expected to recover, and every subsequent
deviation. It is a `prereg` plan; the tool is not required to read it.

## Relation to existing work

`metafor::conv.2x2` reconstructs 2×2 cells from a sample size, both marginals and one further
statistic — an odds ratio, a phi coefficient, or a chi-square — and states that its
calculations "are exact only for unrounded values" and that minimising the discrepancy "is not
guaranteed to reconstruct the actual table exactly". `make compare` measures what that costs
at the sample sizes this corpus contains. Cohen's κ is not among its inputs.

The consistency-testing lineage is GRIM, GRIMMER, SPRITE and `statcheck`, which ask whether
reported statistics can have arisen from any common dataset at all.

## License

MIT.
