"""Tabla de posiciones con desempates configurables."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True, frozen=True)
class Result:
    home: int
    away: int
    home_goals: int
    away_goals: int


@dataclass(slots=True)
class Row:
    team: int
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0
    points: int = 0
    fair_play: int = 0  # puntos de sanción (menos es mejor)

    @property
    def gd(self) -> int:
        return self.gf - self.ga


@dataclass(slots=True)
class Rules:
    win: int = 3
    draw: int = 1
    loss: int = 0
    # criterios en orden: points, h2h (mini-tabla entre empatados), gd, gf, fair_play
    tiebreakers: list[str] = field(
        default_factory=lambda: ["points", "h2h", "gd", "gf", "fair_play"]
    )


def _accumulate(team_ids, results, rules: Rules) -> dict[int, Row]:
    rows = {t: Row(t) for t in team_ids}
    for r in results:
        if r.home not in rows or r.away not in rows:
            continue
        h, a = rows[r.home], rows[r.away]
        h.played += 1; a.played += 1
        h.gf += r.home_goals; h.ga += r.away_goals
        a.gf += r.away_goals; a.ga += r.home_goals
        if r.home_goals > r.away_goals:
            h.won += 1; a.lost += 1
            h.points += rules.win; a.points += rules.loss
        elif r.home_goals < r.away_goals:
            a.won += 1; h.lost += 1
            a.points += rules.win; h.points += rules.loss
        else:
            h.drawn += 1; a.drawn += 1
            h.points += rules.draw; a.points += rules.draw
    return rows


_KEYS: dict[str, Callable[[Row], int]] = {
    "points": lambda r: -r.points,
    "gd": lambda r: -r.gd,
    "gf": lambda r: -r.gf,
    "fair_play": lambda r: r.fair_play,
}


def _order(rows: list[Row], results, rules: Rules, criteria: list[str]) -> list[Row]:
    """Ordena recursivamente: aplica un criterio y subdivide los empates."""
    if len(rows) <= 1 or not criteria:
        return sorted(rows, key=lambda r: r.team)  # orden estable final (sorteo manual)
    crit, rest = criteria[0], criteria[1:]
    if crit == "h2h":
        ids = {r.team for r in rows}
        mini = _accumulate(ids, [x for x in results if x.home in ids and x.away in ids], rules)
        key = lambda r: (-mini[r.team].points, -mini[r.team].gd, -mini[r.team].gf)
    else:
        k = _KEYS[crit]
        key = lambda r: (k(r),)
    groups: dict[tuple, list[Row]] = {}
    for r in sorted(rows, key=key):
        groups.setdefault(key(r), []).append(r)
    out: list[Row] = []
    for g in groups.values():
        # los que siguen empatados se reevalúan con los criterios restantes
        out += _order(g, results, rules, rest)
    return out


def standings(
    team_ids: list[int],
    results: list[Result],
    rules: Rules | None = None,
    fair_play: dict[int, int] | None = None,
) -> list[Row]:
    rules = rules or Rules()
    rows = _accumulate(team_ids, results, rules)
    for t, v in (fair_play or {}).items():
        if t in rows:
            rows[t].fair_play = v
    return _order(list(rows.values()), results, rules, rules.tiebreakers)
