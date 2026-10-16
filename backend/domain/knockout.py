"""Llaves de eliminación directa con byes y partido por el 3er puesto."""
from __future__ import annotations

from dataclasses import dataclass

MAX_TEAMS = 64


@dataclass(slots=True, frozen=True)
class Ref:
    """Origen de un lugar en la llave: un cabeza de serie, o el ganador/perdedor de otro partido."""

    kind: str  # "seed" | "winner" | "loser"
    value: int  # número de serie (1 = mejor) o clave del partido

    @staticmethod
    def seed(n: int) -> "Ref":
        return Ref("seed", n)


@dataclass(slots=True, frozen=True)
class BMatch:
    key: int  # único dentro de la llave, creciente por ronda
    round: int  # 1 = primera ronda ... última = final
    home: Ref
    away: Ref
    third_place: bool = False


def bracket_size(n: int) -> int:
    if n < 2 or n > MAX_TEAMS:
        raise ValueError(f"una llave admite entre 2 y {MAX_TEAMS} equipos")
    size = 1
    while size < n:
        size *= 2
    return size


def total_rounds(n: int) -> int:
    return bracket_size(n).bit_length() - 1


def seed_order(size: int) -> list[int]:
    """Posiciones de la llave: [1, 8, 4, 5, 2, 7, 3, 6] para 8. Los vecinos se enfrentan."""
    order = [1]
    while len(order) < size:
        m = len(order) * 2
        order = [x for s in order for x in (s, m + 1 - s)]
    return order


def build_bracket(n: int, third_place: bool = False) -> list[BMatch]:
    """Partidos de la llave para ``n`` equipos (series 1..n).

    Si ``n`` no es potencia de 2, los mejores cabezas de serie pasan directo a la segunda
    ronda (bye): no se crea partido para ellos, entran como ``Ref.seed`` en esa ronda.
    """
    size = bracket_size(n)
    rounds = total_rounds(n)
    cur: list[Ref | None] = [Ref.seed(s) if s <= n else None for s in seed_order(size)]
    matches: list[BMatch] = []
    key = 0
    for rnd in range(1, rounds + 1):
        nxt: list[Ref | None] = []
        for i in range(0, len(cur), 2):
            a, b = cur[i], cur[i + 1]
            if b is None:  # bye: pasa el de mejor serie
                nxt.append(a)
                continue
            key += 1
            matches.append(BMatch(key, rnd, a, b))
            nxt.append(Ref("winner", key))
        cur = nxt
    if third_place and rounds >= 2:
        semis = [m for m in matches if m.round == rounds - 1]
        if len(semis) == 2:  # con pocos equipos puede haber una sola semifinal real
            matches.append(BMatch(key + 1, rounds, Ref("loser", semis[0].key), Ref("loser", semis[1].key), True))
    return matches


def round_name(rnd: int, rounds: int) -> str:
    left = rounds - rnd  # rondas que faltan después de esta
    names = {0: "Final", 1: "Semifinales", 2: "Cuartos de final", 3: "Octavos de final", 4: "Dieciseisavos de final"}
    return names.get(left, f"Ronda de {2 ** (left + 1)}")
