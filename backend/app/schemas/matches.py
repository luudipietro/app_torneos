from datetime import date, datetime

from pydantic import BaseModel, Field

from .base import ORM


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


class ScheduleIn(BaseModel):
    scheduled_at: datetime | None = None  # hora local del torneo, sin zona horaria
    venue: str | None = Field(default=None, max_length=120)
