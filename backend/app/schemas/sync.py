from datetime import date, datetime

from pydantic import BaseModel, Field

from .lineup import LineupOut
from .matches import MatchDetail


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
