"""Une el motor de disciplina (domain.discipline) con la base de datos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.discipline import CARD_TYPES, Card, DisciplineRules, Suspension, discipline_status

from . import models, schemas


def rules_for(t: models.Tournament) -> DisciplineRules:
    r = t.rules or {}
    base = DisciplineRules()
    return DisciplineRules(
        yellows_for_suspension=r.get("yellows_for_suspension", base.yellows_for_suspension),
        yellow_matches=r.get("yellow_suspension_matches", base.yellow_matches),
        red_matches=r.get("red_suspension_matches", base.red_matches),
    )


def team_status(
    db: Session, t: models.Tournament, team_id: int, before: models.Match | None = None
) -> tuple[dict[int, Suspension], dict[int, int]]:
    """Suspendidos y amarillas en curso de un equipo antes de ``before`` (o de su próximo partido)."""
    rows = db.execute(
        select(models.Match.id, models.Stage.order, models.Match.round)
        .join(models.Stage, models.Stage.id == models.Match.stage_id)
        .where(
            models.Match.tournament_id == t.id,
            models.Match.status == "finished",
            (models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id),
        )
    ).all()
    key = None
    if before is not None:
        stage_order = db.get(models.Stage, before.stage_id).order
        key = (stage_order, before.round, before.id)
    ordered = sorted((o, r, mid) for mid, o, r in rows)
    ids = [mid for o, r, mid in ordered if key is None or (o, r, mid) < key]
    cards: dict[int, list[Card]] = {mid: [] for mid in ids}
    if ids:
        events = db.scalars(
            select(models.MatchEvent).where(
                models.MatchEvent.match_id.in_(ids),
                models.MatchEvent.team_id == team_id,
                models.MatchEvent.type.in_(CARD_TYPES),
            ).order_by(models.MatchEvent.id)
        )
        for e in events:
            cards[e.match_id].append(Card(e.player_id, e.type))
    return discipline_status([cards[i] for i in ids], rules_for(t))


def tournament_suspensions(db: Session, t: models.Tournament) -> list[schemas.TournamentSuspension]:
    """Jugadores que no pueden jugar el próximo partido de su equipo."""
    out = []
    for team in db.scalars(select(models.Team).where(models.Team.tournament_id == t.id).order_by(models.Team.name)):
        sus, _ = team_status(db, t, team.id)
        for pid, s in sus.items():
            out.append(schemas.TournamentSuspension(
                team_id=team.id, team_name=team.name, player_id=pid,
                player_name=db.get(models.Player, pid).name, remaining=s.remaining, reason=s.reason,
            ))
    return out
