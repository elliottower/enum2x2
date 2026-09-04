"""Every integer 2x2 table consistent with what a source printed."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Sequence

from ._core import (InvalidInput, UndefinedStatistic, counts_rounding_to,
                    expected_agreement, kappa_from_cells, kappa_max, kappa_min,
                    rounds_to)

UNIQUE, SET, INFEASIBLE, INSUFFICIENT = "unique", "set", "infeasible", "insufficient"


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
        if not 0 <= count <= n:
            raise InvalidInput(f"n_{side} = {count} is outside [0, {n}]")
        return [int(count)]
    return counts_rounding_to(printed, n, as_percent)


def recover(n: int,
            *,
            n_a: int | None = None, n_b: int | None = None,
            p_a: str | None = None, p_b: str | None = None,
            kappa: str | None = None,
            agreement: str | None = None,
            marginals_as_percent: bool = False,
            agreement_as_percent: bool = False) -> Recovery:
    """Enumerate every integer table consistent with the figures as printed.

    Marginals are given either as exact counts (`n_a`, `n_b`) or as the strings a
    source printed (`p_a`, `p_b`); a printed string carries its own precision, so
    "0.10" and "0.1" are different inputs and must not be passed as floats.

    Raises InvalidInput for a figure that cannot describe any table. Returns a
    Recovery with status 'infeasible' when the figures are individually possible
    but jointly admit nothing — that is a property of the source, not a defect in
    the call, so it is reported rather than raised.
    """
    if not isinstance(n, int) or n <= 0:
        raise InvalidInput(f"N must be a positive integer, got {n!r}")
    for name, v in (("p_a", p_a), ("p_b", p_b), ("kappa", kappa),
                    ("agreement", agreement)):
        if v is not None and not isinstance(v, str):
            raise InvalidInput(
                f"{name} must be the string the source printed, not {type(v).__name__}; "
                f"a float cannot distinguish '0.10' from '0.1'")
    if kappa is None:
        return Recovery(INSUFFICIENT, n=n, reason="kappa was not reported")
    if (n_a is None) == (p_a is None):
        return Recovery(INSUFFICIENT, n=n,
                        reason="give exactly one of n_a or p_a for the first criterion")
    if (n_b is None) == (p_b is None):
        return Recovery(INSUFFICIENT, n=n,
                        reason="give exactly one of n_b or p_b for the second criterion")
    if not -1.0 <= float(kappa) <= 1.0:
        raise InvalidInput(f"kappa = {kappa} is outside [-1, 1]")

    a_counts = _marginal_counts(n, n_a, p_a, marginals_as_percent, "a")
    b_counts = _marginal_counts(n, n_b, p_b, marginals_as_percent, "b")

    survivors: list[Table] = []
    for na in a_counts:
        for nb in b_counts:
            # A candidate pair can make expected agreement exactly 1, leaving kappa
            # undefined for that pair alone. It contributes no table; it is not a
            # reason to abandon the row.
            if n * n == na * nb + (n - na) * (n - nb):
                continue
            for n11 in range(max(0, na + nb - n), min(na, nb) + 1):
                n10, n01 = na - n11, nb - n11
                n00 = n - n11 - n10 - n01
                if n00 < 0:
                    continue
                t = Table(n11, n10, n01, n00)
                if not rounds_to(t.kappa, kappa):
                    continue
                if agreement is not None and not rounds_to(
                        t.agreement, agreement, agreement_as_percent):
                    continue
                survivors.append(t)

    published = {k: v for k, v in
                 (("n_a", n_a), ("n_b", n_b), ("p_a", p_a), ("p_b", p_b),
                  ("kappa", kappa), ("agreement", agreement)) if v is not None}

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
        if not lo - 5e-3 <= float(kappa) <= hi + 5e-3:
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
    out = []
    for row in rows:
        try:
            out.append(recover(**row))
        except Enum2x2Error as e:
            out.append(Recovery(INSUFFICIENT, n=row.get("n"), reason=str(e)))
    return out
