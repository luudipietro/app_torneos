"""Armado de grupos: sugerencia de distribución y sorteo."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping

from .team import Team


@dataclass(slots=True, frozen=True)
class GroupLayout:
    n_groups: int
    sizes: tuple[int, ...]  # tamaño de cada grupo (los primeros pueden ser más grandes)

    @property
    def balanced(self) -> bool:
        return max(self.sizes) - min(self.sizes) == 0


def layout_for(n_teams: int, n_groups: int) -> GroupLayout:
    if n_groups < 1 or n_groups > n_teams:
        raise ValueError("cantidad de grupos inválida")
    base, extra = divmod(n_teams, n_groups)
    sizes = tuple(base + 1 if i < extra else base for i in range(n_groups))
    return GroupLayout(n_groups, sizes)


def suggest_layouts(n_teams: int, min_size: int = 3, max_size: int = 8) -> list[GroupLayout]:
    """Distribuciones razonables (grupos de min_size..max_size), balanceadas primero."""
    if n_teams < 2 or n_teams > 64:
        raise ValueError("el torneo admite entre 2 y 64 equipos")
    out = []
    for g in range(1, n_teams // min_size + 1):
        lay = layout_for(n_teams, g)
        if min(lay.sizes) >= min_size and max(lay.sizes) <= max_size:
            out.append(lay)
    # balanceadas primero; luego potencias de 2 de grupos (cruces de llave más simples)
    out.sort(key=lambda l: (not l.balanced, l.n_groups & (l.n_groups - 1) != 0, -l.n_groups))
    return out


def draw_steps(
    teams: list[Team], n_groups: int, seed: int | None = None, fixed: Mapping[int, int] | None = None
) -> list[tuple[Team, int]]:
    """Sorteo con cabezas de serie, como lista de pasos (equipo, índice de grupo) en el orden en que salen.

    Los de serie se reparten primero, uno por grupo; los demás se mezclan al azar.
    ``fixed`` (id de equipo -> grupo) son equipos ya ubicados a mano: no salen en los pasos,
    pero cuentan para el tamaño de los grupos y para repartir los cabezas de serie.
    Reproducible con ``seed``.
    """
    rng = random.Random(seed)
    layout_for(len(teams), n_groups)  # valida
    fixed = dict(fixed or {})
    ids = {t.id for t in teams}
    for tid, g in fixed.items():
        if tid not in ids:
            raise ValueError(f"el equipo {tid} no existe")
        if not 0 <= g < n_groups:
            raise ValueError(f"grupo inválido para el equipo {tid}")
    free = [t for t in teams if t.id not in fixed]
    seeded = sorted((t for t in free if t.seed is not None), key=lambda t: t.seed)
    rest = [t for t in free if t.seed is None]
    rng.shuffle(rest)
    pool = seeded + rest
    steps: list[tuple[Team, int]] = []
    if not fixed:
        # bombos: de a n_groups equipos por vuelta, repartidos en orden aleatorio.
        # Un bombo incompleto (final) deja grupos con un equipo más: tamaños base o base+1.
        for start in range(0, len(pool), n_groups):
            order = list(range(n_groups))
            rng.shuffle(order)
            steps += zip(pool[start:start + n_groups], order)
        return steps
    sizes = [0] * n_groups
    seeds_in = [0] * n_groups
    for t in teams:
        if t.id in fixed:
            sizes[fixed[t.id]] += 1
            seeds_in[fixed[t.id]] += t.seed is not None
    for t in pool:  # cada equipo va a uno de los grupos más vacíos (y con menos cabezas de serie)
        key = [(seeds_in[g] if t.seed is not None else 0, sizes[g]) for g in range(n_groups)]
        g = rng.choice([g for g in range(n_groups) if key[g] == min(key)])
        sizes[g] += 1
        seeds_in[g] += t.seed is not None
        steps.append((t, g))
    return steps


def draw_groups(
    teams: list[Team], n_groups: int, seed: int | None = None, fixed: Mapping[int, int] | None = None
) -> list[list[Team]]:
    """Grupos resultantes del sorteo (primero los equipos ubicados a mano, luego los sorteados)."""
    steps = draw_steps(teams, n_groups, seed, fixed)  # valida ``fixed``
    by_id = {t.id: t for t in teams}
    groups: list[list[Team]] = [[] for _ in range(n_groups)]
    for tid, g in (fixed or {}).items():
        groups[g].append(by_id[tid])
    for t, g in steps:
        groups[g].append(t)
    return groups
