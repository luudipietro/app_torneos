from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from domain.qualification import suggest_cup_plans

from .. import knockout_build as kb
from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from .stages import _stage_out

router = APIRouter(tags=["llaves"])


@router.get("/tournaments/{tid}/knockout/plans", response_model=list[schemas.PlanOut])
def plans(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Formatos de clasificación sugeridos según la forma de la fase de grupos."""
    t = tournament_access(db, user, tid, admin=True)
    stage = kb.group_stage(t)
    size = min(len(g.teams) for g in stage.groups)
    return [
        schemas.PlanOut(label=p.label, cups=[
            schemas.CupIn(name=c.name, positions=list(c.positions),
                          extra=[schemas.ExtraIn(position=p_, count=n) for p_, n in c.extra],
                          from_winners=list(c.from_winners), from_losers=list(c.from_losers),
                          max_rounds=c.max_rounds, third_place=c.third_place,
                          avoid_same_group=c.avoid_same_group)
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
    stage = kb.group_stage(t)
    entrants, unplayed = kb.entrants(db, t, stage)
    names = {g.id: g.name for g in stage.groups}
    out = []
    for plan in kb.plan(entrants, body, names):
        byes = {r.value for m in plan.matches if m.round > 1 for r in (m.home, m.away) if r.kind == "seed"}
        slots = []
        for i, sl in enumerate(plan.slots, 1):
            e = sl.team
            slots.append(
                schemas.EntrantOut(
                    seed=i, team_id=e.team, group_id=e.group, group_name=names[e.group],
                    position=e.position, points=e.row.points, gd=e.row.gd, code=sl.code, bye=i in byes)
                if e else schemas.EntrantOut(seed=i, label=sl.label, code=sl.code, bye=i in byes))
        pairs = [
            schemas.PairOut(home=slots[m.home.value - 1], away=slots[m.away.value - 1])
            for m in plan.matches if m.round == 1 and m.home.kind == "seed" and m.away.kind == "seed"
        ]
        out.append(schemas.CupPreview(
            name=plan.spec.name, size=plan.size, byes=plan.byes, rounds=plan.rounds,
            total_rounds=plan.total_rounds, entrants=slots, pairs=pairs))
    return schemas.KnockoutPreview(unplayed=unplayed, cups=out)


@router.post("/tournaments/{tid}/stages/knockout", response_model=list[schemas.StageOut], status_code=201)
def create_knockout(
    tid: int,
    body: schemas.KnockoutIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Arma las llaves (una por copa o fase) con los clasificados de la fase de grupos."""
    t = tournament_access(db, user, tid, admin=True)
    stages = kb.build(db, t, body)
    db.commit()
    return [_stage_out(s) for s in stages]


@router.get("/tournaments/{tid}/knockout/config", response_model=schemas.KnockoutConfig | None)
def get_config(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Formato de llaves guardado en el torneo (None si todavía no se guardó ninguno)."""
    return kb.load_config(tournament_access(db, user, tid, admin=True))


@router.put("/tournaments/{tid}/knockout/config", response_model=schemas.KnockoutConfig)
def put_config(
    tid: int,
    body: schemas.KnockoutConfig,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Guarda el formato de llaves. Con ``auto_create`` las llaves se arman solas al cerrar el último partido de grupos."""
    t = tournament_access(db, user, tid, admin=True)
    kb.save_config(t, body)
    db.commit()
    return body
