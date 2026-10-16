"""Armado de grupos: sugerencia de distribución y sorteo."""
from __future__ import annotations

import random
from dataclasses import dataclass

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


def draw_groups(
    teams: list[Team], n_groups: int, seed: int | None = None
) -> list[list[Team]]:
    """Sorteo con cabezas de serie: los de serie se reparten primero, uno por grupo.

    Los equipos sin serie se mezclan al azar y se completan en serpentina.
    Reproducible con ``seed``.
    """
    rng = random.Random(seed)
    layout_for(len(teams), n_groups)  # valida
    seeded = sorted((t for t in teams if t.seed is not None), key=lambda t: t.seed)
    rest = [t for t in teams if t.seed is None]
    rng.shuffle(rest)
    groups: list[list[Team]] = [[] for _ in range(n_groups)]
    # bombos: de a n_groups equipos por vuelta, repartidos en orden aleatorio.
    # Un bombo incompleto (final) deja grupos con un equipo más: tamaños base o base+1.
    pool = seeded + rest
    for start in range(0, len(pool), n_groups):
        pot = pool[start:start + n_groups]
        order = list(range(n_groups))
        rng.shuffle(order)
        for t, gi in zip(pot, order):
            groups[gi].append(t)
    return groups
