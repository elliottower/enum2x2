"""Every integer 2x2 table consistent with what a source printed."""
from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from typing import Iterator, Sequence

from decimal import Decimal, InvalidOperation as InvalidDecimal
from fractions import Fraction

from ._core import (InvalidInput, UndefinedStatistic, counts_rounding_to,
                    exact_interval, exact_kappa, exactly_rounds_to,
                    expected_agreement, kappa_from_cells, kappa_max, kappa_min,
                    mcnemar_chisq, mcnemar_exact_p, mcnemar_midp, mcnemar_p,
                    rounding_interval, rounds_to, satisfies_printed_p,
                    CLOSING_STATISTICS, MARGINAL_DETERMINED)

# Any one of these, added to both marginals and N, closes the table. A 2x2 with N
# fixed has three degrees of freedom and the marginals use two.
CLOSING = (("kappa", "agreement", "mcnemar", "discordant")
           + tuple(k for k in CLOSING_STATISTICS if k not in MARGINAL_DETERMINED))
MCNEMAR_TESTS = ("exact", "midp", "chisq", "chisq_cc")

UNIQUE, SET, INFEASIBLE, INSUFFICIENT = "unique", "set", "infeasible", "insufficient"
# A batch cannot raise, so an impossible figure needs a status of its own: counting it
# as 'insufficient' would inflate the number of sources that under-reported.
IMPOSSIBLE = "impossible"


@dataclass(frozen=True)
class Table:
    """One 2x2, with the statistics it produces."""
    n11: int
    n10: int
    n01: int
    n00: int

    @property
    def n(self) -> int:
        return self.n11 + self.n10 + self.n01 + self.n00

    @property
    def kappa(self) -> float:
        return kappa_from_cells(self.n11, self.n10, self.n01, self.n00)

    @property
    def agreement(self) -> float:
        return (self.n11 + self.n00) / self.n

    @property
    def discordant(self) -> tuple[int, int]:
        """The two off-diagonal counts, in the order (A only, B only)."""
        return self.n10, self.n01

    @property
    def asymmetry(self) -> float | None:
        """|n10 - n01| / (n10 + n01): 0 when the disagreement is even, 1 when it
        runs entirely one way. None when the two criteria never disagree."""
        d = self.n10 + self.n01
        return abs(self.n10 - self.n01) / d if d else None

    @property
    def n_discordant(self) -> int:
        """The number of cases the two criteria classify differently."""
        return self.n10 + self.n01

    def mcnemar(self, test: str = "exact"):
        """The p a McNemar variant reports for this table.

        'exact' is a Fraction and decided exactly; the chi-square variants are
        floats, because the statistic is rational and its tail is not.
        """
        return mcnemar_p(self.n10, self.n01, test)

    def as_dict(self) -> dict[str, int]:
        return {"n11": self.n11, "n10": self.n10, "n01": self.n01, "n00": self.n00}

    def __repr__(self) -> str:
        return f"Table({self.n11}, {self.n10}, {self.n01}, {self.n00})"


@dataclass(frozen=True)
class Recovery:
    """What a published report determines about its own table.

    Iterate it for the tables; len() is how many survived. `status` is one of
    'unique', 'set', 'infeasible', 'insufficient'.
    """
    status: str
    tables: tuple[Table, ...] = ()
    n: int | None = None
    reason: str | None = None
    published: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.tables)

    def __iter__(self) -> Iterator[Table]:
        return iter(self.tables)

    def __getitem__(self, i):
        return self.tables[i]

    def __bool__(self) -> bool:
        return bool(self.tables)

    @property
    def table(self) -> Table:
        """The table, where the report determines exactly one."""
        if self.status != UNIQUE:
            raise Enum2x2Error(
                f"the report is {self.status!r}, so it does not determine one table; "
                f"iterate the recovery for all {len(self.tables)} of them")
        return self.tables[0]

    def cell_range(self, cell: str) -> tuple[int, int]:
        """Smallest and largest value a cell takes across the surviving tables."""
        vs = [getattr(t, cell) for t in self.tables]
        if not vs:
            raise Enum2x2Error("no tables survived, so no cell has a range")
        return min(vs), max(vs)

    @property
    def cell_ranges(self) -> dict[str, tuple[int, int]]:
        return {c: self.cell_range(c) for c in ("n11", "n10", "n01", "n00")}

    def __repr__(self) -> str:
        if self.status == INSUFFICIENT:
            return f"<Recovery insufficient: {self.reason}>"
        if self.status == INFEASIBLE:
            return f"<Recovery infeasible on N={self.n}: {self.reason}>"
        if self.status == UNIQUE:
            return f"<Recovery unique on N={self.n}: {self.tables[0]!r}>"
        r = self.cell_ranges
        span = "/".join(f"{r[c][0]}-{r[c][1]}" if r[c][0] != r[c][1] else str(r[c][0])
                        for c in ("n11", "n10", "n01", "n00"))
        return f"<Recovery {len(self.tables)} tables on N={self.n}: {span}>"


from ._core import Enum2x2Error  # noqa: E402  (used by Recovery above)


def _marginal_counts(n: int, count: int | None, printed: str | None,
                     as_percent: bool, side: str) -> list[int]:
    if count is not None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise InvalidInput(f"n_{side} must be an integer count, got {count!r}")
        if not 0 <= count <= n:
            raise InvalidInput(f"n_{side} = {count} is outside [0, {n}]")
        return [count]
    lo, hi = rounding_interval(printed, as_percent)
    if hi < 0 or lo > 1:
        # No proportion rounds to this, so there is no marginal at all. That is a
        # defect in the call, not a property of the source, and reporting it as an
        # empty candidate set would attach a false reason to it.
        raise InvalidInput(
            f"p_{side} = {printed!r} is outside [0, 1] as a proportion"
            + (" (given as a percentage)" if as_percent else ""))
    return counts_rounding_to(printed, n, as_percent)


def recover(n: int,
            *,
            n_a: int | None = None, n_b: int | None = None,
            p_a: str | None = None, p_b: str | None = None,
            kappa: str | None = None,
            agreement: str | None = None,
            mcnemar: str | None = None,
            mcnemar_test: str = "exact",
            discordant: int | None = None,
            marginals_as_percent: bool = False,
            agreement_as_percent: bool = False,
            **statistics: str) -> Recovery:
    """Enumerate every integer table consistent with the figures as printed.

    Marginals are given either as exact counts (`n_a`, `n_b`) or as the strings a
    source printed (`p_a`, `p_b`); a printed string carries its own precision, so
    "0.10" and "0.1" are different inputs and must not be passed as floats.

    Raises InvalidInput for a figure that cannot describe any table. Returns a
    Recovery with status 'infeasible' when the figures are individually possible
    but jointly admit nothing — that is a property of the source, not a defect in
    the call, so it is reported rather than raised.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise InvalidInput(f"N must be a positive integer, got {n!r}")
    for name, v in (("p_a", p_a), ("p_b", p_b), ("kappa", kappa),
                    ("agreement", agreement), ("mcnemar", mcnemar)):
        if v is not None and not isinstance(v, str):
            raise InvalidInput(
                f"{name} must be the string the source printed, not {type(v).__name__}; "
                f"a float cannot distinguish '0.10' from '0.1'")
    if mcnemar_test not in MCNEMAR_TESTS:
        raise InvalidInput(
            f"mcnemar_test must be one of {MCNEMAR_TESTS}, got {mcnemar_test!r}")
    if discordant is not None:
        if isinstance(discordant, bool) or not isinstance(discordant, int):
            raise InvalidInput(
                f"discordant must be an integer count, got {discordant!r}")
        if not 0 <= discordant <= n:
            raise InvalidInput(f"discordant = {discordant} is outside [0, {n}]")
    unknown = set(statistics) - set(CLOSING_STATISTICS)
    if unknown:
        raise InvalidInput(
            f"unknown statistic(s) {sorted(unknown)}; accepted: "
            + ", ".join(sorted(CLOSING_STATISTICS)))
    for name, v in statistics.items():
        if v is not None and not isinstance(v, str):
            raise InvalidInput(
                f"{name} must be the string the source printed, not "
                f"{type(v).__name__}; a float cannot distinguish '0.10' from '0.1'")
    extra = {k: v for k, v in statistics.items() if v is not None}
    given = [name for name, v in (("kappa", kappa), ("agreement", agreement),
                                  ("mcnemar", mcnemar), ("discordant", discordant))
             if v is not None] + sorted(k for k in extra if k not in MARGINAL_DETERMINED)
    if not given:
        return Recovery(INSUFFICIENT, n=n,
                        reason="no closing statistic was reported; one of "
                               + ", ".join(CLOSING) + " is needed alongside the marginals")
    for side, count, printed in (("a", n_a, p_a), ("b", n_b, p_b)):
        if count is not None and printed is not None:
            raise InvalidInput(
                f"give n_{side} or p_{side} for the {'first' if side == 'a' else 'second'} "
                f"criterion, not both")
        if count is None and printed is None:
            return Recovery(INSUFFICIENT, n=n,
                            reason=f"neither n_{side} nor p_{side} was reported for the "
                                   f"{'first' if side == 'a' else 'second'} criterion")
    for name, v in (("kappa", kappa), ("agreement", agreement),
                    ("p_a", p_a), ("p_b", p_b)):
        if v is None:
            continue
        try:
            parsed = Decimal(v)
        except InvalidDecimal as exc:
            raise InvalidInput(f"{name} = {v!r} is not a decimal number") from exc
        if not parsed.is_finite():
            raise InvalidInput(f"{name} = {v!r} is not a finite number")
    if kappa is not None and not -1 <= Decimal(kappa) <= 1:
        raise InvalidInput(f"kappa = {kappa} is outside [-1, 1]")

    a_counts = _marginal_counts(n, n_a, p_a, marginals_as_percent, "a")
    b_counts = _marginal_counts(n, n_b, p_b, marginals_as_percent, "b")

    survivors: list[Table] = []
    for na in a_counts:
        for nb in b_counts:
            # A candidate pair can make expected agreement exactly 1, leaving kappa
            # undefined for that pair alone. It contributes no table; it is not a
            # reason to abandon the row.
            if kappa is not None and n * n == na * nb + (n - na) * (n - nb):
                continue
            for n11 in range(max(0, na + nb - n), min(na, nb) + 1):
                n10, n01 = na - n11, nb - n11
                n00 = n - n11 - n10 - n01
                if n00 < 0:
                    continue
                # Membership is decided in exact rationals. Both sides are
                # rational -- a decimal string and a ratio of integers -- so the
                # comparison is exact and no tolerance is chosen.
                if kappa is not None and not exactly_rounds_to(
                        exact_kappa(n11, n10, n01, n00), kappa):
                    continue
                if agreement is not None and not exactly_rounds_to(
                        Fraction(n11 + n00, n), agreement, agreement_as_percent):
                    continue
                if discordant is not None and n10 + n01 != discordant:
                    continue
                if mcnemar is not None and not satisfies_printed_p(
                        mcnemar_p(n10, n01, mcnemar_test), mcnemar, mcnemar_test):
                    continue
                if extra:
                    ok = True
                    for name, printed in extra.items():
                        fn = CLOSING_STATISTICS[name][0]
                        try:
                            value = fn(n11, n10, n01, n00)
                        except UndefinedStatistic:
                            ok = False   # undefined here, so this table cannot be the one
                            break
                        if not exactly_rounds_to(value, printed):
                            ok = False
                            break
                    if not ok:
                        continue
                survivors.append(Table(n11, n10, n01, n00))

    published = {k: v for k, v in
                 (("n_a", n_a), ("n_b", n_b), ("p_a", p_a), ("p_b", p_b),
                  ("kappa", kappa), ("agreement", agreement),
                  ("mcnemar", mcnemar), ("discordant", discordant)) if v is not None}
    published.update(extra)
    if mcnemar is not None:
        published["mcnemar_test"] = mcnemar_test
    # Without the flags an archived result cannot be replayed from what it records.
    if p_a is not None or p_b is not None:
        published["marginals_as_percent"] = marginals_as_percent
    if agreement is not None:
        published["agreement_as_percent"] = agreement_as_percent

    if survivors:
        return Recovery(UNIQUE if len(survivors) == 1 else SET,
                        tuple(survivors), n=n, published=published)

    # Nothing survived. Say which figure excluded, rather than blaming the kappa.
    if agreement is not None:
        without = recover(n, n_a=n_a, n_b=n_b, p_a=p_a, p_b=p_b, kappa=kappa,
                          marginals_as_percent=marginals_as_percent)
        if without:
            return Recovery(INFEASIBLE, n=n, published=published,
                            reason=f"the marginals and kappa admit {len(without)} "
                                   f"table(s); adding the published agreement admits none")
    spans = []
    for na in a_counts:
        for nb in b_counts:
            try:
                spans.append((kappa_min(na / n, nb / n), kappa_max(na / n, nb / n)))
            except UndefinedStatistic:
                continue
    if spans:
        lo, hi = min(s[0] for s in spans), max(s[1] for s in spans)
        k_lo, k_hi = (float(x) for x in exact_interval(kappa))
        if k_hi < lo or k_lo > hi:
            return Recovery(INFEASIBLE, n=n, published=published,
                            reason=f"the published kappa lies outside [{lo:.3f}, {hi:.3f}], "
                                   f"the range these marginals permit")
    return Recovery(INFEASIBLE, n=n, published=published,
                    reason="the marginals permit this kappa, but no integer table attains it")


def recover_many(rows: Sequence[dict]) -> list[Recovery]:
    """Recover a series of comparisons.

    One malformed row does not stop the rest: it comes back with status
    'insufficient' and the reason, so a caller can count what was skipped.
    """
    accepted = set(inspect.signature(recover).parameters) - {"n"}
    out = []
    for row in rows:
        extra = set(row) - accepted - {"n"}
        try:
            r = recover(**{k: v for k, v in row.items() if k not in extra})
        except InvalidInput as e:
            r = Recovery(IMPOSSIBLE, n=row.get("n"), reason=str(e))
        except (Enum2x2Error, TypeError, ValueError, ArithmeticError) as e:
            r = Recovery(INSUFFICIENT, n=row.get("n"), reason=str(e))
        out.append(r)
    return out
