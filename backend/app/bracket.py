"""Avance de ganadores en las llaves eliminatorias."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models


def winner_loser(m: models.Match) -> tuple[int | None, int | None]:
    """(ganador, perdedor) de un partido cerrado; (None, None) si no está definido."""
    if m.status != "finished" or m.home_goals is None or m.away_goals is None:
        return None, None
    if m.home_goals != m.away_goals:
        home_wins = m.home_goals > m.away_goals
    elif m.home_pens is not None and m.away_pens is not None and m.home_pens != m.away_pens:
        home_wins = m.home_pens > m.away_pens
    else:
        return None, None
    return (m.home_team_id, m.away_team_id) if home_wins else (m.away_team_id, m.home_team_id)


def sync(db: Session, m: models.Match) -> None:
    """Pone al ganador (y al perdedor, para el 3er puesto) en su próximo partido.

    Si el partido deja de estar definido (se reabrió, o cambió el resultado) vacía esos
    lugares. No toca partidos siguientes que ya empezaron: avisa con 409.
    """
    if not m.bracket:
        return
    winner, loser = winner_loser(m)
    for key, team in (("next", winner), ("loser_next", loser)):
        dest = m.bracket.get(key)
        if not dest:
            continue
        nxt = db.get(models.Match, dest[0])
        attr = f"{dest[1]}_team_id"
        if getattr(nxt, attr) == team:
            continue
        if nxt.status != "scheduled":
            raise HTTPException(409, "El partido siguiente de la llave ya empezó; no se puede cambiar este resultado")
        setattr(nxt, attr, team)


def close_match(db: Session, m: models.Match, home_pens: int | None = None, away_pens: int | None = None) -> None:
    """Cierra el partido. En llaves, un empate se define por penales."""
    if m.is_knockout:
        if not (m.home_team_id and m.away_team_id):
            raise HTTPException(409, "Todavía no están definidos los dos equipos de este partido")
        if m.home_goals is None:
            m.home_goals = m.away_goals = 0
        if m.home_goals == m.away_goals:
            if home_pens is None or away_pens is None or home_pens == away_pens:
                raise HTTPException(422, "Empate en una llave: cargá el resultado de los penales")
            m.home_pens, m.away_pens = home_pens, away_pens
        else:
            m.home_pens = m.away_pens = None
    elif m.home_goals is None:
        m.home_goals = m.away_goals = 0
    m.status = "finished"
    sync(db, m)
