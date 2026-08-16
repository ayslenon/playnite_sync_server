from sqlmodel import SQLModel, Field


class Platform(SQLModel, table=True):
    __tablename__ = "platforms"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
