from pydantic import BaseModel

from .lineup import TournamentSuspension


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
