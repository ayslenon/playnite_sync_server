from sqlmodel import SQLModel, Field


class StorageDevice(SQLModel, table=True):
    __tablename__ = "storage_devices"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, nullable=False)
    drive_letter: str | None = Field(default=None)
