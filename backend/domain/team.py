from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Team:
    name: str
    id: int = 0
    seed: int | None = None  # cabeza de serie (1 = mejor); None = sin serie
