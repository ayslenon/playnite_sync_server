import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from app.database import get_session
from app.models import Game, GameGenreLink, Platform, StorageDevice
from app.config import settings
from app.routers.games import (
    _create_single_game,
    _resolve_platform,
    _resolve_storage_device,
    _resolve_genres,
)
from app.schemas import GameCreate, PlayniteSyncPayload

router = APIRouter(prefix="/api/sync", tags=["sync"])

SOURCE_MAP = {
    "steam": "PC (Steam)",
    "epic": "PC (Epic)",
    "gog": "PC (GOG)",
    "ea": "PC (EA)",
    "ubisoft": "PC (Ubisoft)",
}

PLATFORM_MAP = {
    "pc": "PC",
    "windows": "PC",
    "nintendo switch": "Switch",
    "switch": "Switch",
    "nintendo 3ds": "3DS",
    "3ds": "3DS",
    "nintendo ds": "DS",
    "ds": "DS",
    "game boy advance": "GBA",
    "gba": "GBA",
    "nintendo 64": "N64",
    "n64": "N64",
    "nintendo gamecube": "GameCube",
    "gamecube": "GameCube",
    "super nintendo": "SNES",
    "super nes": "SNES",
    "snes": "SNES",
    "nintendo wii": "Wii",
    "wii": "Wii",
    "playstation 1": "PS1",
    "playstation": "PS1",
    "ps1": "PS1",
    "playstation 2": "PS2",
    "ps2": "PS2",
    "playstation portable": "PSP",
    "psp": "PSP",
}

COMPLETION_MAP = {
    "playing": "Jogando",
    "completed": "Finalizado",
    "abandoned": "Abandonado",
    "backlog": "Backlog",
}


def _normalize_platform(name: str) -> str:
    return name.strip().split("(")[0].strip()


def _detect_platform(session: Session, platforms: list[str], source: str | None) -> str:
    base_platforms = {_normalize_platform(p).lower() for p in platforms}

    if "pc" in base_platforms or "windows" in base_platforms:
        if source:
            source_lower = source.strip().lower()
            if source_lower in SOURCE_MAP:
                return SOURCE_MAP[source_lower]
            return f"PC ({source.strip()})"
        return "PC (Steam)"

    for p in platforms:
        key = p.strip().lower()
        if key in PLATFORM_MAP:
            mapped = PLATFORM_MAP[key]
            if mapped == "PC":
                return "PC (Steam)"
            return mapped

    return platforms[0] if platforms else "PC (Steam)"


def _detect_storage_from_path(session: Session, install_dir: str | None) -> str | None:
    if not install_dir or len(install_dir) < 2:
        return None
    letter = install_dir[:2].upper()
    device = session.exec(
        select(StorageDevice).where(StorageDevice.drive_letter == letter)
    ).first()
    return device.name if device else None


def _map_completion(status: str | None) -> str:
    if not status:
        return "Backlog"
    return COMPLETION_MAP.get(status.strip().lower(), "Backlog")


def _map_categories(categories: list[str]) -> tuple[list[str], str]:
    cats_lower = {c.strip().lower() for c in categories}
    coop_types = set()
    players = "1 Jogador"

    has_local = "coop local" in cats_lower or "coop emulação" in cats_lower
    has_online = "coop online" in cats_lower

    if has_local:
        coop_types.add("Sofá")
        players = "2 Jogadores"
    if has_online:
        coop_types.add("Online")
        if players == "1 Jogador":
            players = "2 Jogadores"

    if not coop_types:
        return ["Um Jogador"], "1 Jogador"

    return sorted(coop_types), players


def _map_features(features: list[str]) -> tuple[str, str]:
    feats_lower = {f.strip().lower() for f in features}

    controller = any("controller" in f or "controle" in f for f in feats_lower)
    input_rec = "Controle" if controller else "Teclado/Mouse"

    screen = "Tela Inteira"
    if any("split" in f for f in feats_lower):
        screen = "Tela Dividida"
    elif any("versus" in f for f in feats_lower):
        screen = "Versus"

    return input_rec, screen


PLAYER_TAG_MAP = {
    "1 jogador": "1 Jogador",
    "2 jogadores": "2 Jogadores",
    "3 jogadores": "Até 4 Jogadores",
    "4 jogadores": "Até 4 Jogadores",
    "ate 4 jogadores": "Até 4 Jogadores",
    "mais de 4 jogadores": "Mais de 4 Jogadores",
}


def _map_tags_coop_players(tags: list[str]) -> str | None:
    tags_lower = {t.strip().lower() for t in tags}
    for tag, mapped in PLAYER_TAG_MAP.items():
        if tag in tags_lower:
            return mapped
    return None


def _should_skip(game_data) -> tuple[bool, str | None]:
    if game_data.Hidden:
        return True, "Hidden game"
    cats_lower = {c.strip().lower() for c in game_data.Categories}
    if "frontend launcher" in cats_lower:
        return True, "Frontend launcher"
    return False, None


def _update_game_from_playnite(session: Session, game: Game, data: GameCreate) -> Game:
    platform = _resolve_platform(session, data.platform)
    storage_device = _resolve_storage_device(session, data.storage_device)
    genres = _resolve_genres(session, data.genres)

    game.title = data.title
    game.playnite_id = data.playnite_id
    game.cover_url = data.cover_url
    game.background_url = data.background_url
    game.platform_id = platform.id
    game.storage_device_id = storage_device.id if storage_device else None
    game.gameplay_status = data.gameplay_status
    game.coop_players = data.coop_players
    game.coop_type = Game.coop_type_str(data.coop_type)
    game.coop_screen_type = data.coop_screen_type
    game.input_recommendation = data.input_recommendation
    game.playtime_seconds = data.playtime_seconds
    game.notes = data.notes
    game.favorite = data.favorite
    game.updated_at = datetime.now(timezone.utc).isoformat()

    existing_links = session.exec(
        select(GameGenreLink).where(GameGenreLink.game_id == game.id)
    ).all()
    for link in existing_links:
        session.delete(link)
    for genre in genres:
        session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    return game


def _playnite_to_gamecreate(session: Session, item) -> GameCreate | None:
    skip, _ = _should_skip(item)
    if skip:
        return None

    platform_name = _detect_platform(session, item.Platforms, item.Source)
    storage_name = _detect_storage_from_path(session, item.InstallDirectory)
    status = _map_completion(item.CompletionStatus)
    coop_type, coop_players = _map_categories(item.Categories)
    tag_players = _map_tags_coop_players(item.Tags)
    if tag_players:
        coop_players = tag_players
    input_rec, coop_screen = _map_features(item.Features)

    cover_url = None
    background_url = None
    if item.CoverImage and item.Id:
        fn = item.CoverImage.replace("\\", "/").split("/")[-1]
        cover_url = f"/api/covers/playnite/{item.Id}/{fn}"
    if item.BackgroundImage and item.Id:
        fn = item.BackgroundImage.replace("\\", "/").split("/")[-1]
        background_url = f"/api/covers/playnite/{item.Id}/{fn}"

    return GameCreate(
        title=item.Name,
        playnite_id=item.Id,
        cover_url=cover_url,
        background_url=background_url,
        genres=item.Genres or ["Outro"],
        platform=platform_name,
        storage_device=storage_name,
        gameplay_status=status,
        coop_players=coop_players,
        coop_type=coop_type,
        coop_screen_type=coop_screen,
        input_recommendation=input_rec,
        playtime_seconds=item.Playtime,
        notes=item.Notes,
        favorite=item.Favorite,
    )


@router.post("/playnite")
def sync_playnite(data: PlayniteSyncPayload, session: Session = Depends(get_session)):
    results = []
    skipped = 0

    for item in data.games:
        create_data = _playnite_to_gamecreate(session, item)
        if create_data is None:
            skipped += 1
            continue

        existing = session.exec(select(Game).where(Game.playnite_id == item.Id)).first()

        try:
            if existing:
                _update_game_from_playnite(session, existing, create_data)
                session.flush()
                results.append(
                    {
                        "id": existing.id,
                        "title": existing.title,
                        "action": "updated",
                    }
                )
            else:
                game = _create_single_game(session, create_data)
                results.append(
                    {
                        "id": game.id,
                        "title": game.title,
                        "action": "created",
                    }
                )
        except Exception as e:
            session.rollback()
            raise HTTPException(400, f"Error processing '{item.Name}': {e}")

    session.commit()
    return {"processed": len(results), "skipped": skipped, "results": results}
