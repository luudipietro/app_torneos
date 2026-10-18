from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.standings import Result, Rules, standings

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from .. import bracket
from .matches import _match, _writable

router = APIRouter(tags=["etapas"])


def _teams(db: Session, tid: int) -> list[models.Team]:
    return list(db.scalars(select(models.Team).where(models.Team.tournament_id == tid).order_by(models.Team.id)))


def _stage_out(s: models.Stage) -> schemas.StageOut:
    return schemas.StageOut(
        id=s.id, order=s.order, type=s.type, name=s.name, config=s.config,
        groups=[
            schemas.GroupOut(id=g.id, name=g.name, team_ids=sorted(gt.team_id for gt in g.teams))
            for g in s.groups
        ],
    )


def _rules(t: models.Tournament) -> Rules:
    r = t.rules or {}
    base = Rules()
    return Rules(
        win=r.get("win", base.win),
        draw=r.get("draw", base.draw),
        loss=r.get("loss", base.loss),
        tiebreakers=r.get("tiebreakers", base.tiebreakers),
    )


@router.get("/tournaments/{tid}/stages", response_model=list[schemas.StageOut])
def list_stages(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    t = tournament_access(db, user, tid, admin=False)
    return [_stage_out(s) for s in t.stages]


def _stage(db: Session, user: models.User, stage_id: int, admin: bool) -> models.Stage:
    s = db.get(models.Stage, stage_id)
    if not s:
        raise HTTPException(404, "Etapa no encontrada")
    tournament_access(db, user, s.tournament_id, admin)
    return s


@router.delete("/stages/{stage_id}", status_code=204)
def delete_stage(stage_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    s = _stage(db, user, stage_id, admin=True)
    later = db.query(models.Stage).filter(
        models.Stage.tournament_id == s.tournament_id, models.Stage.order > s.order).count()
    if later:
        raise HTTPException(409, "Primero borrá las etapas siguientes (llaves)")
    played = db.query(models.Match).filter(
        models.Match.stage_id == s.id, models.Match.home_goals.is_not(None)
    ).count()
    if played:
        raise HTTPException(409, "La etapa ya tiene resultados cargados")
    db.query(models.Match).filter_by(stage_id=s.id).delete()
    db.delete(s)
    db.commit()


@router.get("/stages/{stage_id}/matches", response_model=list[schemas.MatchOut])
def stage_matches(stage_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    s = _stage(db, user, stage_id, admin=False)
    q = select(models.Match).where(models.Match.stage_id == s.id).order_by(models.Match.group_id, models.Match.round, models.Match.id)
    return db.scalars(q).all()


@router.put("/matches/{match_id}/result", response_model=schemas.MatchOut)
def set_result(
    match_id: int,
    body: schemas.ResultIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m, role = _match(db, user, match_id)  # organizador o planillero asignado
    _writable(m, role)
    if db.query(models.MatchEvent).filter_by(match_id=m.id).count():
        raise HTTPException(409, "El partido tiene eventos cargados; el resultado se calcula con los goles")
    m.home_goals, m.away_goals = body.home_goals, body.away_goals
    bracket.close_match(db, m, body.home_pens, body.away_pens)
    db.commit()
    return m


def group_standings(db: Session, t: models.Tournament, stage: models.Stage) -> list[schemas.GroupStandings]:
    """Tabla de cada grupo de la etapa con el reglamento del torneo (usa solo partidos cerrados)."""
    rules = _rules(t)
    out = []
    for g in stage.groups:
        ids = [gt.team_id for gt in g.teams]
        results = [
            Result(m.home_team_id, m.away_team_id, m.home_goals, m.away_goals)
            for m in db.scalars(select(models.Match).where(models.Match.group_id == g.id, models.Match.status == "finished"))
            if m.home_goals is not None and m.away_goals is not None
        ]
        rows = standings(sorted(ids), results, rules)
        out.append(schemas.GroupStandings(
            group_id=g.id, name=g.name,
            rows=[
                schemas.StandingRow(
                    team_id=r.team, played=r.played, won=r.won, drawn=r.drawn, lost=r.lost,
                    gf=r.gf, ga=r.ga, gd=r.gd, points=r.points,
                )
                for r in rows
            ],
        ))
    return out


@router.get("/stages/{stage_id}/standings", response_model=list[schemas.GroupStandings])
def stage_standings(stage_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    s = _stage(db, user, stage_id, admin=False)
    return group_standings(db, db.get(models.Tournament, s.tournament_id), s)
