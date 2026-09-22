# Changelog

## 0.1.0

First public release.

- `recover()` enumerates every integer 2x2 table whose statistics round back to the
  digits a source printed, given a sample size, both positive marginals (as exact counts,
  or as printed proportions or percentages) and at least one closing statistic.
  Membership is decided in exact rational arithmetic; there is no tolerance parameter.
- Closing statistics, each exact where the statistic is rational:
  - Cohen's `kappa`;
  - `phi` as printed, sign included, decided through its square with the sign kept;
  - observed `agreement`;
  - a printed McNemar p, as a point value or a bound. `mcnemar_test` selects `exact`,
    `midp`, `chisq` or `chisq_cc`, and the last follows R's `mcnemar.test`;
  - the `discordant` count;
  - `positive_agreement` and `negative_agreement`, which are specific agreement and not
    the FDA's PPA and NPA;
  - `jaccard`, `pabak`, `scott_pi`, `gwet_ac1`, `odds_ratio`, `mcnemar_odds_ratio` and
    `phi_squared`.
- Byrt's `prevalence_index` and `bias_index` are accepted as checks but close nothing
  alone, since both are functions of the marginals.
- `convention` reads printed figures as rounded half-up (the default), truncated, or
  `any`, meaning either, figure by figure. Sources truncate without saying so. Of the 55
  pairwise comparisons in Goyal et al. 2025, 15 have disagreement percentages a rounding
  source could not have printed.
- Four statuses for a comparison: unique, set, infeasible or insufficient. An infeasible
  result names the figure that excludes where one can be identified. An impossible
  figure raises `InvalidInput`.
- `recover_many` runs a batch without raising. A row that would have raised is reported
  as `impossible`, with its reason.
- A command line, `enum2x2 comparisons.csv`, reads comparisons from CSV or JSON, prints a
  summary and writes the results as JSON with `--out`.
- `kappa_max`, `kappa_min`, `expected_agreement`, `kappa_from_cells`,
  `rounding_interval`, `exact_interval` and `exactly_rounds_to` are exposed for use on
  their own.
