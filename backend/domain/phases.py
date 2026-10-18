"""Fases eliminatorias encadenadas: copas que se alimentan de la fase de grupos y/o de otras fases.

Ejemplo: los primeros de cada grupo van directo a la Copa de Oro; 2º y 3º juegan una sola ronda
(reclasificación); los ganadores suben a Oro y los perdedores, con los 4º de cada grupo, arman la Plata.
Cada lugar de una llave es un equipo ya conocido o "el ganador/perdedor del partido N de otra fase".
Las fases se pueden listar en cualquier orden: se resuelven según de quién dependen.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence

from .knockout import MAX_TEAMS, BMatch, bracket_size, build_bracket, total_rounds
from .qualification import CupSpec, Entrant, assign_cups, avoid_same_group

PAIRINGS = ("seeded", "cross", "random", "manual")


@dataclass(slots=True, frozen=True)
class Slot:
    """Un lugar de la llave: un equipo ya clasificado, o el resultado de un partido de otra fase."""

    team: Entrant | None = None
    source: tuple[str, int, str] | None = None  # (fase, clave del partido, "winner" | "loser")
    label: str = ""
    code: str = ""  # "1A" = primero del grupo A; "G2:Fase" / "P2:Fase" = ganador / perdedor del partido 2 de Fase


@dataclass(slots=True, frozen=True)
class PhasePlan:
    spec: CupSpec
    slots: tuple[Slot, ...]  # en orden de siembra: slots[0] es el cabeza de serie 1
    matches: tuple[BMatch, ...]  # solo las rondas que se juegan en esta fase
    size: int
    byes: int
    total_rounds: int  # rondas de la llave completa
    rounds: int  # rondas que se juegan acá (menos que total_rounds si la fase se corta)


def _group_of(slot: Slot) -> int | None:
    return slot.team.group if slot.team else None


def _order(specs: Sequence[CupSpec]) -> list[CupSpec]:
    """Orden de resolución: cada fase después de aquellas de las que toma ganadores o perdedores."""
    by_name = {s.name: s for s in specs}
    for s in specs:
        for src in (*s.from_winners, *s.from_losers):
            if src not in by_name:
                raise ValueError(f"{s.name}: la fase «{src}» no existe")
    out: list[CupSpec] = []
    done: set[str] = set()
    pending = list(specs)
    while pending:
        ready = [s for s in pending if all(d in done for d in (*s.from_winners, *s.from_losers))]
        if not ready:
            raise ValueError("Las copas se alimentan unas de otras en círculo: " + ", ".join(s.name for s in pending))
        first = ready[0]
        out.append(first)
        done.add(first.name)
        pending.remove(first)
    return out


def _cross_pairs(slots: Sequence[Slot], name: str) -> list[tuple[Slot, Slot]]:
    """Cruces estilo mundial entre grupos vecinos con dos puestos: 1ºA-2ºB, 1ºC-2ºD, 1ºB-2ºA, 1ºD-2ºC.

    Sirve para cualquier par de puestos (por ejemplo 2º y 3º: 2ºA-3ºB, 2ºC-3ºD, 2ºB-3ºA, 2ºD-3ºC).
    """
    places = sorted({s.team.position for s in slots if s.team})
    if len(places) != 2 or any(s.team is None for s in slots):
        raise ValueError(f"{name}: el cruce tipo mundial necesita exactamente dos puestos de cada grupo (por ej. 1º y 2º, o 2º y 3º)")
    lo, hi = places
    first: dict[int, Slot] = {}
    second: dict[int, Slot] = {}
    for s in slots:
        (first if s.team.position == lo else second)[s.team.group] = s
    groups = sorted(first)
    if set(first) != set(second) or len(groups) % 2 or len(first) + len(second) != len(slots):
        raise ValueError(f"{name}: el cruce tipo mundial necesita los mismos dos puestos de una cantidad par de grupos")
    pairs: list[tuple[Slot, Slot]] = []
    for i in range(0, len(groups), 4):
        blk = groups[i:i + 4]
        if len(blk) == 4:
            a, b, c, d = blk
            pairs += [(first[a], second[b]), (first[c], second[d]), (first[b], second[a]), (first[d], second[c])]
        else:
            a, b = blk
            pairs += [(first[a], second[b]), (first[b], second[a])]
    return pairs


def _manual_pairs(slots: Sequence[Slot], spec: CupSpec) -> list[tuple[Slot, Slot]]:
    by_code = {s.code: s for s in slots}
    pairs, used = [], set()
    for a, b in spec.manual_pairs:
        for c in (a, b):
            if c not in by_code:
                raise ValueError(f"{spec.name}: «{c}» no está entre los equipos de esta copa")
            if c in used:
                raise ValueError(f"{spec.name}: «{c}» está en más de un cruce")
            used.add(c)
        pairs.append((by_code[a], by_code[b]))
    if len(pairs) != len(slots) // 2:
        raise ValueError(f"{spec.name}: faltan cruces ({len(pairs)} de {len(slots) // 2})")
    return pairs


def _arrange(slots: list[Slot], ms: Sequence[BMatch], spec: CupSpec, avoid: bool) -> list[Slot]:
    """Acomoda los lugares en la llave según el tipo de cruce elegido."""
    n = len(slots)
    mode = spec.pairing
    if mode not in PAIRINGS:
        raise ValueError(f"{spec.name}: tipo de cruce desconocido")
    if mode == "random":
        random.Random(spec.pairing_seed).shuffle(slots)
    if mode in ("cross", "manual"):
        if bracket_size(n) != n:
            raise ValueError(f"{spec.name}: este tipo de cruce necesita una cantidad de equipos potencia de 2 (hay {n})")
        pairs = _cross_pairs(slots, spec.name) if mode == "cross" else _manual_pairs(slots, spec)
        out: list[Slot | None] = [None] * n
        for m, (home, away) in zip(sorted((m for m in ms if m.round == 1), key=lambda m: m.key), pairs):
            out[m.home.value - 1], out[m.away.value - 1] = home, away
        return out  # type: ignore[return-value]
    return avoid_same_group(slots, ms, _group_of) if avoid else slots


def plan_phases(
    entrants: Sequence[Entrant], specs: Sequence[CupSpec], third_place: bool = True, avoid_same: bool = True,
    group_names: Mapping[int, str] | None = None,
) -> list[PhasePlan]:
    """Arma todas las fases (devueltas en el orden pedido). ``group_names`` da las letras para los códigos."""
    names = [s.name for s in specs]
    if len(set(names)) != len(names):
        raise ValueError("Cada copa necesita un nombre distinto")
    for s in specs:
        if not (s.positions or s.extra or s.from_winners or s.from_losers):
            raise ValueError(f"{s.name}: indicá qué puestos clasifican")
    order = _order(specs)
    chosen = dict(zip((s.name for s in specs), assign_cups(entrants, specs)))
    letter = lambda g: (group_names or {}).get(g, str(g)).replace("Grupo ", "")  # noqa: E731

    by_name: dict[str, PhasePlan] = {}
    taken: set[tuple[str, str]] = set()
    for spec in order:
        slots = [Slot(team=e, code=f"{e.position}{letter(e.group)}") for e in chosen[spec.name]]
        for kind, sources in (("winner", spec.from_winners), ("loser", spec.from_losers)):
            for src in sources:
                prev = by_name[src]
                if (src, kind) in taken:
                    raise ValueError(f"{src}: esos equipos ya entran a otra fase")
                taken.add((src, kind))
                last = [m for m in prev.matches if m.round == prev.rounds and not m.third_place]
                word = "Ganador" if kind == "winner" else "Perdedor"
                def who(ref) -> str:  # quiénes juegan ese partido, p. ej. "2B"
                    sl = prev.slots[ref.value - 1] if ref.kind == "seed" else None
                    return sl.code if sl and sl.team else (sl.label if sl else "?")

                for i, m in enumerate(last, 1):
                    slots.append(Slot(source=(src, m.key, kind),
                                      label=f"{word} del partido {i} de {src} ({who(m.home)} vs {who(m.away)})",
                                      code=f"{'G' if kind == 'winner' else 'P'}{i}:{src}"))

        n = len(slots)
        if not 2 <= n <= MAX_TEAMS:
            raise ValueError(f"{spec.name}: necesita entre 2 y {MAX_TEAMS} equipos y tiene {n}")
        total, size = total_rounds(n), bracket_size(n)
        rounds = spec.max_rounds or total
        if not 1 <= rounds <= total:
            raise ValueError(f"{spec.name}: con {n} equipos hay entre 1 y {total} rondas")
        if rounds == 1 < total and size != n:
            raise ValueError(f"{spec.name}: para jugar una sola ronda hace falta una cantidad de equipos potencia de 2 (hay {n})")

        third = (third_place if spec.third_place is None else spec.third_place) and rounds == total
        ms = build_bracket(n, third)
        use_avoid = spec.avoid_same_group if spec.avoid_same_group is not None else avoid_same
        slots = _arrange(slots, ms, spec, use_avoid)
        by_name[spec.name] = PhasePlan(
            spec, tuple(slots), tuple(m for m in ms if m.round <= rounds), size, size - n, total, rounds)
    return [by_name[n] for n in names]
