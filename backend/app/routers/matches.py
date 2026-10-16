from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user
from .. import bracket
from ..media import delete_media, media_path, save_image

router = APIRouter(tags=["partidos"])

HOME_GOALS = ("goal", "penalty_goal")


def _match(db: Session, user: models.User, match_id: int) -> tuple[models.Match, str]:
    """Devuelve el partido y el rol del usuario en su torneo (404 si no es miembro; los
    planilleros solo acceden a los partidos que tienen asignados)."""
    m = db.get(models.Match, match_id)
    member = db.get(models.Member, (m.tournament_id, user.id)) if m else None
    if not m or not member:
        raise HTTPException(404, "Partido no encontrado")
    if member.role == "scorer" and user.id not in m.assignee_ids:
        raise HTTPException(403, "No estás asignado a este partido")
    return m, member.role


def _writable(m: models.Match, role: str) -> None:
    """Partido cerrado: solo el organizador puede modificarlo."""
    if m.status == "finished" and role != "admin":
        raise HTTPException(403, "El partido está cerrado; solo el organizador puede modificarlo")


def _recompute_score(db: Session, m: models.Match) -> None:
    events = db.scalars(
        select(models.MatchEvent).where(
            models.MatchEvent.match_id == m.id,
            models.MatchEvent.type.in_((*HOME_GOALS, "own_goal")),
        )
    ).all()
    home = away = 0
    for e in events:
        # el gol en contra suma al rival del equipo del jugador
        scorer = e.team_id if e.type in HOME_GOALS else (
            m.away_team_id if e.team_id == m.home_team_id else m.home_team_id
        )
        if scorer == m.home_team_id:
            home += 1
        else:
            away += 1
    m.home_goals, m.away_goals = home, away
    if m.status == "scheduled":
        m.status = "in_progress"


def _detail(db: Session, m: models.Match) -> schemas.MatchDetail:
    events = db.scalars(
        select(models.MatchEvent).where(models.MatchEvent.match_id == m.id)
        .order_by(models.MatchEvent.minute.is_(None), models.MatchEvent.minute, models.MatchEvent.id)
    ).all()
    sheets = db.scalars(select(models.MatchSheet).where(models.MatchSheet.match_id == m.id).order_by(models.MatchSheet.id)).all()
    rows = db.execute(
        select(models.MatchComment, models.User.name)
        .join(models.User, models.User.id == models.MatchComment.user_id)
        .where(models.MatchComment.match_id == m.id)
        .order_by(models.MatchComment.id)
    ).all()
    base = schemas.MatchOut.model_validate(m).model_dump()
    return schemas.MatchDetail(
        **base,
        events=[schemas.EventOut.model_validate(e) for e in events],
        sheets=[schemas.SheetOut.model_validate(s) for s in sheets],
        comments=[
            schemas.CommentOut(id=c.id, user_id=c.user_id, author=name, text=c.text, created_at=c.created_at)
            for c, name in rows
        ],
    )


@router.get("/matches/{match_id}", response_model=schemas.MatchDetail)
def match_detail(match_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m, _ = _match(db, user, match_id)
    return _detail(db, m)


# ---------- cierre ----------
@router.post("/matches/{match_id}/finish", response_model=schemas.MatchOut)
def finish_match(
    match_id: int,
    body: schemas.FinishIn | None = None,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m, role = _match(db, user, match_id)
    _writable(m, role)
    body = body or schemas.FinishIn()
    bracket.close_match(db, m, body.home_pens, body.away_pens)
    db.commit()
    return m


@router.post("/matches/{match_id}/reopen", response_model=schemas.MatchOut)
def reopen_match(match_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    m, role = _match(db, user, match_id)
    if role != "admin":
        raise HTTPException(403, "Requiere rol de organizador")
    m.status = "in_progress"
    bracket.sync(db, m)  # el ganador deja de avanzar
    db.commit()
    return m


# ---------- eventos ----------
@router.post("/matches/{match_id}/events", response_model=schemas.MatchDetail, status_code=201)
def add_event(
    match_id: int,
    body: schemas.EventIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m, role = _match(db, user, match_id)
    _writable(m, role)
    if body.client_id and db.scalar(select(models.MatchEvent.id).where(
            models.MatchEvent.client_id == body.client_id, models.MatchEvent.match_id == m.id)):
        return _detail(db, m)  # reintento de algo ya cargado
    player = db.get(models.Player, body.player_id)
    if not player or player.team_id not in (m.home_team_id, m.away_team_id):
        raise HTTPException(422, "El jugador no pertenece a ninguno de los equipos del partido")
    taken = db.scalars(select(models.MatchLineup.player_id).where(
        models.MatchLineup.match_id == m.id, models.MatchLineup.team_id == player.team_id)).all()
    t = db.get(models.Tournament, m.tournament_id)
    if (taken or (t.rules or {}).get("require_lineup")) and player.id not in taken:
        raise HTTPException(422, "El jugador no está en la lista de buena fe de este partido")
    db.add(models.MatchEvent(
        match_id=m.id, team_id=player.team_id, player_id=player.id,
        type=body.type, minute=body.minute, created_by=user.id, client_id=body.client_id,
    ))
    db.flush()
    _recompute_score(db, m)
    bracket.sync(db, m)
    db.commit()
    return _detail(db, m)


@router.delete("/matches/{match_id}/events/{event_id}", response_model=schemas.MatchDetail)
def delete_event(
    match_id: int, event_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    m, role = _match(db, user, match_id)
    _writable(m, role)
    e = db.get(models.MatchEvent, event_id)
    if not e or e.match_id != m.id:
        raise HTTPException(404, "Evento no encontrado")
    db.delete(e)
    db.flush()
    _recompute_score(db, m)
    bracket.sync(db, m)
    db.commit()
    return _detail(db, m)


# ---------- foto de planilla ----------
@router.post("/matches/{match_id}/sheets", response_model=schemas.MatchDetail, status_code=201)
async def upload_sheet(
    match_id: int,
    file: UploadFile,
    client_id: str | None = Form(default=None, max_length=64),
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m, role = _match(db, user, match_id)
    _writable(m, role)
    if client_id and db.scalar(select(models.MatchSheet.id).where(models.MatchSheet.client_id == client_id)):
        return _detail(db, m)  # reintento de una foto ya subida
    rel, ctype = await save_image(file, f"sheets/{m.id}")
    db.add(models.MatchSheet(match_id=m.id, path=rel, content_type=ctype, uploaded_by=user.id, client_id=client_id))
    db.commit()
    return _detail(db, m)


def _sheet(db: Session, user: models.User, sheet_id: int):
    s = db.get(models.MatchSheet, sheet_id)
    if not s:
        raise HTTPException(404, "Planilla no encontrada")
    m, role = _match(db, user, s.match_id)
    return s, m, role


@router.get("/sheets/{sheet_id}/file")
def sheet_file(sheet_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    s, _, _ = _sheet(db, user, sheet_id)
    path = media_path(s.path)
    if not path.is_file():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(path, media_type=s.content_type)


@router.delete("/sheets/{sheet_id}", response_model=schemas.MatchDetail)
def delete_sheet(sheet_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    s, m, role = _sheet(db, user, sheet_id)
    _writable(m, role)
    delete_media(s.path)
    db.delete(s)
    db.commit()
    return _detail(db, m)


# ---------- comentarios ----------
@router.post("/matches/{match_id}/comments", response_model=schemas.MatchDetail, status_code=201)
def add_comment(
    match_id: int,
    body: schemas.CommentIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m, _ = _match(db, user, match_id)  # se puede comentar aunque esté cerrado
    db.add(models.MatchComment(match_id=m.id, user_id=user.id, text=body.text.strip()))
    db.commit()
    return _detail(db, m)


@router.delete("/matches/{match_id}/comments/{comment_id}", response_model=schemas.MatchDetail)
def delete_comment(
    match_id: int, comment_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    m, role = _match(db, user, match_id)
    c = db.get(models.MatchComment, comment_id)
    if not c or c.match_id != m.id:
        raise HTTPException(404, "Comentario no encontrado")
    if c.user_id != user.id and role != "admin":
        raise HTTPException(403, "Solo el autor o el organizador pueden borrarlo")
    db.delete(c)
    db.commit()
    return _detail(db, m)
