from datetime import date, datetime

from pydantic import BaseModel, Field

from .base import ORM


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
