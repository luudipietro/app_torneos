"""Sanciones automáticas por tarjetas (acumulación de amarillas y rojas)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

CARD_TYPES = ("yellow", "second_yellow", "red")


@dataclass(slots=True, frozen=True)
class DisciplineRules:
    yellows_for_suspension: int = 3  # cada N amarillas acumuladas = suspensión; 0 = sin acumulación
    yellow_matches: int = 1  # partidos por acumulación
    red_matches: int = 1  # partidos por roja directa o doble amarilla


@dataclass(slots=True, frozen=True)
class Card:
    player_id: int
    type: str  # yellow | second_yellow | red


@dataclass(slots=True, frozen=True)
class Suspension:
    player_id: int
    remaining: int  # partidos que le faltan cumplir
    reason: str  # "yellows" | "red"


def discipline_status(
    history: Iterable[Sequence[Card]], rules: DisciplineRules | None = None
) -> tuple[dict[int, Suspension], dict[int, int]]:
    """Estado disciplinario de un equipo antes de su próximo partido.

    ``history`` son los partidos ya jugados del equipo, en orden cronológico; cada uno es
    la lista de tarjetas que recibieron sus jugadores. Un jugador suspendido cumple un
    partido por cada partido siguiente del equipo, haya o no recibido tarjetas.

    Devuelve (suspendidos, amarillas_en_curso). Las amarillas se acumulan durante todo
    el torneo; la doble amarilla cuenta como roja y no suma a la acumulación.
    """
    rules = rules or DisciplineRules()
    pending: dict[int, int] = {}
    reason: dict[int, str] = {}
    yellows: dict[int, int] = {}
    for match_cards in history:
        # sanciones vigentes al comenzar este partido: lo cumplen sentados
        for p in [p for p, n in pending.items() if n > 0]:
            pending[p] -= 1
        for c in match_cards:
            if c.type == "yellow":
                yellows[c.player_id] = yellows.get(c.player_id, 0) + 1
                n = rules.yellows_for_suspension
                if n and yellows[c.player_id] % n == 0:
                    pending[c.player_id] = pending.get(c.player_id, 0) + rules.yellow_matches
                    reason[c.player_id] = "yellows"
            elif c.type in ("red", "second_yellow"):
                pending[c.player_id] = pending.get(c.player_id, 0) + rules.red_matches
                reason[c.player_id] = "red"
    suspended = {
        p: Suspension(p, n, reason[p]) for p, n in pending.items() if n > 0
    }
    n = rules.yellows_for_suspension
    running = {p: (y % n if n else y) for p, y in yellows.items()}
    return suspended, running
