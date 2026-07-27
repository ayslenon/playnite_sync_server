import json
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text

from app.models.genre import Genre
from app.models.platform import Platform
from app.models.storage_device import StorageDevice


class GameGenreLink(SQLModel, table=True):
    __tablename__ = "game_genres"

    game_id: str = Field(foreign_key="games.id", primary_key=True)
    genre_id: int = Field(foreign_key="genres.id", primary_key=True)


class Game(SQLModel, table=True):
    __tablename__ = "games"

    id: str = Field(primary_key=True)
    playnite_id: str | None = Field(default=None, unique=True, nullable=True)
    title: str = Field(nullable=False)
    cover_url: str | None = Field(default=None)
    background_url: str | None = Field(default=None)

    platform_id: int | None = Field(default=None, foreign_key="platforms.id")
    storage_device_id: int | None = Field(
        default=None, foreign_key="storage_devices.id"
    )

    gameplay_status: str = Field(default="Backlog", nullable=False)
    interest_rating: int = Field(default=3, nullable=False)
    replay_score: int | None = Field(default=None)
    score: str | None = Field(default=None)
    must_test: bool = Field(default=False, nullable=False)

    finish_hours: float | None = Field(default=None)
    finish_date: str | None = Field(default=None)

    hltb_main: float = Field(default=0, nullable=False)
    hltb_main_extra: float = Field(default=0, nullable=False)
    hltb_full: float = Field(default=0, nullable=False)

    coop_players: str = Field(default="1 Jogador", nullable=False)
    coop_type: str = Field(
        default='["Um Jogador"]', sa_column=Column(Text, nullable=False)
    )
    coop_screen_type: str = Field(default="Tela Inteira", nullable=False)

    input_recommendation: str = Field(default="Controle", nullable=False)

    playtime_seconds: int = Field(default=0, nullable=False)

    notes: str | None = Field(default=None)

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        nullable=False,
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        nullable=False,
    )

    platform: Platform | None = Relationship()
    storage_device: StorageDevice | None = Relationship()
    genres: list[Genre] = Relationship(link_model=GameGenreLink)

    def coop_type_list(self) -> list[str]:
        if not self.coop_type:
            return ["Um Jogador"]
        try:
            return json.loads(self.coop_type)
        except (json.JSONDecodeError, TypeError):
            return ["Um Jogador"]

    @staticmethod
    def coop_type_str(value: list[str]) -> str:
        return json.dumps(value, ensure_ascii=False)
