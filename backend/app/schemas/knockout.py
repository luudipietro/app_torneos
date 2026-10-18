from pydantic import BaseModel, Field


class ExtraIn(BaseModel):
    position: int = Field(ge=1, le=20)
    count: int = Field(ge=1, le=64)


class CupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    positions: list[int] = Field(default=[], max_length=20)
    extra: list[ExtraIn] = Field(default=[], max_length=5)
    from_winners: list[str] = Field(default=[], max_length=8)  # fases previas cuyos ganadores entran acá
    from_losers: list[str] = Field(default=[], max_length=8)  # ... o cuyos perdedores entran acá
    max_rounds: int | None = Field(default=None, ge=1, le=6)  # corta la fase tras esas rondas
    third_place: bool | None = None  # None = el valor general
    avoid_same_group: bool | None = None
    pairing: str = Field(default="seeded", pattern="^(seeded|cross|random|manual)$")  # cómo se arman los cruces
    pairing_seed: int | None = None  # semilla del azar (para que la vista previa y las llaves coincidan)
    manual_pairs: list[tuple[str, str]] = Field(default=[], max_length=32)  # códigos como "1A" o "G1:Fase"


class KnockoutIn(BaseModel):
    cups: list[CupIn] = Field(min_length=1, max_length=8)
    third_place: bool = True
    avoid_same_group: bool = True


class KnockoutConfig(KnockoutIn):
    """Formato de llaves guardado en el torneo, con la opción de crearlas solas al terminar los grupos."""

    auto_create: bool = True
    picked: int | None = None  # formato sugerido elegido en la pantalla (solo para recordarlo)


class PlanOut(BaseModel):
    label: str
    cups: list[CupIn]


class EntrantOut(BaseModel):
    """Un lugar de la llave: un equipo, o (sin ``team_id``) el resultado de un partido de otra fase."""

    seed: int
    team_id: int | None = None
    group_id: int | None = None
    group_name: str | None = None
    position: int | None = None
    points: int | None = None
    gd: int | None = None
    label: str | None = None
    code: str = ""  # identifica el lugar en cruces manuales: "1A", "G2:Fase"
    bye: bool = False  # pasa directo a la segunda ronda


class PairOut(BaseModel):
    home: EntrantOut
    away: EntrantOut


class CupPreview(BaseModel):
    name: str
    size: int  # tamaño de la llave (potencia de 2)
    byes: int
    rounds: int  # rondas que se juegan en esta fase
    total_rounds: int  # rondas de la llave completa (mayor si la fase se corta)
    entrants: list[EntrantOut]
    pairs: list[PairOut] = []  # cruces de la primera ronda, en el orden de la llave


class KnockoutPreview(BaseModel):
    unplayed: int  # partidos de grupos que faltan cerrar
    cups: list[CupPreview]
