# Changelog

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
