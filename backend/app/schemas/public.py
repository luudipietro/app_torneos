from datetime import date, datetime

from pydantic import BaseModel, Field

from .base import ORM
from .stages import StandingRow
from .stats import StatsOut


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
    total_rounds: int | None = None  # mayor que ``rounds`` si la fase se corta
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
