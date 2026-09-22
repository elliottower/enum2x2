# Changelog

## Unreleased

### Added
- `mcnemar`, accepting a printed p as either a point value (`"0.0002"`) or a bound
  (`"<0.001"`), with `mcnemar_test` selecting `exact` (default), `chisq` or `chisq_cc`.
  McNemar depends only on the two discordant cells and the marginals already fix their
  difference, so a printed McNemar result closes the table.
- `discordant`, the printed count of cases the two criteria classify differently.
- Further closing statistics, each exact: `positive_agreement`, `negative_agreement`
  (specific agreement, not the FDA's PPA and NPA), `jaccard`, `pabak`,
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
- `phi`, the phi coefficient as printed. It is decided exactly through its square with
  the sign kept, so +0.60 and -0.60 identify different tables.

### Fixed
- An empty candidate set reached with a closing figure other than kappa -- agreement,
  a discordant count, McNemar or any further statistic -- raised `TypeError` instead of
  returning `infeasible`.
- The `infeasible` reason no longer blames the published agreement when another figure
  is the one that excludes: the agreement is dropped alone and every other figure kept.
- `recover_many` and the command line dropped the further statistics (`pabak`,
  `scott_pi` and the rest) from each row, so a row giving only one of them was reported
  as insufficient.
- McNemar with continuity correction applied the correction to a symmetric table,
  giving it a smaller p than a table with a difference of one. It now follows R's
  `mcnemar.test`: no correction when the two discordant cells are equal.
- A malformed printed figure among the further statistics, or a McNemar p that is not a
  number, raised a raw `decimal.InvalidOperation`; it now raises `InvalidInput`.
- Printing an `impossible` result from `recover_many` raised instead of showing the
  reason.
- A printed figure outside the values it can take (agreement above 1, a negative
  odds ratio, a p above 1) now raises `InvalidInput` whatever else the call contains,
  where before it could return `infeasible`, `insufficient` or raise `TypeError`.
- A McNemar p printed as `p<0.001`, `P < 0.001`, `p≤0.001` or `p = 0.03` is read as
  the comparison and number it states.
- The command line read `discordant` as text, so every row giving it was rejected, and
  truncated a fractional count to an integer; a fractional count is now rejected.

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
