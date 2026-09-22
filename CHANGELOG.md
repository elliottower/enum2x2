# Changelog

## Unreleased

### Added
- `mcnemar`, accepting a printed p as either a point value (`"0.0002"`) or a bound
  (`"<0.001"`), with `mcnemar_test` selecting `exact` (default), `chisq` or `chisq_cc`.
  McNemar depends only on the two discordant cells and the marginals already fix their
  difference, so a printed McNemar result closes the table.
- `discordant`, the printed count of cases the two criteria classify differently.
- Nine further closing statistics, each exact: `ppa`, `npa`, `jaccard`, `pabak`,
  `scott_pi`, `gwet_ac1`, `prevalence_index`, `bias_index`, `odds_ratio`,
  `mcnemar_odds_ratio`, `phi_squared`.
- `Table.n_discordant` and `Table.mcnemar(test=...)`.
- `convention`, on `recover()` and on the interval functions, saying how the source
  produced its printed digits: `half_up` (the default, unchanged), `truncate`, or
  `any` for the union of the two. Sources truncate without saying so, and a figure
  that could only have been truncated lies outside the half-up interval, so the
  table that produced it is excluded and the comparison reports no compatible table
  at all. Of the 55 pairwise comparisons in Goyal et al. 2025, 15 have disagreement
  percentages a rounding source could not have printed; all 55 are recovered under
  `any` against 40 under `half_up`.
- `CONVENTIONS`, the three names.

### Changed
- Any one closing statistic now suffices. Observed agreement alone determines the table
  and the package previously demanded kappa alongside it; that was a limitation, not a
  requirement of the arithmetic.
- The `insufficient` reason names every accepted statistic rather than kappa alone.
- An `infeasible` result whose printed marginal admits no integer count at all says
  so, rather than reporting that the marginals permit the kappa but no table attains
  it. A percentage finer than 1/N has no matching count, which is routine where a
  source truncates.


## 0.1.0

First release.

- `recover()` enumerates every integer 2x2 table whose statistics round back to
  the digits a source printed, given a sample size, both positive marginals and
  Cohen's kappa. Membership is decided in exact rational arithmetic; there is no
  tolerance parameter.
- Outcomes are reported as unique, set-identified, infeasible, or insufficient
  inputs, so a source whose published figures admit no common table is
  distinguished from one whose rounding leaves several.
- `kappa_max`, `kappa_min`, `expected_agreement`, `kappa_from_cells` and
  `rounding_interval` are exposed for use on their own.
- Command line: `enum2x2 comparisons.csv`, reading a table of published
  comparisons and writing the recovered tables as CSV or JSON.
