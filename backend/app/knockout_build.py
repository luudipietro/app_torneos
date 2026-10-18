"""Armado de las llaves a partir de la fase de grupos, y creación automática con la config guardada."""
import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.phases import PhasePlan, plan_phases
from domain.qualification import CupSpec, Entrant, entrants_from_tables
from domain.standings import Result, standings

from . import models, schemas
from .routers.stages import _rules

log = logging.getLogger(__name__)
PLAN_KEY = "knockout_plan"  # dentro de tournament.rules


def group_stage(t: models.Tournament) -> models.Stage:
    s = next((s for s in t.stages if s.type == "groups"), None)
    if not s:
        raise HTTPException(409, "Primero hacé el sorteo de la fase de grupos")
    return s


def entrants(db: Session, t: models.Tournament, stage: models.Stage) -> tuple[list[Entrant], int]:
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


def specs(body: schemas.KnockoutIn) -> list[CupSpec]:
    return [
        CupSpec(
            c.name, tuple(c.positions), tuple((e.position, e.count) for e in c.extra),
            tuple(c.from_winners), tuple(c.from_losers), c.max_rounds, c.third_place, c.avoid_same_group,
            c.pairing, c.pairing_seed, tuple(c.manual_pairs),
        )
        for c in body.cups
    ]


def plan(ents: list[Entrant], body: schemas.KnockoutIn, group_names: dict[int, str]) -> list[PhasePlan]:
    try:
        return plan_phases(ents, specs(body), body.third_place, body.avoid_same_group, group_names)
    except ValueError as e:
        raise HTTPException(422, str(e))


def build(db: Session, t: models.Tournament, body: schemas.KnockoutIn) -> list[models.Stage]:
    """Crea una llave por copa o fase (no hace commit). Exige la fase de grupos terminada."""
    gs = group_stage(t)
    if any(s.type == "knockout" for s in t.stages):
        raise HTTPException(409, "Ya hay llaves; borralas para rehacerlas")
    ents, unplayed = entrants(db, t, gs)
    if unplayed:
        raise HTTPException(409, f"Faltan cerrar {unplayed} partidos de la fase de grupos")
    plans = plan(ents, body, {g.id: g.name for g in gs.groups})

    stages = []
    rows_of: dict[str, dict[int, models.Match]] = {}
    pending: list[tuple[tuple[str, int, str], models.Match, str]] = []  # (origen, partido destino, lado)
    for p in plans:
        name = p.spec.name
        stage = models.Stage(
            tournament_id=t.id, order=gs.order + 1, type="knockout", name=name,
            config={"cup": name, "size": p.size, "third_place": any(b.third_place for b in p.matches),
                    "rounds": p.rounds, "total_rounds": p.total_rounds, "limited": p.rounds < p.total_rounds},
        )
        db.add(stage)
        db.flush()
        rows: dict[int, models.Match] = {}
        for b in p.matches:
            m = models.Match(
                tournament_id=t.id, stage_id=stage.id, round=b.round,
                bracket={"key": b.key, "third": b.third_place, "next": None, "loser_next": None},
            )
            # los "byes" entran ya a la segunda ronda como cabezas de serie
            for side, ref in (("home", b.home), ("away", b.away)):
                if ref.kind != "seed":
                    continue
                slot = p.slots[ref.value - 1]
                if slot.team:
                    setattr(m, f"{side}_team_id", slot.team.team)
                else:  # lo completa el resultado de un partido de otra fase
                    pending.append((slot.source, m, side))
            rows[b.key] = m
            db.add(m)
        db.flush()
        for b in p.matches:
            for slot_name, ref in (("home", b.home), ("away", b.away)):
                if ref.kind == "seed":
                    continue
                src = rows[ref.value]
                field = "next" if ref.kind == "winner" else "loser_next"
                src.bracket = {**src.bracket, field: [rows[b.key].id, slot_name]}
        rows_of[name] = rows
        stages.append(stage)
    for (phase, key, kind), dest, side in pending:
        src = rows_of[phase][key]
        field = "next" if kind == "winner" else "loser_next"
        src.bracket = {**src.bracket, field: [dest.id, side]}
    return stages


def load_config(t: models.Tournament) -> schemas.KnockoutConfig | None:
    raw = (t.rules or {}).get(PLAN_KEY)
    if not raw:
        return None
    try:
        return schemas.KnockoutConfig.model_validate(raw)
    except ValueError:
        return None


def save_config(t: models.Tournament, cfg: schemas.KnockoutConfig | None) -> None:
    rules = dict(t.rules or {})
    if cfg is None:
        rules.pop(PLAN_KEY, None)
    else:
        rules[PLAN_KEY] = cfg.model_dump(mode="json")
    t.rules = rules  # asignar un dict nuevo para que SQLAlchemy detecte el cambio


def auto_create(db: Session, group_match: models.Match) -> None:
    """Si se cerró el último partido de grupos y hay una config guardada con creación automática, arma las llaves.

    Nunca interrumpe el cierre del partido: si la config no es válida con los resultados finales, no hace nada
    y el organizador la corrige y crea las llaves a mano.
    """
    if group_match.group_id is None:
        return
    t = db.get(models.Tournament, group_match.tournament_id)
    cfg = load_config(t) if t else None
    if not cfg or not cfg.auto_create:
        return
    db.flush()  # la sesión no hace autoflush: que el conteo vea este partido cerrado
    try:  # build() valida todo antes de escribir, así un error no deja llaves a medias
        build(db, t, cfg)
    except HTTPException as e:
        if e.status_code == 422:
            log.warning("No se pudieron crear las llaves automáticamente: %s", e.detail)
    except Exception:  # pragma: no cover - defensa: no romper el cierre del partido
        log.exception("Error creando las llaves automáticamente")
