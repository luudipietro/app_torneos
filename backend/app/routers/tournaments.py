from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access
from ..stats import compute_stats
from ..media import delete_media, media_path, save_image

router = APIRouter(tags=["torneos"])


def _out(db: Session, user: models.User, t: models.Tournament) -> schemas.TournamentOut:
    out = schemas.TournamentOut.model_validate(t)
    out.my_role = db.get(models.Member, (t.id, user.id)).role
    return out


# ---------- torneos ----------
@router.post("/tournaments", response_model=schemas.TournamentOut, status_code=201)
def create_tournament(
    body: schemas.TournamentIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    t = models.Tournament(**body.model_dump())
    t.members.append(models.Member(user_id=user.id, role="admin"))
    db.add(t)
    db.commit()
    return _out(db, user, t)


@router.get("/tournaments", response_model=list[schemas.TournamentOut])
def list_tournaments(user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    q = (
        select(models.Tournament)
        .join(models.Member, models.Member.tournament_id == models.Tournament.id)
        .where(models.Member.user_id == user.id)
        .order_by(models.Tournament.id.desc())
    )
    return [_out(db, user, t) for t in db.scalars(q)]


@router.get("/tournaments/{tid}", response_model=schemas.TournamentOut)
def get_tournament(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    return _out(db, user, tournament_access(db, user, tid, admin=False))


@router.patch("/tournaments/{tid}", response_model=schemas.TournamentOut)
def patch_tournament(
    tid: int,
    body: schemas.TournamentPatch,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    t = tournament_access(db, user, tid, admin=True)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("rules") is not None and (t.rules or {}).get("knockout_plan"):
        changes["rules"] = {**changes["rules"], "knockout_plan": t.rules["knockout_plan"]}  # no pisar el formato de llaves
    for k, v in changes.items():
        setattr(t, k, v)
    db.commit()
    return _out(db, user, t)


@router.delete("/tournaments/{tid}", status_code=204)
def delete_tournament(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(tournament_access(db, user, tid, admin=True))
    db.commit()


# ---------- equipos ----------
def _commit_or_409(db: Session, msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, msg)


def _team(db: Session, user: models.User, team_id: int, admin: bool) -> models.Team:
    team = db.get(models.Team, team_id)
    if not team:
        raise HTTPException(404, "Equipo no encontrado")
    tournament_access(db, user, team.tournament_id, admin)
    return team


@router.post("/tournaments/{tid}/teams", response_model=schemas.TeamOut, status_code=201)
def create_team(
    tid: int,
    body: schemas.TeamIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    tournament_access(db, user, tid, admin=True)
    if db.query(models.Team).filter_by(tournament_id=tid).count() >= 64:
        raise HTTPException(422, "Máximo 64 equipos por torneo")
    if db.query(models.Stage).filter_by(tournament_id=tid).count():
        raise HTTPException(409, "No se pueden agregar equipos con el sorteo ya hecho")
    team = models.Team(tournament_id=tid, **body.model_dump())
    db.add(team)
    _commit_or_409(db, "Ya existe un equipo con ese nombre")
    return team


@router.get("/tournaments/{tid}/teams", response_model=list[schemas.TeamOut])
def list_teams(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    tournament_access(db, user, tid, admin=False)
    return db.scalars(select(models.Team).where(models.Team.tournament_id == tid).order_by(models.Team.name)).all()


@router.patch("/teams/{team_id}", response_model=schemas.TeamOut)
def patch_team(
    team_id: int,
    body: schemas.TeamPatch,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    team = _team(db, user, team_id, admin=True)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(team, k, v)
    _commit_or_409(db, "Ya existe un equipo con ese nombre")
    return team


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    team = _team(db, user, team_id, admin=True)
    if db.query(models.Stage).filter_by(tournament_id=team.tournament_id).count():
        raise HTTPException(409, "No se pueden quitar equipos con el sorteo ya hecho")
    db.delete(team)
    db.commit()


# ---------- jugadores ----------
@router.post("/teams/{team_id}/players", response_model=schemas.PlayerOut, status_code=201)
def create_player(
    team_id: int,
    body: schemas.PlayerIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    team = _team(db, user, team_id, admin=True)
    player = models.Player(team_id=team.id, tournament_id=team.tournament_id, **body.model_dump())
    db.add(player)
    _commit_or_409(db, "Ese DNI ya está cargado en este torneo")
    return player


@router.get("/teams/{team_id}/players", response_model=list[schemas.PlayerOut])
def list_players(team_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    team = _team(db, user, team_id, admin=False)
    return db.scalars(select(models.Player).where(models.Player.team_id == team.id).order_by(models.Player.number, models.Player.name)).all()


def _player(db: Session, user: models.User, player_id: int) -> models.Player:
    p = db.get(models.Player, player_id)
    if not p:
        raise HTTPException(404, "Jugador no encontrado")
    tournament_access(db, user, p.tournament_id, admin=True)
    return p


@router.patch("/players/{player_id}", response_model=schemas.PlayerOut)
def patch_player(
    player_id: int,
    body: schemas.PlayerPatch,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    p = _player(db, user, player_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    _commit_or_409(db, "Ese DNI ya está cargado en este torneo")
    return p


@router.delete("/players/{player_id}", status_code=204)
def delete_player(player_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    p = _player(db, user, player_id)
    delete_media(p.photo_path)
    db.delete(p)
    db.commit()


@router.post("/players/{player_id}/photo", response_model=schemas.PlayerOut)
async def upload_player_photo(
    player_id: int, file: UploadFile, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    p = _player(db, user, player_id)
    rel, _ = await save_image(file, f"players/{p.id}")
    delete_media(p.photo_path)
    p.photo_path = rel
    p.photo_url = f"/api/players/{p.id}/photo"
    db.commit()
    return p


@router.get("/players/{player_id}/photo")
def player_photo(player_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(models.Player, player_id)
    if not p or not p.photo_path:
        raise HTTPException(404, "Sin foto")
    tournament_access(db, user, p.tournament_id, admin=False)  # cualquier miembro (veedores)
    path = media_path(p.photo_path)
    if not path.is_file():
        raise HTTPException(404, "Sin foto")
    return FileResponse(path)


@router.get("/tournaments/{tid}/stats", response_model=schemas.StatsOut)
def tournament_stats(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Goleadores, tarjetas, valla menos vencida, fair play y suspendidos."""
    return compute_stats(db, tournament_access(db, user, tid, admin=False))
