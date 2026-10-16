from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import current_user, tournament_access

router = APIRouter(tags=["equipo de trabajo"])


def accept_invitations(db: Session, user: models.User) -> None:
    """Convierte las invitaciones pendientes de este email en membresías."""
    for inv in db.scalars(select(models.Invitation).where(models.Invitation.email == user.email)).all():
        if not db.get(models.Member, (inv.tournament_id, user.id)):
            db.add(models.Member(tournament_id=inv.tournament_id, user_id=user.id, role=inv.role))
        db.delete(inv)


def _members_out(db: Session, tid: int) -> schemas.MembersOut:
    rows = db.execute(
        select(models.Member, models.User)
        .join(models.User, models.User.id == models.Member.user_id)
        .where(models.Member.tournament_id == tid)
        .order_by(models.Member.role, models.User.name)
    ).all()
    invs = db.scalars(select(models.Invitation).where(models.Invitation.tournament_id == tid).order_by(models.Invitation.id)).all()
    return schemas.MembersOut(
        members=[schemas.MemberOut(user_id=u.id, name=u.name, email=u.email, role=m.role) for m, u in rows],
        invitations=[schemas.InvitationOut.model_validate(i) for i in invs],
    )


@router.get("/tournaments/{tid}/members", response_model=schemas.MembersOut)
def list_members(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    tournament_access(db, user, tid, admin=True)
    return _members_out(db, tid)


@router.post("/tournaments/{tid}/members", response_model=schemas.MembersOut, status_code=201)
def invite(
    tid: int,
    body: schemas.MemberIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Suma a alguien al torneo. Si todavía no tiene cuenta queda invitado y entra al registrarse."""
    tournament_access(db, user, tid, admin=True)
    email = body.email.lower()
    target = db.scalar(select(models.User).where(models.User.email == email))
    if target:
        m = db.get(models.Member, (tid, target.id))
        if m:
            raise HTTPException(409, "Esa persona ya es parte del torneo")
        db.add(models.Member(tournament_id=tid, user_id=target.id, role=body.role))
    else:
        if db.scalar(select(models.Invitation.id).where(
                models.Invitation.tournament_id == tid, models.Invitation.email == email)):
            raise HTTPException(409, "Ya hay una invitación pendiente para ese email")
        db.add(models.Invitation(tournament_id=tid, email=email, role=body.role, invited_by=user.id))
    db.commit()
    return _members_out(db, tid)


@router.delete("/tournaments/{tid}/members/{user_id}", response_model=schemas.MembersOut)
def remove_member(
    tid: int, user_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    tournament_access(db, user, tid, admin=True)
    if user_id == user.id:
        raise HTTPException(409, "No podés sacarte a vos mismo del torneo")
    m = db.get(models.Member, (tid, user_id))
    if not m:
        raise HTTPException(404, "Miembro no encontrado")
    mine = select(models.Match.id).where(models.Match.tournament_id == tid)
    db.execute(delete(models.MatchAssignment).where(
        models.MatchAssignment.user_id == user_id, models.MatchAssignment.match_id.in_(mine)))
    db.delete(m)
    db.commit()
    return _members_out(db, tid)


@router.delete("/tournaments/{tid}/invitations/{inv_id}", response_model=schemas.MembersOut)
def cancel_invitation(
    tid: int, inv_id: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)
):
    tournament_access(db, user, tid, admin=True)
    inv = db.get(models.Invitation, inv_id)
    if not inv or inv.tournament_id != tid:
        raise HTTPException(404, "Invitación no encontrada")
    db.delete(inv)
    db.commit()
    return _members_out(db, tid)


# ---------- asignación a partidos ----------
def _require_members(db: Session, tid: int, user_ids: list[int]) -> None:
    ok = set(db.scalars(select(models.Member.user_id).where(
        models.Member.tournament_id == tid, models.Member.user_id.in_(user_ids))))
    if ok != set(user_ids):
        raise HTTPException(422, "Solo se puede asignar a miembros del torneo")


@router.put("/matches/{match_id}/assignments", response_model=schemas.MatchOut)
def set_assignments(
    match_id: int,
    body: schemas.AssignIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    m = db.get(models.Match, match_id)
    if not m:
        raise HTTPException(404, "Partido no encontrado")
    tournament_access(db, user, m.tournament_id, admin=True)
    ids = sorted(set(body.user_ids))
    _require_members(db, m.tournament_id, ids)
    m.assignments = [models.MatchAssignment(match_id=m.id, user_id=u) for u in ids]
    db.commit()
    return m


@router.post("/tournaments/{tid}/assignments", response_model=list[schemas.MatchOut])
def bulk_assign(
    tid: int,
    body: schemas.BulkAssignIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Suma a una persona a muchos partidos de una vez (por ejemplo, toda una fecha)."""
    tournament_access(db, user, tid, admin=True)
    _require_members(db, tid, [body.user_id])
    matches = db.scalars(select(models.Match).where(
        models.Match.tournament_id == tid, models.Match.id.in_(body.match_ids))).all()
    if len(matches) != len(set(body.match_ids)):
        raise HTTPException(404, "Algún partido no existe en este torneo")
    for m in matches:
        if body.user_id not in m.assignee_ids:
            m.assignments.append(models.MatchAssignment(match_id=m.id, user_id=body.user_id))
    db.commit()
    return matches


@router.get("/tournaments/{tid}/my-matches", response_model=list[schemas.MatchOut])
def my_matches(tid: int, user: models.User = Depends(current_user), db: Session = Depends(get_db)):
    tournament_access(db, user, tid, admin=False)
    q = (
        select(models.Match)
        .join(models.MatchAssignment, models.MatchAssignment.match_id == models.Match.id)
        .where(models.Match.tournament_id == tid, models.MatchAssignment.user_id == user.id)
        .order_by(models.Match.status == "finished", models.Match.stage_id, models.Match.round, models.Match.id)
    )
    return db.scalars(q).all()


@router.put("/matches/{match_id}/schedule", response_model=schemas.MatchOut)
def set_schedule(
    match_id: int,
    body: schemas.ScheduleIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Fecha, hora y cancha del partido (organizador)."""
    m = db.get(models.Match, match_id)
    if not m:
        raise HTTPException(404, "Partido no encontrado")
    tournament_access(db, user, m.tournament_id, admin=True)
    m.scheduled_at = body.scheduled_at.replace(tzinfo=None) if body.scheduled_at else None
    m.venue = (body.venue or "").strip() or None
    db.commit()
    return m
