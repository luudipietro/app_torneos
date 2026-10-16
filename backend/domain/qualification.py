"""Clasificación desde la fase de grupos hacia una o más llaves (copa de oro, plata...)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .knockout import BMatch, build_bracket
from .standings import Row


@dataclass(slots=True, frozen=True)
class Entrant:
    team: int
    group: int
    position: int  # puesto final dentro de su grupo (1 = primero)
    row: Row


@dataclass(slots=True, frozen=True)
class CupSpec:
    """Quiénes juegan una copa.

    ``positions``: entran todos los equipos que terminaron en esos puestos del grupo.
    ``extra``: (puesto, cantidad) suma a los mejores de ese puesto entre todos los grupos,
    por ejemplo (3, 8) = "los 8 mejores terceros".
    """

    name: str
    positions: tuple[int, ...] = ()
    extra: tuple[tuple[int, int], ...] = ()


def _record(e: Entrant) -> tuple:
    r = e.row
    return (-r.points, -r.gd, -r.gf, r.fair_play, e.team)


def entrants_from_tables(tables: Mapping[int, Sequence[Row]]) -> list[Entrant]:
    """``tables``: grupo -> filas ya ordenadas de la tabla de posiciones."""
    return [Entrant(r.team, g, pos, r) for g, rows in tables.items() for pos, r in enumerate(rows, 1)]


def assign_cups(entrants: Sequence[Entrant], specs: Sequence[CupSpec]) -> list[list[Entrant]]:
    """Reparte los equipos entre las copas, en orden, y devuelve cada copa sembrada.

    Una copa toma sus puestos completos y sus "mejores N"; lo que no usa queda para la
    siguiente (así la copa de plata recoge a los no clasificados a la de oro).
    La siembra va por puesto (primeros, luego segundos...) y, dentro del puesto, por
    rendimiento (puntos, diferencia de gol, goles a favor, fair play).
    """
    used: set[int] = set()
    out: list[list[Entrant]] = []
    for spec in specs:
        if set(spec.positions) & {p for p, _ in spec.extra}:
            raise ValueError(f"{spec.name}: un puesto no puede estar completo y también en 'mejores'")
        pool = [e for e in entrants if e.team not in used]
        chosen = [e for e in pool if e.position in spec.positions]
        for pos, count in spec.extra:
            cands = sorted((e for e in pool if e.position == pos), key=_record)
            if count > len(cands):
                raise ValueError(f"{spec.name}: pide {count} equipos de puesto {pos} y solo hay {len(cands)}")
            chosen += cands[:count]
        chosen.sort(key=lambda e: (e.position, _record(e)))
        used |= {e.team for e in chosen}
        out.append(chosen)
    return out


def avoid_same_group(entrants: Sequence[Entrant], matches: Sequence[BMatch]) -> list[Entrant]:
    """Reordena los visitantes de primera ronda para evitar cruces entre equipos del mismo grupo.

    Solo intercambia equipos de partidos de la primera ronda; si no hay forma de evitar
    todos los cruces deja los que no pueda. Los cabezas de serie (locales) no se mueven.
    """
    teams = list(entrants)
    r1 = [m for m in matches if m.round == 1]

    def clash(h: int, a: int) -> bool:
        return teams[h - 1].group == teams[a - 1].group

    away = [m.away.value for m in r1]
    home = [m.home.value for m in r1]
    for i in range(len(r1)):
        if not clash(home[i], away[i]):
            continue
        for j in range(len(r1)):
            if j != i and not clash(home[i], away[j]) and not clash(home[j], away[i]):
                away[i], away[j] = away[j], away[i]
                break
    result = list(teams)
    for m, a in zip(r1, away):  # reubica: la serie m.away.value pasa a ocupar el equipo a
        result[m.away.value - 1] = teams[a - 1]
    return result


@dataclass(slots=True, frozen=True)
class CupPlan:
    label: str
    cups: tuple[CupSpec, ...]


def suggest_cup_plans(n_groups: int, group_size: int) -> list[CupPlan]:
    """Formatos habituales de clasificación según la forma de la fase de grupos."""
    plans: list[CupPlan] = []

    def pow2_up(n: int) -> int:
        p = 1
        while p < n:
            p *= 2
        return p

    total = n_groups * group_size
    for q in range(1, group_size):
        base = n_groups * q
        if base < 2:
            continue
        top = tuple(range(1, q + 1))
        rest_pos = tuple(range(q + 1, group_size + 1))
        label = "Primero de cada grupo" if q == 1 else f"Los {q} primeros de cada grupo"
        options: list[tuple[str, CupSpec]] = [(label, CupSpec("Copa de Oro", top))]
        if base & (base - 1):  # no es potencia de 2: completar con los mejores del puesto siguiente
            need = pow2_up(base) - base
            if 0 < need <= n_groups:
                options.append((f"{label} + los {need} mejores {q + 1}º", CupSpec("Copa de Oro", top, ((q + 1, need),))))
        for lab, oro in options:
            plans.append(CupPlan(lab, (oro,)))
            qualified = base + (oro.extra[0][1] if oro.extra else 0)
            if total - qualified >= 4:  # alcanza para una copa de consolación
                # recoge a todos los no clasificados: lo que quedó de cada puesto restante
                plans.append(CupPlan(f"{lab} · con Copa de Plata", (oro, CupSpec("Copa de Plata", rest_pos))))
    return plans
