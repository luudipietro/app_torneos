from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str
    name: str


class TournamentIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    start_date: date | None = None
    rules: dict = {}


class TournamentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    start_date: date | None = None
    rules: dict | None = None


class TournamentOut(ORM):
    id: int
    name: str
    start_date: date | None
    rules: dict
    my_role: str = "admin"  # admin | scorer


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    crest_url: str | None = None
    delegate: str | None = None
    seed: int | None = Field(default=None, ge=1)


class TeamPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    crest_url: str | None = None
    delegate: str | None = None
    seed: int | None = Field(default=None, ge=1)


class TeamOut(ORM):
    id: int
    tournament_id: int
    name: str
    crest_url: str | None
    delegate: str | None
    seed: int | None


class PlayerIn(BaseModel):
    enabled: bool = True
    name: str = Field(min_length=1, max_length=120)
    dni: str = Field(min_length=6, max_length=20)
    birth_date: date | None = None
    number: int | None = Field(default=None, ge=0, le=999)
    position: str | None = None
    photo_url: str | None = None


class PlayerPatch(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    dni: str | None = Field(default=None, min_length=6, max_length=20)
    birth_date: date | None = None
    number: int | None = Field(default=None, ge=0, le=999)
    position: str | None = None
    photo_url: str | None = None


class PlayerOut(ORM):
    id: int
    enabled: bool
    team_id: int
    name: str
    dni: str
    birth_date: date | None
    number: int | None
    position: str | None
    photo_url: str | None


class LayoutOut(BaseModel):
    n_groups: int
    sizes: list[int]
    balanced: bool


class GroupStageIn(BaseModel):
    name: str = "Fase de grupos"
    n_groups: int = Field(ge=1, le=26)  # nombres A..Z
    double_round: bool = False
    seed: int | None = None  # semilla del sorteo (reproducible)


class GroupOut(BaseModel):
    id: int
    name: str
    team_ids: list[int]


class StageOut(BaseModel):
    id: int
    order: int
    type: str
    name: str
    config: dict
    groups: list[GroupOut]


class MatchOut(ORM):
    id: int
    stage_id: int
    group_id: int | None
    round: int
    home_team_id: int | None
    away_team_id: int | None
    home_goals: int | None
    away_goals: int | None
    status: str
    assignee_ids: list[int] = []
    home_pens: int | None = None
    away_pens: int | None = None
    is_knockout: bool = False
    is_third_place: bool = False
    scheduled_at: datetime | None = None
    venue: str | None = None


class ResultIn(BaseModel):
    home_goals: int = Field(ge=0, le=99)
    away_goals: int = Field(ge=0, le=99)
    home_pens: int | None = Field(default=None, ge=0, le=99)  # solo llaves, si hubo empate
    away_pens: int | None = Field(default=None, ge=0, le=99)


class FinishIn(BaseModel):
    home_pens: int | None = Field(default=None, ge=0, le=99)
    away_pens: int | None = Field(default=None, ge=0, le=99)


class StandingRow(BaseModel):
    team_id: int
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    points: int


class GroupStandings(BaseModel):
    group_id: int
    name: str
    rows: list[StandingRow]


EVENT_TYPES = ("goal", "penalty_goal", "own_goal", "yellow", "red", "second_yellow")


class EventIn(BaseModel):
    player_id: int
    type: str = Field(pattern="^(goal|penalty_goal|own_goal|yellow|red|second_yellow)$")
    minute: int | None = Field(default=None, ge=0, le=130)
    client_id: str | None = Field(default=None, max_length=64)


class EventOut(ORM):
    id: int
    client_id: str | None = None
    team_id: int
    player_id: int
    type: str
    minute: int | None


class SheetOut(ORM):
    id: int
    content_type: str


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    user_id: int
    author: str
    text: str
    created_at: datetime


class MatchDetail(MatchOut):
    events: list[EventOut]
    sheets: list[SheetOut]
    comments: list[CommentOut]


class SuspensionOut(BaseModel):
    remaining: int
    reason: str  # "yellows" | "red"


class LineupPlayer(BaseModel):
    player_id: int
    name: str
    dni: str
    number: int | None
    has_photo: bool
    enabled: bool
    present: bool
    verified_by: str | None
    verified_at: datetime | None
    suspension: SuspensionOut | None
    yellows: int  # amarillas acumuladas en curso


class LineupSide(BaseModel):
    team_id: int
    team_name: str
    players: list[LineupPlayer]
    present_count: int


class LineupOut(BaseModel):
    match_id: int
    status: str
    home: LineupSide
    away: LineupSide


class OnsitePlayerIn(PlayerIn):
    team_id: int


class TournamentSuspension(BaseModel):
    team_id: int
    team_name: str
    player_id: int
    player_name: str
    remaining: int
    reason: str


class MemberIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: str = Field(default="scorer", pattern="^(scorer|admin)$")


class MemberOut(BaseModel):
    user_id: int
    name: str
    email: str
    role: str


class InvitationOut(ORM):
    id: int
    email: str
    role: str


class MembersOut(BaseModel):
    members: list[MemberOut]
    invitations: list[InvitationOut]


class AssignIn(BaseModel):
    user_ids: list[int]


class BulkAssignIn(BaseModel):
    user_id: int
    match_ids: list[int] = Field(min_length=1, max_length=500)


class ExtraIn(BaseModel):
    position: int = Field(ge=1, le=20)
    count: int = Field(ge=1, le=64)


class CupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    positions: list[int] = Field(default=[], max_length=20)
    extra: list[ExtraIn] = Field(default=[], max_length=5)


class KnockoutIn(BaseModel):
    cups: list[CupIn] = Field(min_length=1, max_length=4)
    third_place: bool = True
    avoid_same_group: bool = True


class PlanOut(BaseModel):
    label: str
    cups: list[CupIn]


class EntrantOut(BaseModel):
    seed: int
    team_id: int
    group_id: int
    group_name: str
    position: int
    points: int
    gd: int


class CupPreview(BaseModel):
    name: str
    size: int  # tamaño de la llave (potencia de 2)
    byes: int
    rounds: int
    entrants: list[EntrantOut]


class KnockoutPreview(BaseModel):
    unplayed: int  # partidos de grupos que faltan cerrar
    cups: list[CupPreview]


class SyncOpIn(BaseModel):
    id: str = Field(min_length=8, max_length=64)  # uuid generado en el cliente
    type: str = Field(pattern=r"^(lineup\.mark|lineup\.unmark|event\.add|event\.delete|comment\.add|match\.finish)$")
    match_id: int
    payload: dict = {}


class SyncIn(BaseModel):
    ops: list[SyncOpIn] = Field(max_length=100)


class SyncResult(BaseModel):
    id: str
    status: str  # ok | rejected | error
    code: int
    message: str | None = None
    duplicate: bool = False


class SyncOut(BaseModel):
    results: list[SyncResult]


class Bundle(BaseModel):
    """Todo lo que el planillero necesita de un partido para trabajar sin conexión."""

    detail: MatchDetail
    lineup: LineupOut | None


class ScheduleIn(BaseModel):
    scheduled_at: datetime | None = None  # hora local del torneo, sin zona horaria
    venue: str | None = Field(default=None, max_length=120)


class ScorerRow(BaseModel):
    rank: int
    player_id: int
    name: str
    team_id: int
    team_name: str
    goals: int
    penalties: int  # de esos goles, cuántos fueron de penal


class CardRow(BaseModel):
    player_id: int
    name: str
    team_id: int
    team_name: str
    yellow: int
    red: int  # incluye las expulsiones por doble amarilla


class DefenseRow(BaseModel):
    rank: int
    team_id: int
    team_name: str
    played: int
    goals_against: int
    average: float  # goles recibidos por partido
    clean_sheets: int  # partidos sin recibir goles


class FairPlayRow(BaseModel):
    team_id: int
    team_name: str
    yellow: int
    red: int
    points: int  # amarilla = 1, roja = 3 (menos es mejor)


class StatsOut(BaseModel):
    matches_played: int
    total_goals: int
    goals_per_match: float
    scorers: list[ScorerRow]
    cards: list[CardRow]
    defense: list[DefenseRow]
    fair_play: list[FairPlayRow]
    suspensions: list[TournamentSuspension]


class PublicTeam(BaseModel):
    id: int
    name: str
    crest_url: str | None


class PublicMatch(ORM):
    id: int
    round: int
    group_id: int | None
    home_team_id: int | None
    away_team_id: int | None
    home_goals: int | None
    away_goals: int | None
    home_pens: int | None
    away_pens: int | None
    status: str
    scheduled_at: datetime | None
    venue: str | None
    is_third_place: bool


class PublicGroup(BaseModel):
    id: int
    name: str
    standings: list[StandingRow]
    matches: list[PublicMatch]


class PublicCup(BaseModel):
    name: str
    rounds: int
    matches: list[PublicMatch]


class PublicOut(BaseModel):
    name: str
    start_date: date | None
    teams: list[PublicTeam]
    groups_name: str | None
    groups: list[PublicGroup]
    cups: list[PublicCup]
    stats: StatsOut
    updated_at: datetime


class PublicEvent(BaseModel):
    minute: int | None
    type: str
    player_name: str
    team_id: int


class PublicMatchDetail(BaseModel):
    match: PublicMatch
    events: list[PublicEvent]


class PublicLinkIn(BaseModel):
    enabled: bool
    regenerate: bool = False


class PublicLinkOut(BaseModel):
    enabled: bool
    token: str | None
