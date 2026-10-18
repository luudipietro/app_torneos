from pydantic import BaseModel, Field, model_validator


class LayoutOut(BaseModel):
    n_groups: int
    sizes: list[int]
    balanced: bool


class GroupStageIn(BaseModel):
    """Crea la fase de grupos: sorteando (``n_groups``) o con grupos armados a mano (``groups``)."""

    name: str = "Fase de grupos"
    n_groups: int | None = Field(default=None, ge=1, le=26)  # nombres A..Z
    groups: list[list[int]] | None = Field(default=None, max_length=26)  # ids de equipo por grupo
    double_round: bool = False
    seed: int | None = None  # semilla del sorteo (reproducible)

    @model_validator(mode="after")
    def _one_way(self):
        if self.groups is None and self.n_groups is None:
            raise ValueError("Indicá la cantidad de grupos o los equipos de cada grupo")
        return self


class DrawIn(BaseModel):
    """Pide un sorteo sin guardarlo; ``fixed`` ubica equipos a mano (id de equipo -> índice de grupo)."""

    n_groups: int = Field(ge=1, le=26)
    seed: int | None = None
    fixed: dict[int, int] = {}


class DrawStepOut(BaseModel):
    team_id: int
    group: int  # índice del grupo (0 = A)


class DrawOut(BaseModel):
    steps: list[DrawStepOut]  # los equipos sorteados, en el orden en que salen
    groups: list[list[int]]  # resultado final: ids de equipo por grupo


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
