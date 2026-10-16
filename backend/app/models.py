from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))


class Tournament(Base):
    __tablename__ = "tournaments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    # reglamento: puntos, desempates, amarillas para suspensión, etc.
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # link de la vista pública (solo lectura); nulo = vista pública desactivada
    public_token: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)

    members: Mapped[list[Member]] = relationship(cascade="all, delete-orphan")
    teams: Mapped[list[Team]] = relationship(cascade="all, delete-orphan")
    stages: Mapped[list[Stage]] = relationship(
        cascade="all, delete-orphan", order_by="Stage.order"
    )


class Member(Base):
    """Rol de un usuario dentro de un torneo: admin | scorer (planillero/veedor)."""

    __tablename__ = "tournament_members"
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("tournament_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    crest_url: Mapped[str | None] = mapped_column(String(300))
    delegate: Mapped[str | None] = mapped_column(String(120))
    seed: Mapped[int | None] = mapped_column(Integer)  # cabeza de serie

    players: Mapped[list[Player]] = relationship(cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"
    # un DNI no puede estar en dos equipos del mismo torneo (buena fe)
    __table_args__ = (UniqueConstraint("tournament_id", "dni"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    dni: Mapped[str] = mapped_column(String(20))
    birth_date: Mapped[date | None] = mapped_column(Date)
    number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(30))
    photo_url: Mapped[str | None] = mapped_column(String(300))
    photo_path: Mapped[str | None] = mapped_column(String(300))  # relativo a MEDIA_DIR
    # habilitado por el organizador (ficha médica, edad, documentación, etc.)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Stage(Base):
    __tablename__ = "stages"
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    order: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))  # groups | league | knockout
    name: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    groups: Mapped[list[Group]] = relationship(
        cascade="all, delete-orphan", order_by="Group.id"
    )


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(40))

    teams: Mapped[list[GroupTeam]] = relationship(cascade="all, delete-orphan")


class GroupTeam(Base):
    __tablename__ = "group_teams"
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    round: Mapped[int] = mapped_column(Integer)
    # nulos cuando el equipo aún no está definido (llaves, fase 3)
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))
    home_goals: Mapped[int | None] = mapped_column(Integer)
    away_goals: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    venue: Mapped[str | None] = mapped_column(String(120))
    # definición por penales (llaves): solo si el partido terminó empatado
    home_pens: Mapped[int | None] = mapped_column(Integer)
    away_pens: Mapped[int | None] = mapped_column(Integer)
    # llaves: {"key", "next": [match_id, "home"|"away"] | None, "loser_next": [...] | None, "third": bool}
    bracket: Mapped[dict | None] = mapped_column(JSON)

    assignments: Mapped[list[MatchAssignment]] = relationship(cascade="all, delete-orphan")

    @property
    def is_knockout(self) -> bool:
        return self.bracket is not None

    @property
    def is_third_place(self) -> bool:
        return bool((self.bracket or {}).get("third"))

    @property
    def assignee_ids(self) -> list[int]:
        return sorted(a.user_id for a in self.assignments)


class MatchEvent(Base):
    """Gol, tarjeta, etc. El equipo se deduce del jugador."""

    __tablename__ = "match_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    # goal | penalty_goal | own_goal | yellow | red | second_yellow
    type: Mapped[str] = mapped_column(String(20))
    minute: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # id generado por el cliente: permite reintentar sin duplicar y borrar lo cargado sin conexión
    client_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)


class MatchSheet(Base):
    """Foto de la planilla del partido."""

    __tablename__ = "match_sheets"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(300))  # relativo a MEDIA_DIR
    content_type: Mapped[str] = mapped_column(String(50))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    client_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)


class MatchComment(Base):
    __tablename__ = "match_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MatchLineup(Base):
    """Lista de buena fe: jugadores verificados como presentes en un partido."""

    __tablename__ = "match_lineups"
    __table_args__ = (UniqueConstraint("match_id", "player_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Invitation(Base):
    """Invitación pendiente: se convierte en Member cuando la persona se registra."""

    __tablename__ = "invitations"
    __table_args__ = (UniqueConstraint("tournament_id", "email"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(20))
    invited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MatchAssignment(Base):
    """Planillero/veedor asignado a un partido."""

    __tablename__ = "match_assignments"
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class SyncOp(Base):
    """Operación enviada por un cliente offline; evita aplicarla dos veces si se reintenta."""

    __tablename__ = "sync_ops"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_op_id: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    match_id: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(30))
    code: Mapped[int] = mapped_column(Integer)  # 200 = aplicada; >=400 = rechazada
    message: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
