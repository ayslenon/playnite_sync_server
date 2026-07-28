import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import select

from app.config import settings
from app.database import get_session, init_db
from app.models import Platform, StorageDevice
from app.routers import games, genres, platforms, storage, export, metadata, sync

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
                session.add(StorageDevice(name=name, drive_letter=letter))

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


@app.middleware("http")
async def cache_control(request, call_next):
    response = await call_next(request)
    if request.method == "GET":
        path = request.url.path
        if path.startswith("/api/covers/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/api/games"):
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith(("/api/genres", "/api/platforms", "/api/storage-devices")):
            response.headers["Cache-Control"] = "public, max-age=3600"
    return response


app.include_router(games.router)
app.include_router(genres.router)
app.include_router(platforms.router)
app.include_router(storage.router)
app.include_router(export.router)
app.include_router(metadata.router)
app.include_router(sync.router)


@app.get("/api/covers/playnite/{playnite_id}/{filename}")
def serve_playnite_cover(playnite_id: str, filename: str):
    path = os.path.join(settings.covers_dir, playnite_id, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Cover not found")
    return FileResponse(path)


@app.get("/api/health")
def health():
    return {"status": "ok"}
