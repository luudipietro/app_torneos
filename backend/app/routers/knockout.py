from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.knockout import bracket_size, build_bracket, total_rounds
from domain.qualification import (
    CupSpec, Entrant, assign_cups, avoid_same_group, entrants_from_tables, suggest_cup_plans,
)
from domain.standings import Result, standings

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from .stages import _rules, _stage_out

router = APIRouter(tags=["llaves"])


def _group_stage(t: models.Tournament) -> models.Stage:
    s = next((s for s in t.stages if s.type == "groups"), None)
    if not s:
        raise HTTPException(409, "Primero hacé el sorteo de la fase de grupos")
    return s


def _entrants(db: Session, t: models.Tournament, stage: models.Stage) -> tuple[list[Entrant], int]:
    """Posiciones actuales de cada grupo y cuántos partidos de grupos faltan cerrar."""
    rules = _rules(t)
    tables = {}
    for g in stage.groups:
        ids = sorted(gt.team_id for gt in g.teams)
        results = [
            Result(m.home_team_id, m.away_team_id, m.home_goals, m.away_goals)
            for m in db.scalars(select(models.Match).where(
                models.Match.group_id == g.id, models.Match.status == "finished"))
            if m.home_goals is not None
        ]
        tables[g.id] = standings(ids, results, rules)
    unplayed = db.query(models.Match).filter(
        models.Match.stage_id == stage.id, models.Match.status != "finished").count()
    return entrants_from_tables(tables), unplayed


def _specs(body: schemas.KnockoutIn) -> list[CupSpec]:
    return [
        CupSpec(c.name, tuple(c.positions), tuple((e.position, e.count) for e in c.extra))
        for c in body.cups
    ]


def _plan(entrants: list[Entrant], body: schemas.KnockoutIn) -> list[list[Entrant]]:
    if len({c.name for c in body.cups}) != len(body.cups):
        raise HTTPException(422, "Cada copa necesita un nombre distinto")
    try:
        cups = assign_cups(entrants, _specs(body))
    except ValueError as e:
        raise HTTPException(422, str(e))
    for spec, cup in zip(body.cups, cups):
        if not 2 <= len(cup) <= 64:
            raise HTTPException(422, f"{spec.name}: necesita entre 2 y 64 equipos y tiene {len(cup)}")
        if not spec.positions and not spec.extra:
            raise HTTPException(422, f"{spec.name}: indicá qué puestos clasifican")
    if body.avoid_same_group:
        cups = [avoid_same_group(c, build_bracket(len(c), body.third_place)) for c in cups]
    return cups


@router.get("/tournaments/{tid}/knockout/plans", response_model=list[schemas.PlanOut])
def plans(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Formatos de clasificación sugeridos según la forma de la fase de grupos."""
    t = tournament_access(db, user, tid, admin=True)
    stage = _group_stage(t)
    size = min(len(g.teams) for g in stage.groups)
    return [
        schemas.PlanOut(label=p.label, cups=[
            schemas.CupIn(name=c.name, positions=list(c.positions),
                          extra=[schemas.ExtraIn(position=p_, count=n) for p_, n in c.extra])
            for c in p.cups])
        for p in suggest_cup_plans(len(stage.groups), size)
    ]


@router.post("/tournaments/{tid}/knockout/preview", response_model=schemas.KnockoutPreview)
def preview(
    tid: int,
    body: schemas.KnockoutIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Quiénes clasificarían con las posiciones actuales (provisorio hasta cerrar los grupos)."""
    t = tournament_access(db, user, tid, admin=True)
    stage = _group_stage(t)
    entrants, unplayed = _entrants(db, t, stage)
    names = {g.id: g.name for g in stage.groups}
    out = []
    for spec, cup in zip(body.cups, _plan(entrants, body)):
        n = len(cup)
        out.append(schemas.CupPreview(
            name=spec.name, size=bracket_size(n), byes=bracket_size(n) - n, rounds=total_rounds(n),
            entrants=[
                schemas.EntrantOut(
                    seed=i, team_id=e.team, group_id=e.group, group_name=names[e.group],
                    position=e.position, points=e.row.points, gd=e.row.gd)
                for i, e in enumerate(cup, 1)
            ],
        ))
    return schemas.KnockoutPreview(unplayed=unplayed, cups=out)


@router.post("/tournaments/{tid}/stages/knockout", response_model=list[schemas.StageOut], status_code=201)
def create_knockout(
    tid: int,
    body: schemas.KnockoutIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Arma una llave por copa con los clasificados de la fase de grupos."""
    t = tournament_access(db, user, tid, admin=True)
    gs = _group_stage(t)
    if any(s.type == "knockout" for s in t.stages):
        raise HTTPException(409, "Ya hay llaves; borralas para rehacerlas")
    entrants, unplayed = _entrants(db, t, gs)
    if unplayed:
        raise HTTPException(409, f"Faltan cerrar {unplayed} partidos de la fase de grupos")
    cups = _plan(entrants, body)

    stages = []
    for spec, cup in zip(body.cups, cups):
        bm = build_bracket(len(cup), body.third_place)
        stage = models.Stage(
            tournament_id=tid, order=gs.order + 1, type="knockout", name=spec.name,
            config={"cup": spec.name, "size": bracket_size(len(cup)), "third_place": body.third_place,
                    "rounds": total_rounds(len(cup))},
        )
        db.add(stage)
        db.flush()
        rows: dict[int, models.Match] = {}
        for b in bm:
            m = models.Match(
                tournament_id=tid, stage_id=stage.id, round=b.round,
                bracket={"key": b.key, "third": b.third_place, "next": None, "loser_next": None},
            )
            # los "byes" entran ya a la segunda ronda como cabezas de serie
            if b.home.kind == "seed":
                m.home_team_id = cup[b.home.value - 1].team
            if b.away.kind == "seed":
                m.away_team_id = cup[b.away.value - 1].team
            rows[b.key] = m
            db.add(m)
        db.flush()
        for b in bm:
            for slot, ref in (("home", b.home), ("away", b.away)):
                if ref.kind == "seed":
                    continue
                src = rows[ref.value]
                field = "next" if ref.kind == "winner" else "loser_next"
                src.bracket = {**src.bracket, field: [rows[b.key].id, slot]}
        stages.append(stage)
    db.commit()
    return [_stage_out(s) for s in stages]
