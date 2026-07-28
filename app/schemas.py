from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

GAMEPLAY_STATUS = Literal["Backlog", "Jogando", "Finalizado", "Abandonado"]
COOP_PLAYERS = Literal[
    "1 Jogador", "2 Jogadores", "Até 4 Jogadores", "Mais de 4 Jogadores"
]
COOP_TYPE_ITEMS = {"Um Jogador", "Sofá", "Online", "LAN"}
COOP_SCREEN_TYPE = Literal["Tela Inteira", "Tela Dividida", "Versus"]
INPUT_REC = Literal["Controle", "Teclado/Mouse", "Ambos"]


def round_hltb(value: float) -> float:
    import math

    return math.ceil(value * 2) / 2


def validate_iso_date(v: str | None) -> str | None:
    if v is not None:
        try:
            datetime.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid ISO date: {v}")
    return v


class GameCreate(BaseModel):
    title: str = Field(min_length=1)
    playnite_id: str | None = None
    cover_url: str | None = None
    background_url: str | None = None
    genres: list[str] = Field(min_length=1)
    platform: str = Field(min_length=1)
    storage_device: str | None = None
    gameplay_status: GAMEPLAY_STATUS = "Backlog"
    interest_rating: int = Field(default=3, ge=1, le=5)
    replay_score: int | None = Field(default=None, ge=1, le=5)
    score: str | None = None
    must_test: bool = False
    finish_hours: float | None = Field(default=None, ge=0)
    finish_date: str | None = None
    hltb_main: float = Field(default=0, ge=0)
    hltb_main_extra: float = Field(default=0, ge=0)
    hltb_full: float = Field(default=0, ge=0)
    coop_players: COOP_PLAYERS = "1 Jogador"
    coop_type: list[str] = ["Um Jogador"]
    coop_screen_type: COOP_SCREEN_TYPE = "Tela Inteira"
    input_recommendation: INPUT_REC = "Controle"
    playtime_seconds: int = Field(default=0, ge=0)
    notes: str | None = None

    @field_validator("title", "platform")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip()

    @field_validator("genres", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            raise ValueError("genres must be a list, not a string")
        return v

    @field_validator("coop_type")
    @classmethod
    def validate_coop_type(cls, v: list[str]) -> list[str]:
        for item in v:
            if item not in COOP_TYPE_ITEMS:
                raise ValueError(
                    f"Invalid coop_type item '{item}'. Must be one of: {', '.join(sorted(COOP_TYPE_ITEMS))}"
                )
        return v

    @field_validator("finish_date")
    @classmethod
    def check_finish_date(cls, v: str | None) -> str | None:
        return validate_iso_date(v)

    @field_validator("score")
    @classmethod
    def check_score(cls, v: str | None) -> str | None:
        if v is not None and v.strip() == "":
            return None
        return v

    @model_validator(mode="after")
    def validate_finalized(self):
        if self.gameplay_status == "Finalizado":
            if self.replay_score is None:
                self.replay_score = 3
        return self


class GameUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    cover_url: str | None = None
    background_url: str | None = None
    genres: list[str] | None = None
    platform: str | None = None
    storage_device: str | None = None
    gameplay_status: GAMEPLAY_STATUS | None = None
    interest_rating: int | None = Field(default=None, ge=1, le=5)
    replay_score: int | None = Field(default=None, ge=1, le=5)
    score: str | None = None
    must_test: bool | None = None
    finish_hours: float | None = Field(default=None, ge=0)
    finish_date: str | None = None
    hltb_main: float | None = Field(default=None, ge=0)
    hltb_main_extra: float | None = Field(default=None, ge=0)
    hltb_full: float | None = Field(default=None, ge=0)
    coop_players: COOP_PLAYERS | None = None
    coop_type: list[str] | None = None
    coop_screen_type: COOP_SCREEN_TYPE | None = None
    input_recommendation: INPUT_REC | None = None
    playtime_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None

    @field_validator("title", "platform")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator("genres", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is not None and isinstance(v, str):
            raise ValueError("genres must be a list, not a string")
        return v

    @field_validator("coop_type")
    @classmethod
    def validate_coop_type(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for item in v:
                if item not in COOP_TYPE_ITEMS:
                    raise ValueError(
                        f"Invalid coop_type item '{item}'. Must be one of: {', '.join(sorted(COOP_TYPE_ITEMS))}"
                    )
        return v

    @field_validator("finish_date")
    @classmethod
    def check_finish_date(cls, v: str | None) -> str | None:
        return validate_iso_date(v)

    @field_validator("score")
    @classmethod
    def check_score(cls, v: str | None) -> str | None:
        if v is not None and v.strip() == "":
            return None
        return v


class BatchCreateRequest(BaseModel):
    games: list[GameCreate]


class PlayniteSyncEntry(BaseModel):
    playnite_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    is_installed: bool = False
    install_directory: str | None = None
    playtime_seconds: int = Field(default=0, ge=0)
    last_activity: str | None = None
    tags: list[str] = []

    @field_validator("last_activity")
    @classmethod
    def check_date(cls, v: str | None) -> str | None:
        return validate_iso_date(v)


class PlayniteSyncRequest(BaseModel):
    games: list[PlayniteSyncEntry]


class CatalogCreate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class CatalogUpdate(BaseModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class HltbSearchResult(BaseModel):
    title: str
    hltb_main: float
    hltb_main_extra: float
    hltb_full: float
    cover_url: str | None = None


class PlayniteGame(BaseModel):
    Id: str
    Name: str
    InstallDirectory: str | None = None
    IsInstalled: bool = True
    Playtime: int = 0
    Genres: list[str] = []
    Platforms: list[str] = []
    Source: str | None = None
    CompletionStatus: str | None = None
    Favorite: bool = False
    Hidden: bool = False
    Categories: list[str] = []
    Tags: list[str] = []
    Features: list[str] = []
    CoverImage: str | None = None
    BackgroundImage: str | None = None
    PlayCount: int = 0
    Notes: str | None = None


class PlayniteSyncPayload(BaseModel):
    games: list[PlayniteGame]
