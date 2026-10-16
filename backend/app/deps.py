from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .db import get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    uid = decode_token(cred.credentials) if cred else None
    user = db.get(models.User, uid) if uid else None
    if not user:
        raise HTTPException(401, "No autenticado")
    return user


def tournament_access(
    db: Session, user: models.User, tournament_id: int, admin: bool
) -> models.Tournament:
    """Devuelve el torneo si el usuario es miembro (y admin, si se pide)."""
    t = db.get(models.Tournament, tournament_id)
    m = db.get(models.Member, (tournament_id, user.id)) if t else None
    if not t or not m:
        raise HTTPException(404, "Torneo no encontrado")
    if admin and m.role != "admin":
        raise HTTPException(403, "Requiere rol de organizador")
    return t
