from sqlmodel import SQLModel, Field


class Genre(SQLModel, table=True):
    __tablename__ = "genres"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
