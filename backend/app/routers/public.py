"""Vista pública de solo lectura de un torneo, accesible con un link secreto (sin login).

Solo expone lo que se publica en un fixture: equipos, partidos, resultados, tablas, llaves,
estadísticas y los nombres de quienes marcaron o fueron amonestados. Nunca DNI, fechas de
nacimiento, fotos, comentarios, planillas ni datos de usuarios.
"""
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from ..stats import compute_stats
from .stages import group_standings

router = APIRouter(tags=["vista pública"])

CACHE = "public, max-age=15"


def _by_token(db: Session, token: str) -> models.Tournament:
    t = db.scalar(select(models.Tournament).where(models.Tournament.public_token == token)) if token else None
    if not t:
        raise HTTPException(404, "El link no existe o fue desactivado")
    return t


def _matches(db: Session, stage_id: int, group_id: int | None = None) -> list[schemas.PublicMatch]:
    q = select(models.Match).where(models.Match.stage_id == stage_id)
    if group_id is not None:
        q = q.where(models.Match.group_id == group_id)
    q = q.order_by(models.Match.round, models.Match.id)
    return [schemas.PublicMatch.model_validate(m) for m in db.scalars(q)]


@router.get("/public/{token}", response_model=schemas.PublicOut)
def public_tournament(token: str, response: Response, db: Session = Depends(get_db)):
    t = _by_token(db, token)
    response.headers["Cache-Control"] = CACHE
    teams = db.scalars(select(models.Team).where(models.Team.tournament_id == t.id).order_by(models.Team.name)).all()
    gstage = next((s for s in t.stages if s.type == "groups"), None)
    groups = []
    if gstage:
        tables = {g.group_id: g.rows for g in group_standings(db, t, gstage)}
        groups = [
            schemas.PublicGroup(id=g.id, name=g.name, standings=tables[g.id], matches=_matches(db, gstage.id, g.id))
            for g in gstage.groups
        ]
    cups = [
        schemas.PublicCup(name=s.name, rounds=int(s.config.get("rounds", 1)), matches=_matches(db, s.id))
        for s in t.stages if s.type == "knockout"
    ]
    return schemas.PublicOut(
        name=t.name, start_date=t.start_date,
        teams=[schemas.PublicTeam(id=x.id, name=x.name, crest_url=x.crest_url) for x in teams],
        groups_name=gstage.name if gstage else None, groups=groups, cups=cups,
        stats=compute_stats(db, t), updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


@router.get("/public/{token}/matches/{match_id}", response_model=schemas.PublicMatchDetail)
def public_match(token: str, match_id: int, response: Response, db: Session = Depends(get_db)):
    t = _by_token(db, token)
    m = db.get(models.Match, match_id)
    if not m or m.tournament_id != t.id:
        raise HTTPException(404, "Partido no encontrado")
    response.headers["Cache-Control"] = CACHE
    rows = db.execute(
        select(models.MatchEvent, models.Player.name)
        .join(models.Player, models.Player.id == models.MatchEvent.player_id)
        .where(models.MatchEvent.match_id == m.id)
        .order_by(models.MatchEvent.minute.is_(None), models.MatchEvent.minute, models.MatchEvent.id)
    ).all()
    return schemas.PublicMatchDetail(
        match=schemas.PublicMatch.model_validate(m),
        events=[schemas.PublicEvent(minute=e.minute, type=e.type, player_name=name, team_id=e.team_id) for e, name in rows],
    )


# ---------- el organizador activa, desactiva o renueva el link ----------
@router.get("/tournaments/{tid}/public", response_model=schemas.PublicLinkOut)
def get_public_link(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    t = tournament_access(db, user, tid, admin=True)
    return schemas.PublicLinkOut(enabled=t.public_token is not None, token=t.public_token)


@router.put("/tournaments/{tid}/public", response_model=schemas.PublicLinkOut)
def set_public_link(
    tid: int,
    body: schemas.PublicLinkIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    t = tournament_access(db, user, tid, admin=True)
    if not body.enabled:
        t.public_token = None  # el link anterior deja de funcionar
    elif t.public_token is None or body.regenerate:
        t.public_token = secrets.token_urlsafe(12)  # 16 caracteres, no adivinable
    db.commit()
    return schemas.PublicLinkOut(enabled=t.public_token is not None, token=t.public_token)
