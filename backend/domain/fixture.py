"""Generación de fixture todos-contra-todos (método del círculo)."""
from __future__ import annotations

Match = tuple[int, int]  # (local, visitante) por id de equipo
BYE = -1


def round_robin(team_ids: list[int], double: bool = False) -> list[list[Match]]:
    """Devuelve una lista de fechas; cada fecha es una lista de partidos.

    Con cantidad impar de equipos, uno descansa cada fecha (no aparece en la fecha).
    Con ``double=True`` se agrega la vuelta con localías invertidas.
    """
    ids = list(team_ids)
    if len(ids) != len(set(ids)):
        raise ValueError("ids de equipo repetidos")
    if len(ids) < 2:
        return []
    if len(ids) % 2:
        ids.append(BYE)
    n = len(ids)
    rounds: list[list[Match]] = []
    rot = ids[:]
    for r in range(n - 1):
        matches: list[Match] = []
        for i in range(n // 2):
            a, b = rot[i], rot[n - 1 - i]
            if BYE in (a, b):
                continue
            # alterna localía para balancear el equipo fijo (posición 0)
            matches.append((b, a) if (i == 0 and r % 2) else (a, b))
        rounds.append(matches)
        rot = [rot[0], rot[-1], *rot[1:-1]]
    if double:
        rounds += [[(b, a) for a, b in rnd] for rnd in rounds]
    return rounds
