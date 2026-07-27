from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.database import get_session, init_db
from app.models import Platform, StorageDevice
from app.routers import games, genres, platforms, storage

SEED_PLATFORMS = [
    "PC (Steam)",
    "PC (Epic)",
    "PC (GOG)",
    "PC (EA)",
    "PC (Ubisoft)",
    "3DS",
    "DS",
    "GBA",
    "N64",
    "GameCube",
    "PS1",
    "PS2",
    "PSP",
    "SNES",
    "Switch",
    "Wii",
]

SEED_STORAGE = [
    ("SSD Windows", "C:"),
    ("HD ROMs", "R:"),
    ("HD Singleplayer", "J:"),
    ("HD Multiplayer", "M:"),
]


def seed_catalogs():
    session = next(get_session())
    try:
        for name in SEED_PLATFORMS:
            existing = session.exec(
                select(Platform).where(Platform.name == name)
            ).first()
            if not existing:
                session.add(Platform(name=name))

        for name, letter in SEED_STORAGE:
            existing = session.exec(
                select(StorageDevice).where(StorageDevice.name == name)
            ).first()
            if not existing:
                session.add(StorageDevice(name=name))

        session.commit()
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_catalogs()
    yield


app = FastAPI(
    title="Game Library API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router)
app.include_router(genres.router)
app.include_router(platforms.router)
app.include_router(storage.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
