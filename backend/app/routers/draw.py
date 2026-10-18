"""Sorteo de grupos (automático, manual o mixto) y generación del fixture."""
from string import ascii_uppercase

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from domain.fixture import round_robin
from domain.groups import draw_steps, suggest_layouts
from domain.team import Team

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from .stages import _stage_out, _teams

router = APIRouter(tags=["sorteo"])


def _domain_teams(teams: list[models.Team]) -> list[Team]:
    return [Team(name=m.name, id=m.id, seed=m.seed) for m in teams]


@router.get("/tournaments/{tid}/layouts", response_model=list[schemas.LayoutOut])
def layouts(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Distribuciones de grupos sugeridas según la cantidad de equipos cargados."""
    tournament_access(db, user, tid, admin=False)
    n = len(_teams(db, tid))
    if n < 2:
        raise HTTPException(422, "Cargá al menos 2 equipos")
    return [
        schemas.LayoutOut(n_groups=l.n_groups, sizes=list(l.sizes), balanced=l.balanced)
        for l in suggest_layouts(n)
    ]


@router.post("/tournaments/{tid}/stages/groups/draw", response_model=schemas.DrawOut)
def draw(
    tid: int,
    body: schemas.DrawIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Sortea los equipos que no estén ubicados a mano, sin guardar nada.

    Devuelve el orden en que van saliendo para poder mostrarlo uno a uno; el organizador
    confirma (o corrige a mano) con ``POST /stages/groups`` indicando ``groups``.
    """
    tournament_access(db, user, tid, admin=True)
    teams = _teams(db, tid)
    if body.n_groups * 2 > len(teams):
        raise HTTPException(422, "Cada grupo necesita al menos 2 equipos")
    try:
        steps = draw_steps(_domain_teams(teams), body.n_groups, body.seed, body.fixed)
    except ValueError as e:
        raise HTTPException(422, str(e))
    groups: list[list[int]] = [[] for _ in range(body.n_groups)]
    for team_id, g in body.fixed.items():
        groups[g].append(team_id)
    for t, g in steps:
        groups[g].append(t.id)
    return schemas.DrawOut(steps=[schemas.DrawStepOut(team_id=t.id, group=g) for t, g in steps], groups=groups)


def _manual_groups(teams: list[models.Team], groups: list[list[int]]) -> list[list[int]]:
    ids = {m.id for m in teams}
    flat = [i for g in groups for i in g]
    if len(set(flat)) != len(flat):
        raise HTTPException(422, "Un equipo está en más de un grupo")
    if set(flat) - ids:
        raise HTTPException(422, "Hay equipos que no pertenecen al torneo")
    if ids - set(flat):
        raise HTTPException(422, f"Faltan ubicar {len(ids - set(flat))} equipos en algún grupo")
    if any(len(g) < 2 for g in groups):
        raise HTTPException(422, "Cada grupo necesita al menos 2 equipos")
    return groups


@router.post("/tournaments/{tid}/stages/groups", response_model=schemas.StageOut, status_code=201)
def create_group_stage(
    tid: int,
    body: schemas.GroupStageIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Crea los grupos (sorteados o armados a mano) y genera todos los partidos de la fase."""
    t = tournament_access(db, user, tid, admin=True)
    if t.stages:
        raise HTTPException(409, "El torneo ya tiene etapas; borrá la existente para rehacer el sorteo")
    teams = _teams(db, tid)
    if body.groups is not None:
        member_ids = _manual_groups(teams, body.groups)
    else:
        n = body.n_groups or 0
        if n * 2 > len(teams):
            raise HTTPException(422, "Cada grupo necesita al menos 2 equipos")
        member_ids = [[] for _ in range(n)]
        for team, g in draw_steps(_domain_teams(teams), n, body.seed):
            member_ids[g].append(team.id)

    stage = models.Stage(
        tournament_id=tid, order=1, type="groups", name=body.name,
        config={"n_groups": len(member_ids), "double_round": body.double_round, "seed": body.seed,
                "manual": body.groups is not None},
    )
    db.add(stage)
    for i, ids in enumerate(member_ids):
        g = models.Group(name=f"Grupo {ascii_uppercase[i]}")
        g.teams = [models.GroupTeam(team_id=team_id) for team_id in ids]
        stage.groups.append(g)
    db.flush()
    for g, ids in zip(stage.groups, member_ids):
        for rnd, matches in enumerate(round_robin(ids, body.double_round), 1):
            for home, away in matches:
                db.add(models.Match(
                    tournament_id=tid, stage_id=stage.id, group_id=g.id,
                    round=rnd, home_team_id=home, away_team_id=away,
                ))
    db.commit()
    return _stage_out(stage)
