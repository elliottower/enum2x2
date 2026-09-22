"""Every integer 2x2 table consistent with what a source printed."""
from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from typing import Iterator, Sequence

from decimal import Decimal, InvalidOperation as InvalidDecimal
from fractions import Fraction

from ._core import (CONVENTIONS, InvalidInput, UndefinedStatistic,
                    counts_rounding_to, exact_interval, exact_kappa,
                    exactly_rounds_to, expected_agreement, kappa_from_cells,
                    kappa_max, kappa_min, mcnemar_chisq, mcnemar_exact_p,
                    mcnemar_midp, mcnemar_p, normalize_printed_p, phi_rounds_to,
                    rounding_interval, rounds_to, satisfies_printed_p,
                    CLOSING_STATISTICS, MARGINAL_DETERMINED, RANGES)

# Any one of these, added to both marginals and N, closes the table. A 2x2 with N
# fixed has three degrees of freedom and the marginals use two.
CLOSING = (("kappa", "phi", "agreement", "mcnemar", "discordant")
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
        if self.status == IMPOSSIBLE:
            return f"<Recovery impossible: {self.reason}>"
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
                     as_percent: bool, side: str, convention: str) -> list[int]:
    if count is not None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise InvalidInput(f"n_{side} must be an integer count, got {count!r}")
        if not 0 <= count <= n:
            raise InvalidInput(f"n_{side} = {count} is outside [0, {n}]")
        return [count]
    lo, hi = rounding_interval(printed, as_percent, convention)
    if hi < 0 or lo > 1:
        # No proportion rounds to this, so there is no marginal at all. That is a
        # defect in the call, not a property of the source, and reporting it as an
        # empty candidate set would attach a false reason to it.
        raise InvalidInput(
            f"p_{side} = {printed!r} is outside [0, 1] as a proportion"
            + (" (given as a percentage)" if as_percent else ""))
    return counts_rounding_to(printed, n, as_percent, convention)


def recover(n: int,
            *,
            n_a: int | None = None, n_b: int | None = None,
            p_a: str | None = None, p_b: str | None = None,
            kappa: str | None = None,
            phi: str | None = None,
            agreement: str | None = None,
            mcnemar: str | None = None,
            mcnemar_test: str = "exact",
            discordant: int | None = None,
            marginals_as_percent: bool = False,
            agreement_as_percent: bool = False,
            convention: str = "half_up",
            **statistics: str) -> Recovery:
    """Enumerate every integer table consistent with the figures as printed.

    `phi` is the phi coefficient as printed, sign included; `phi_squared`, among the
    further statistics, is for a source that printed its square.

    Marginals are given either as exact counts (`n_a`, `n_b`) or as the strings a
    source printed (`p_a`, `p_b`); a printed string carries its own precision, so
    "0.10" and "0.1" are different inputs and must not be passed as floats.

    `convention` says how the source produced its printed figures and applies to
    every printed figure in the call: 'half_up' (the default) reads a figure as
    plus or minus half a unit in its last place, 'truncate' reads it as the unit
    running away from zero, and 'any' takes the union, which cannot drop a table
    either convention admits. Under 'any' each figure is read either way on its
    own, since one source can round some figures and truncate others. Sources truncate without saying so, and a figure
    that could only have been truncated leaves an empty candidate set under the
    default.

    Raises InvalidInput for a figure that cannot describe any table. Returns a
    Recovery with status 'infeasible' when the figures are individually possible
    but jointly admit nothing — that is a property of the source, not a defect in
    the call, so it is reported rather than raised.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise InvalidInput(f"N must be a positive integer, got {n!r}")
    for name, v in (("p_a", p_a), ("p_b", p_b), ("kappa", kappa), ("phi", phi),
                    ("agreement", agreement), ("mcnemar", mcnemar)):
        if v is not None and not isinstance(v, str):
            raise InvalidInput(
                f"{name} must be the string the source printed, not {type(v).__name__}; "
                f"a float cannot distinguish '0.10' from '0.1'")
    if mcnemar_test not in MCNEMAR_TESTS:
        raise InvalidInput(
            f"mcnemar_test must be one of {MCNEMAR_TESTS}, got {mcnemar_test!r}")
    if convention not in CONVENTIONS:
        # Checked here as well as in the interval arithmetic, which a call giving
        # only exact counts never reaches.
        raise InvalidInput(
            f"convention must be one of {CONVENTIONS}, got {convention!r}")
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
    # Every printed figure is read before anything else, so a malformed or impossible
    # figure is reported as such whatever else the call does or does not contain.
    for name, v in ((("kappa", kappa), ("phi", phi), ("agreement", agreement),
                     ("p_a", p_a), ("p_b", p_b)) + tuple(extra.items())):
        if v is None:
            continue
        try:
            parsed = Decimal(v)
        except InvalidDecimal as exc:
            raise InvalidInput(f"{name} = {v!r} is not a decimal number") from exc
        if not parsed.is_finite():
            raise InvalidInput(f"{name} = {v!r} is not a finite number")
        lo, hi = RANGES.get(name, (None, None))
        if name == "agreement" and agreement_as_percent:
            lo, hi = 0, 100
        if (lo is not None and parsed < lo) or (hi is not None and parsed > hi):
            span = f"[{lo}, {hi if hi is not None else 'infinity'}]"
            raise InvalidInput(f"{name} = {v} is outside {span}, the values it can take")
    if mcnemar is not None:
        text = normalize_printed_p(mcnemar)
        for op in ("<=", ">=", "<", ">"):
            if text.startswith(op):
                text = text[len(op):]
                break
        try:
            value = Decimal(text)
            ok = value.is_finite() and 0 <= value <= 1
        except InvalidDecimal:
            ok = False
        if not ok:
            raise InvalidInput(
                f"mcnemar = {mcnemar!r} is not a p value as printed, such as '0.03' or '<0.001'")
    given = [name for name, v in (("kappa", kappa), ("phi", phi), ("agreement", agreement),
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
    a_counts = _marginal_counts(n, n_a, p_a, marginals_as_percent, "a", convention)
    b_counts = _marginal_counts(n, n_b, p_b, marginals_as_percent, "b", convention)

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
                        exact_kappa(n11, n10, n01, n00), kappa,
                        convention=convention):
                    continue
                if phi is not None:
                    try:
                        if not phi_rounds_to(n11, n10, n01, n00, phi, convention):
                            continue
                    except UndefinedStatistic:
                        continue   # a zero marginal: this table cannot be the one
                if agreement is not None and not exactly_rounds_to(
                        Fraction(n11 + n00, n), agreement, agreement_as_percent,
                        convention):
                    continue
                if discordant is not None and n10 + n01 != discordant:
                    continue
                if mcnemar is not None and not satisfies_printed_p(
                        mcnemar_p(n10, n01, mcnemar_test), mcnemar, mcnemar_test,
                        convention):
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
                        if not exactly_rounds_to(value, printed,
                                                 convention=convention):
                            ok = False
                            break
                    if not ok:
                        continue
                survivors.append(Table(n11, n10, n01, n00))

    published = {k: v for k, v in
                 (("n_a", n_a), ("n_b", n_b), ("p_a", p_a), ("p_b", p_b),
                  ("kappa", kappa), ("phi", phi), ("agreement", agreement),
                  ("mcnemar", mcnemar), ("discordant", discordant)) if v is not None}
    published.update(extra)
    if mcnemar is not None:
        published["mcnemar_test"] = mcnemar_test
    # Without the flags an archived result cannot be replayed from what it records.
    if p_a is not None or p_b is not None:
        published["marginals_as_percent"] = marginals_as_percent
    if agreement is not None:
        published["agreement_as_percent"] = agreement_as_percent
    # Recorded only where it is not the default, so a result archived before the
    # parameter existed and one archived under the default read the same.
    if convention != "half_up":
        published["convention"] = convention

    if survivors:
        return Recovery(UNIQUE if len(survivors) == 1 else SET,
                        tuple(survivors), n=n, published=published)

    # Nothing survived. Say which figure excluded, rather than blaming the kappa.
    # A printed marginal can be finer than 1/N -- routinely so where a source
    # truncates -- and then no integer count matches it at all. The kappa is not
    # what excluded, and saying it was would send a reader to the wrong figure.
    for side, counts, printed in (("a", a_counts, p_a), ("b", b_counts, p_b)):
        if not counts:
            return Recovery(INFEASIBLE, n=n, published=published,
                            reason=f"no integer count on {n} has a proportion "
                                   f"matching p_{side} = {printed!r}")
    if agreement is not None and len(given) > 1:
        # Drop the agreement alone and keep every other figure, so the agreement is
        # blamed only where it is the figure that excludes.
        without = recover(n, n_a=n_a, n_b=n_b, p_a=p_a, p_b=p_b, kappa=kappa, phi=phi,
                          mcnemar=mcnemar, mcnemar_test=mcnemar_test,
                          discordant=discordant,
                          marginals_as_percent=marginals_as_percent,
                          convention=convention, **extra)
        if without:
            others = ("the marginals and kappa" if given == ["kappa", "agreement"]
                      else "the other published figures")
            return Recovery(INFEASIBLE, n=n, published=published,
                            reason=f"{others} admit {len(without)} "
                                   f"table(s); adding the published agreement admits none")
    if kappa is not None:
        spans = []
        for na in a_counts:
            for nb in b_counts:
                try:
                    spans.append((kappa_min(na / n, nb / n), kappa_max(na / n, nb / n)))
                except UndefinedStatistic:
                    continue
        if spans:
            lo, hi = min(s[0] for s in spans), max(s[1] for s in spans)
            k_lo, k_hi = (float(x) for x in exact_interval(kappa,
                                                           convention=convention))
            if k_hi < lo or k_lo > hi:
                return Recovery(INFEASIBLE, n=n, published=published,
                                reason=f"the published kappa lies outside [{lo:.3f}, {hi:.3f}], "
                                       f"the range these marginals permit")
        if given == ["kappa"] and not extra:
            return Recovery(INFEASIBLE, n=n, published=published,
                            reason="the marginals permit this kappa, but no integer "
                                   "table attains it")
    return Recovery(INFEASIBLE, n=n, published=published,
                    reason="no integer table on these marginals reproduces the published "
                           + " and ".join(given) + " together")


def recover_many(rows: Sequence[dict]) -> list[Recovery]:
    """Recover a series of comparisons.

    One malformed row does not stop the rest: it comes back with status
    'insufficient' and the reason, so a caller can count what was skipped.
    """
    # The further statistics arrive through **statistics, so their names are not
    # parameters of recover and have to be added, or a row giving only one of them
    # would be read as reporting nothing.
    accepted = ((set(inspect.signature(recover).parameters) - {"n", "statistics"})
                | set(CLOSING_STATISTICS))
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
