from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from ..discipline import team_status, tournament_suspensions
from .matches import _match, _writable

router = APIRouter(tags=["buena fe"])

REASON = {"yellows": "acumulación de amarillas", "red": "expulsión"}


def _side(db: Session, t: models.Tournament, m: models.Match, team_id: int) -> schemas.LineupSide:
    team = db.get(models.Team, team_id)
    suspended, yellows = team_status(db, t, team_id, before=m)
    present = {
        l.player_id: l
        for l in db.scalars(select(models.MatchLineup).where(
            models.MatchLineup.match_id == m.id, models.MatchLineup.team_id == team_id))
    }
    names = {u.id: u.name for u in db.scalars(
        select(models.User).where(models.User.id.in_([l.verified_by for l in present.values() if l.verified_by])))}
    players = db.scalars(
        select(models.Player).where(models.Player.team_id == team_id)
        .order_by(models.Player.number.is_(None), models.Player.number, models.Player.name)
    ).all()
    out = []
    for p in players:
        l = present.get(p.id)
        s = suspended.get(p.id)
        out.append(schemas.LineupPlayer(
            player_id=p.id, name=p.name, dni=p.dni, number=p.number, has_photo=bool(p.photo_path),
            enabled=p.enabled, present=l is not None,
            verified_by=names.get(l.verified_by) if l else None,
            verified_at=l.verified_at if l else None,
            suspension=schemas.SuspensionOut(remaining=s.remaining, reason=s.reason) if s else None,
            yellows=yellows.get(p.id, 0),
        ))
    return schemas.LineupSide(
        team_id=team_id, team_name=team.name, players=out, present_count=len(present)
    )


def _lineup(db: Session, m: models.Match) -> schemas.LineupOut:
    t = db.get(models.Tournament, m.tournament_id)
    if not m.home_team_id or not m.away_team_id:
        raise HTTPException(409, "El partido todavía no tiene los dos equipos definidos")
    return schemas.LineupOut(
        match_id=m.id, status=m.status,
        home=_side(db, t, m, m.home_team_id), away=_side(db, t, m, m.away_team_id),
    )


@router.get("/matches/{match_id}/lineup", response_model=schemas.LineupOut)
def get_lineup(match_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m, _ = _match(db, user, match_id)
    return _lineup(db, m)


def _check_eligible(db: Session, m: models.Match, p: models.Player) -> None:
    if p.team_id not in (m.home_team_id, m.away_team_id):
        raise HTTPException(422, "El jugador no pertenece a ninguno de los equipos del partido")
    if not p.enabled:
        raise HTTPException(409, f"{p.name} no está habilitado por el organizador")
    t = db.get(models.Tournament, m.tournament_id)
    s = team_status(db, t, p.team_id, before=m)[0].get(p.id)
    if s:
        raise HTTPException(409, f"{p.name} está suspendido por {REASON[s.reason]} ({s.remaining} partido/s)")


@router.put("/matches/{match_id}/lineup/{player_id}", response_model=schemas.LineupOut)
def mark_present(
    match_id: int, player_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    """El veedor verifica la identidad del jugador y lo incluye en la lista de buena fe."""
    m, role = _match(db, user, match_id)
    _writable(m, role)
    p = db.get(models.Player, player_id)
    if not p:
        raise HTTPException(404, "Jugador no encontrado")
    _check_eligible(db, m, p)
    if not db.scalar(select(models.MatchLineup.id).where(
            models.MatchLineup.match_id == m.id, models.MatchLineup.player_id == p.id)):
        db.add(models.MatchLineup(match_id=m.id, player_id=p.id, team_id=p.team_id, verified_by=user.id))
        db.commit()
    return _lineup(db, m)


@router.delete("/matches/{match_id}/lineup/{player_id}", response_model=schemas.LineupOut)
def unmark_present(
    match_id: int, player_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    m, role = _match(db, user, match_id)
    _writable(m, role)
    if db.scalar(select(models.MatchEvent.id).where(
            models.MatchEvent.match_id == m.id, models.MatchEvent.player_id == player_id)):
        raise HTTPException(409, "El jugador tiene incidencias cargadas en este partido")
    l = db.scalar(select(models.MatchLineup).where(
        models.MatchLineup.match_id == m.id, models.MatchLineup.player_id == player_id))
    if l:
        db.delete(l)
        db.commit()
    return _lineup(db, m)


@router.post("/matches/{match_id}/lineup/new-player", response_model=schemas.LineupOut, status_code=201)
def onsite_player(
    match_id: int,
    body: schemas.OnsitePlayerIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Alta de un jugador en la cancha: se crea y queda verificado en la lista."""
    m, role = _match(db, user, match_id)
    _writable(m, role)
    t = db.get(models.Tournament, m.tournament_id)
    if role != "admin" and not (t.rules or {}).get("allow_onsite_players", True):
        raise HTTPException(403, "El reglamento no permite altas de jugadores en la cancha")
    if body.team_id not in (m.home_team_id, m.away_team_id):
        raise HTTPException(422, "El equipo no juega este partido")
    data = body.model_dump(exclude={"team_id"})
    data["enabled"] = True
    p = models.Player(team_id=body.team_id, tournament_id=m.tournament_id, **data)
    db.add(p)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ese DNI ya está cargado en este torneo")
    db.add(models.MatchLineup(match_id=m.id, player_id=p.id, team_id=p.team_id, verified_by=user.id))
    db.commit()
    return _lineup(db, m)


@router.get("/tournaments/{tid}/suspensions", response_model=list[schemas.TournamentSuspension])
def suspensions(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Jugadores que no pueden jugar el próximo partido de su equipo."""
    return tournament_suspensions(db, tournament_access(db, user, tid, admin=False))
