# What can be recovered from a published agreement statistic?

**Status:** FROZEN at `a9094a841bd1`
**Plan sha256:** `aaf0eb45ac1dfca1c505998d60da98a997845684c534122237113849f8d86a41`
**Log:** 6 entries, head `36bf72fe`
**Frozen:** 2026-09-04

Sections use the [OSF Preregistration](https://osf.io/prereg/) question titles verbatim, so
this maps onto a registration without being rewritten. A question that does not apply is
answered **N/A** with the reason, never deleted.

## Research questions or hypotheses

Studies comparing two diagnostic criteria on one population report a
chance-corrected agreement statistic, an accuracy statistic, or both, and most
report no contingency table. A reader who wants the quantity that bears on
practice --- how many patients are classified differently, and in which
direction --- generally cannot find it. This study asks how much of that is
recoverable from what such papers already print.

For a binary comparison with positive marginals $p_A$ and $p_B$ and Cohen's
$\kappa$ on a population of size $N$, the joint table is determined:

    p_e  = p_A p_B + (1 - p_A)(1 - p_B)
    p_o  = kappa (1 - p_e) + p_e
    p_11 = (p_o + p_A + p_B - 1) / 2

**H1.** For at least eight of the sixteen comparisons assembled in
`paper/criterion_agreement_v5.tex`, the source publishes $N$, both marginals and
$\kappa$, and the reconstructed table reproduces the published $\kappa$ to the
precision the source states.

**H2.** Among recovered tables, directional discordance is asymmetric --- the two
off-diagonal proportions differ by more than a factor of two --- in at least half
of them, so that which criterion expands caseness is a fact the published
statistic conceals.

**H3.** For at least half of the recovered tables, $\kappa_{\max}$ under the
observed marginals is below 0.9, so the reported $\kappa$ was bounded away from
1 by marginal incompatibility before any disagreement about patients arose.

H1 carries the design. If fewer than eight recover, the paper reports a smaller
finding --- that published aggregate reports rarely permit even descriptive
reconstruction --- and H2 and H3 are not evaluated.

## Foreknowledge of data or evidence

Substantial, and stated. The sixteen comparisons were assembled before this
plan and appear in `criterion_agreement_v5.tex`. Every published $\kappa$ is
already known and quoted. Reading the sources during assembly established that
`guerra2026` prints its 2x2 outright (326 / 540 / 1277 / 18163 on N = 20,306),
that `westbury2023`, `meagher2014`, `daghi2026` and `heianza2012` print $N$ with
both marginals, that `mana2026` ships its pairwise table as an R package, and
that `zhu2016`, `mahmoudi2026` and `zhang2019` do not print marginals in the
retrieved text.

That foreknowledge sets H1's threshold at eight rather than at a number chosen
to be safe: nine binary rows are believed recoverable, so eight is a threshold
the expectation can fail. No recovery has been computed. No discordance or
$\kappa_{\max}$ value has been computed for any row, so H2 and H3 are
uninformed by the data.

## Explanation of foreknowledge and managing unintended influences

The analysis is algebra with no free parameters: given $N$, both marginals and
$\kappa$, the table is determined. There is no model to select and no threshold
to tune, so the ordinary p-hacking channel is absent. The degree of freedom that
does exist is which rows enter, and the inclusion rule below is fixed here
before any recovery is run.

## Study type

Secondary analysis of published aggregate statistics. No human subjects, no new data collection.

## Intention for causal interpretation

N/A --- nothing causal is claimed; the quantities are descriptive properties of published tables.

## Blinding of experimental treatments

N/A --- no treatment is administered.

## Additional blinding during research or analysis

N/A --- the inputs are published numbers already read and quoted in the manuscript.

## Study design

Each eligible comparison is one unit. For each, the published $N$, both
positive marginals and $\kappa$ are entered from the stored source artifact, the
table is reconstructed by the identity above, and the reconstruction is checked
by recomputing $\kappa$ from the reconstructed cells.

## Randomization

N/A --- no assignment.

## Data collection procedures

Inputs are read from the artifacts already pinned in
`reference/FETCH_LOG.json` and stored in the shared citations library, each with
a sha256. No new retrieval is performed. Where a source reports marginals as
percentages, the percentage is used as printed and the implied count is reported
alongside.

## Data collection procedures - File upload

N/A.

## Sample size

Sixteen comparisons across eight conditions, thirteen of them binary. Of the thirteen, nine are believed to publish the required inputs.

## Sample size rationale

The corpus is fixed by the manuscript and is not a sample. It is a purposive
series located without a protocol, and no population parameter is estimated from
it. The design can show that recovery is possible and how often; it cannot
estimate how often recovery would be possible across the diagnostic literature.

## Starting and stopping rules

All eligible rows are attempted in one pass. No row is added or removed after results are seen.

## Manipulated variables

N/A --- observational.

## Measured variables

Per recovered table: the four cell counts; raw agreement $p_o$; total
discordance $1 - p_o$; directional discordance $n_{10}/N$ and $n_{01}/N$
separately; $\kappa_{\max}$ and $\kappa / \kappa_{\max}$ under the observed
marginals; and the residual between the recomputed and published $\kappa$.

## Measured variables - File upload

N/A.

## Indices

$\kappa_{\max} = (p_{o,\max} - p_e)/(1 - p_e)$ with
$p_{o,\max} = \min(p_A,p_B) + \min(1-p_A, 1-p_B)$, reported as a marginal
diagnostic and never as a reliability correction.

## Indices - File upload

N/A.

## Statistical models

None. The recovery is an algebraic identity, not an estimator. No latent
model is fitted, no disattenuation is applied, and no quantity requiring
patient-level or repeated data is computed.

## Statistical models - File upload

N/A.

## Transformations

Percentages are converted to proportions. Cell counts are reported both as the exact real-valued solution and rounded to integers, with the rounding residual stated.

## Inference criteria

| hypothesis | holds when |
|---|---|
| H1 | at least 8 of 16 comparisons recover, where recovery means the reconstructed table reproduces the published $\kappa$ to the decimal places the source prints |
| H2 | among recovered tables, $\max(n_{10},n_{01}) / \min(n_{10},n_{01}) > 2$ in at least half |
| H3 | among recovered tables, $\kappa_{\max} < 0.9$ in at least half |

**H2 and H3 are void if H1 fails.** A finding about recovered tables requires
enough of them to be a finding rather than an anecdote.

A row whose reconstruction does not reproduce the published $\kappa$ is reported
as a failure with its residual. It is not dropped, and no alternative input is
substituted to make it close.

## Data inclusion and exclusion

Included: any comparison in Table 3 of `criterion_agreement_v5.tex` whose
source publishes $N$, both positive marginals, and $\kappa$, or publishes the
contingency table directly.

Excluded, and marked *not attempted* rather than missing: comparisons with three
or more categories, because the identity above is stated for the binary case;
and comparisons whose source does not publish both marginals in the retrieved
artifact.

## Missing data

No imputation. A source that does not print an input yields no recovery for that row.

## Other planned analysis

None. Any further quantity computed after this freeze is reported as post hoc and logged below.

## Context and additional information

This replaces a deleted analysis. Earlier drafts applied Spearman's correction
for attenuation to a criterion-level $\kappa$ using a rater-level $\kappa$ from
a different study, and reported corrected values. That correction is derived for
the product-moment correlation under classical test theory and $\kappa$ meets
neither condition, and the two inputs came from different populations. Nothing
in this plan reinstates it.

The plan registers an outcome that would strengthen the reporting practice it
examines: if most sources publish enough to permit recovery, then the
information a reader needs is already being collected and only the reporting
convention withholds it, which is a smaller problem than the paper currently
describes and should be reported as such.

## Log

---

## Log

```
2026-09-04  frozen at a9094a841bd1                nothing run  ·d1a82e84
2026-09-04  Deviation, before any run. The plan describes recovering one table and checking it reproduces the published kappa within that kappa's printed precision. That treats a set-identification problem as point estimation: published figures are rounded, and an interval of inputs is compatible with a set of integer tables, not one. The method now enumerates every integer table whose marginals and kappa round back to the published strings, and reports unique / set_identified / infeasible / insufficient_inputs. H1's threshold of eight is unchanged but now counts rows reaching unique or set_identified. Two implementation faults found and fixed before running: precision was being inferred from a Python float, which cannot distinguish 0.10 from 0.100; and rounding intervals were half-open, which drops a true table whose statistic falls exactly on a boundary rounded by a convention the source does not state. Intervals are now closed at both ends, which can only widen a reported set.  no results seen  ·6ed8374c
2026-09-04  Amendment, before any run, following a second design review. Three changes. (1) H1's denominator was all sixteen comparisons, which made the hypothesis partly a test of how many rows were ineligible by construction rather than of whether recovery works. The denominator is now the eligible binary comparisons, where eligibility is fixed before results are seen and requires: a binary comparison, N reported, both marginals reported, unweighted Cohen kappa, printed precision recoverable, and denominator_status explicit_same or inferred. On the current inputs that denominator is three, so H1's threshold of eight is unreachable until the source-reading pass adds rows; the threshold does not move to meet the data. (2) H2 defined asymmetry as a ratio of the two discordant cells, which is undefined when one is zero and unstable when both are small. It is now the normalised difference D = |n10 - n01| / (n10 + n01), defined when total discordance exceeds zero, and asymmetry means D > 1/3, which is the ratio-of-two threshold expressed on a bounded scale. (3) H3's reading was that kappa_max below 0.9 shows kappa was bounded away from 1 before any disagreement about patients. That is too strong: the marginals are produced by the classifications, so their incompatibility is itself criterion disagreement. kappa_max separates disagreement forced by different positive totals from disagreement about which patients occupy them, and H3 is now read that way.  no results seen  ·1bda3587
2026-09-04  Implementation change and source-reading pass, before any run. Data collection procedures requires a marginal to be used as printed, but the implementation accepted only a printed percentage, so a source printing an exact count had to be re-expressed as a percentage and its rounding interval widened to admit counts the source excludes. Declaring heianza2012's JDS marginal as '2.1' admits 151 to 157 where the source prints 153. Marginals may now be declared as exact counts (n_A, n_B) and are then used verbatim; percentage declarations are unchanged. Five tests added, including one requiring that a printed count identify what a printed percentage leaves open, and one requiring the two declaration forms to agree wherever the percentage pins a single count. The source-reading pass this gates raised the eligible denominator from three to nine: meagher2014 prints all four cells for two of its three pairs in its Results text and both marginals for the third, and heianza2012 prints its full 2x2 for two pairs in Table 2 and both marginals for the third in the same table. H1's threshold of eight is unchanged and is now reachable and falsifiable, which it was not at a denominator of three. Every published figure entered was first checked for internal consistency: all six known tables sum to N and reproduce every statistic their source printed, and all three marginals-only rows carry a kappa inside the range their marginals permit, so no row is entered over a source's own arithmetic error.  no results seen  ·47f1d651
2026-09-04  Post hoc, after the registered run. Eight of nine eligible rows recovered (six unique, two set-identified), so H1 holds at its registered threshold of eight. All five self-test rows returned their published cells inside the candidate set. One row, daghi2026, returned the empty set: no integer table reproduces N, both published marginals and kappa together, and the marginals do permit that kappa, so the failure is not a marginal-range violation. Diagnosing it used two figures the plan does not register, sensitivity and specificity, and is reported as post hoc in scripts/daghi_diagnosis.py and results/daghi_diagnosis.json. The source publishes, for the same comparison, N = 370, a neurologist prevalence of 43.2%, sensitivity 95.6%, specificity 55.2%, raw agreement 73% and kappa 0.48. Those six are mutually consistent and determine the single table 153/94/7/116, which reproduces the printed agreement and kappa to their printed precision; the same construction reproduces the paper's other two criterion combinations exactly (87% with kappa 0.73, and 84% with kappa 0.66), so the construction is not misfiring on this source. That table gives a 5-2-1 prevalence of 66.8%, or 247 of 370. The paper prints 44.6%, or 165 of 370, twice and with a confidence interval consistent with its own value. The registered inputs for this row therefore contain one figure that the source's other five contradict. No input was substituted to make the row close, and the row is reported as a recovery failure with this diagnosis attached, per the plan's rule that a row failing to reproduce its published kappa is reported rather than dropped.  results seen  ·fff2f7c5
2026-09-04  Corrections after two independent adversarial reviews, both run after the first pass. Six faults found and fixed, then the analysis was re-run. (1) The reason attached to an empty candidate set ignored every optional constraint, so daghi2026 was reported as a kappa no integer table attains. Dropping only the published raw agreement admits the table 115/50/45/160, whose kappa prints as 0.48; the excluding figure is the raw agreement, whose value there is 74.3% against a printed 73%. The reason now drops each optional figure in turn and names the one whose removal admits a table. This mattered because the string was attached to a claim about another group's paper. (2) A candidate marginal pair whose expected agreement is exactly 1 raised an uncaught exception and abandoned the row rather than contributing no table; any source printing a zero prevalence would have aborted the run. (3) The completeness test asserted set equality between the enumerator and a brute-force sweep, but stopped after sixty tables taken in iteration order, which is 4.8% of the space at N=18 and 2.7% at N=22, and every table it reached had no concordant positives. The bound is removed and the test now covers all 1258 and 2212 non-degenerate tables; it is what would have caught fault 2, and two regression tests were added for faults 1 and 2. (4) guerra2026 publishes no agreement statistic of any kind, reporting sensitivity, specificity, predictive values, accuracy and a C-index against the neurologist's definition, which it nominates as the reference. The kappa entered for that row was computed by this analysis from the cells being recovered, so its self-test is circular and is now reported as such. The row is retained, since the plan forbids removing a row after results are seen. (5) guerra2026 and westbury2023 both print exact counts alongside their percentages, and entering the percentages widened their intervals against the rule that a marginal is used as printed; entering the counts moves guerra from 47 candidates to 11 and westbury from 102 to a unique table. (6) The eligibility gate never fired, because every row reaching it had already been hand-marked in the inputs, so the reported eligible denominator restated the hand marking. The gate now runs over every row and reports where it disagrees with the marking; it currently disagrees nowhere. After the re-run: eight of nine eligible rows recover, seven of them uniquely, so H1 holds at its registered threshold of eight; H2 holds with asymmetry above one third in four of eight; H3 holds with kappa_max below 0.9 in five of eight. The daghi2026 diagnosis was also strengthened: every one of the 369 possible reference totals was scanned, and only the clinician total of 160 reproduces all three of the source's printed rows, so the direction of the diagnosis is forced by the published figures rather than assumed, and the mirrored reading that would impeach the clinician prevalence instead is arithmetically unavailable.  results seen  ·36bf72fe
```
