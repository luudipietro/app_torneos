from datetime import date, datetime

from pydantic import BaseModel, Field

from .tournament import PlayerIn


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
