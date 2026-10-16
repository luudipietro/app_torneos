"""Sincronización de operaciones cargadas sin conexión.

El cliente guarda cada acción (marcar presente, gol, tarjeta, comentario, cierre) en una
cola local y la envía por lotes cuando vuelve la señal. Cada operación trae un id propio:
si el lote se reenvía (se cortó la respuesta), el servidor devuelve el resultado anterior
sin volver a aplicarla. Una operación que ya no se puede aplicar (el partido lo cerró el
organizador, el jugador quedó suspendido, etc.) se informa como rechazada y el servidor
conserva su versión: gana el estado del servidor.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user
from . import lineup, matches

router = APIRouter(tags=["sincronización"])


class _PlayerRef(BaseModel):
    player_id: int


class _EventRef(BaseModel):
    id: int | None = None
    client_id: str | None = Field(default=None, max_length=64)


def _apply(db: Session, user: models.User, op: schemas.SyncOpIn) -> None:
    """Ejecuta la operación con la misma lógica (y permisos) que los endpoints normales."""
    mid, p = op.match_id, op.payload
    if op.type == "lineup.mark":
        lineup.mark_present(mid, _PlayerRef(**p).player_id, user, db)
    elif op.type == "lineup.unmark":
        lineup.unmark_present(mid, _PlayerRef(**p).player_id, user, db)
    elif op.type == "event.add":
        matches.add_event(mid, schemas.EventIn(**p), user, db)
    elif op.type == "event.delete":
        ref = _EventRef(**p)
        q = select(models.MatchEvent).where(models.MatchEvent.match_id == mid)
        q = q.where(models.MatchEvent.id == ref.id) if ref.id else q.where(models.MatchEvent.client_id == ref.client_id)
        ev = db.scalar(q) if (ref.id or ref.client_id) else None
        if ev:  # si ya no existe, borrar es no hacer nada
            matches.delete_event(mid, ev.id, user, db)
    elif op.type == "comment.add":
        matches.add_comment(mid, schemas.CommentIn(**p), user, db)
    elif op.type == "match.finish":
        matches.finish_match(mid, schemas.FinishIn(**p), user, db)


def _msg(detail) -> str:
    return detail if isinstance(detail, str) else str(detail)


@router.post("/sync", response_model=schemas.SyncOut)
def sync(body: schemas.SyncIn, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    results: list[schemas.SyncResult] = []
    for op in body.ops:
        prev = db.scalar(select(models.SyncOp).where(models.SyncOp.client_op_id == op.id))
        if prev:
            if prev.user_id != user.id:
                results.append(schemas.SyncResult(id=op.id, status="rejected", code=409, message="Operación de otro usuario"))
            else:
                ok = prev.code < 400
                results.append(schemas.SyncResult(
                    id=op.id, status="ok" if ok else "rejected", code=prev.code, message=prev.message, duplicate=True))
            continue
        # el registro viaja en la misma transacción que la operación: si se aplica, queda anotada
        rec = models.SyncOp(client_op_id=op.id, user_id=user.id, match_id=op.match_id, type=op.type, code=200)
        db.add(rec)
        try:
            _apply(db, user, op)
            db.commit()
            results.append(schemas.SyncResult(id=op.id, status="ok", code=200))
        except HTTPException as e:
            db.rollback()
            db.add(models.SyncOp(
                client_op_id=op.id, user_id=user.id, match_id=op.match_id, type=op.type,
                code=e.status_code, message=_msg(e.detail)[:300]))
            db.commit()
            results.append(schemas.SyncResult(id=op.id, status="rejected", code=e.status_code, message=_msg(e.detail)))
        except (ValidationError, ValueError, TypeError) as e:  # payload mal formado: no tiene arreglo reintentando
            db.rollback()
            db.add(models.SyncOp(
                client_op_id=op.id, user_id=user.id, match_id=op.match_id, type=op.type,
                code=422, message="Datos inválidos"))
            db.commit()
            results.append(schemas.SyncResult(id=op.id, status="rejected", code=422, message="Datos inválidos"))
        except Exception:  # fallo del servidor: se corta el lote y el cliente reintenta más tarde
            db.rollback()
            results.append(schemas.SyncResult(id=op.id, status="error", code=500, message="Error del servidor"))
            break
    return schemas.SyncOut(results=results)


@router.get("/matches/{match_id}/bundle", response_model=schemas.Bundle)
def bundle(match_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    """Partido + lista de buena fe en una sola respuesta, para guardarlos en el dispositivo."""
    m, _ = matches._match(db, user, match_id)
    both = bool(m.home_team_id and m.away_team_id)
    return schemas.Bundle(detail=matches._detail(db, m), lineup=lineup._lineup(db, m) if both else None)
