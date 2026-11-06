import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select, Session
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Game, GameGenreLink, Platform, StorageDevice
from app.config import settings
from app.routers.games import (
    _create_single_game,
    _resolve_platform,
    _resolve_storage_device,
    _resolve_genres,
)
from app.schemas import (
    GameCreate,
    PlaynitePullRequest,
    PlaynitePullResponse,
    PlayniteSyncPayload,
)
from app.utils.playnite_assets import playnite_asset_url

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
    "macos": "PC",
    "nintendo switch": "Switch",
    "switch": "Switch",
    "nintendo 3ds": "3DS",
    "3ds": "3DS",
    "nintendo ds": "DS",
    "ds": "DS",
    "game boy advance": "GBA",
    "nintendo game boy advance": "GBA",
    "gba": "GBA",
    "nintendo 64": "N64",
    "n64": "N64",
    "nintendo gamecube": "GameCube",
    "gamecube": "GameCube",
    "super nintendo": "SNES",
    "super nes": "SNES",
    "nintendo snes": "SNES",
    "snes": "SNES",
    "nintendo wii": "Wii",
    "wii": "Wii",
    "playstation 1": "PS1",
    "playstation": "PS1",
    "sony playstation": "PS1",
    "ps1": "PS1",
    "playstation 2": "PS2",
    "sony playstation 2": "PS2",
    "ps2": "PS2",
    "playstation portable": "PSP",
    "sony playstation portable": "PSP",
    "psp": "PSP",
}

COMPLETION_MAP = {
    "playing": "Jogando",
    "jogando": "Jogando",
    "completed": "Finalizado",
    "finalizado": "Finalizado",
    "abandoned": "Abandonado",
    "abandonado": "Abandonado",
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
        return [], "1 Jogador"

    return sorted(coop_types), players


def _map_features(features: list[str]) -> tuple[str, str]:
    feats_lower = {f.strip().lower() for f in features}

    controller = any("controller" in f or "controle" in f for f in feats_lower)
    input_rec = "Controle" if controller else "Teclado/Mouse"

    screen = "Tela Compartilhada"
    if any("split" in f for f in feats_lower):
        screen = "Tela Dividida"

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


def _managed_values(tags: list[str], field: str, allowed: set[str]) -> list[str]:
    prefix = f"[servidor] {field}:"
    values = {value.casefold(): value for value in allowed}
    return list(dict.fromkeys(
        values[raw.casefold()]
        for tag in tags
        if tag.strip().casefold().startswith(prefix)
        for raw in [tag.strip()[len(prefix):].strip()]
        if raw.casefold() in values
    ))


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
    game.multiplayer_mode = Game.coop_type_str(data.multiplayer_mode)
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
    modes = []
    if any("coop" in f.lower() or "co-op" in f.lower() for f in item.Features + item.Categories):
        modes.append("Cooperativo")
    if any("versus" in f.lower() or "competitive" in f.lower() for f in item.Features + item.Categories):
        modes.append("Competitivo/Versus")
    managed_modes = _managed_values(item.Tags, "modo", {"Cooperativo", "Competitivo/Versus", "Nenhum"})
    if managed_modes:
        modes = [value for value in managed_modes if value != "Nenhum"]
    managed_coop = _managed_values(item.Tags, "coop", {"Um Jogador", "Sofá", "Online", "LAN", "Nenhum"})
    managed_players = _managed_values(item.Tags, "jogadores", {"1 Jogador", "2 Jogadores", "Até 4 Jogadores", "Mais de 4 Jogadores"})
    managed_input = _managed_values(item.Tags, "input", {"Controle", "Teclado/Mouse", "Ambos"})
    managed_screen = _managed_values(item.Tags, "tela", {"Tela Inteira", "Tela Compartilhada", "Tela Dividida", "Versus"})
    if managed_coop:
        coop_type = [value for value in managed_coop if value not in {"Nenhum", "Um Jogador"}]
    if len(managed_players) == 1:
        coop_players = managed_players[0]
    if len(managed_input) == 1:
        input_rec = managed_input[0]
    if len(managed_screen) == 1:
        if managed_screen[0] == "Versus":
            if not managed_modes and "Competitivo/Versus" not in modes:
                modes.append("Competitivo/Versus")
        else:
            coop_screen = "Tela Compartilhada" if managed_screen[0] == "Tela Inteira" else managed_screen[0]

    cover_url = playnite_asset_url(item.Id, item.CoverImage)
    background_url = playnite_asset_url(item.Id, item.BackgroundImage)

    return GameCreate(
        title=item.Name,
        playnite_id=item.Id,
        cover_url=cover_url,
        background_url=background_url,
        genres=item.Genres if item.Genres else [],
        platform=platform_name,
        storage_device=storage_name,
        gameplay_status=status,
        coop_players=coop_players,
        coop_type=coop_type,
        coop_screen_type=coop_screen,
        multiplayer_mode=modes,
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


def _playnite_pull_dict(game: Game) -> dict:
    gameplay_status = game.gameplay_status
    replay_score = None
    if (
        gameplay_status == "Finalizado"
        and game.replay_score is not None
        and 1 <= game.replay_score <= 5
    ):
        replay_score = game.replay_score

    return {
        "playnite_id": game.playnite_id,
        "genres": [genre.name for genre in (game.genres or [])],
        "gameplay_status": gameplay_status,
        "favorite": game.favorite,
        "must_test": game.must_test,
        "interest_rating": game.interest_rating,
        "replay_score": replay_score,
        "score": game.score,
        "notes": game.notes,
        "coop_players": game.coop_players,
        "coop_type": game.coop_type_list(),
        "coop_screen_type": game.coop_screen_type,
        "multiplayer_mode": game.multiplayer_mode_list(),
        "input_recommendation": game.input_recommendation,
        "updated_at": game.updated_at,
    }


@router.post("/playnite/pull", response_model=PlaynitePullResponse)
def pull_playnite_games(
    data: PlaynitePullRequest, session: Session = Depends(get_session)
):
    games = session.exec(
        select(Game)
        .options(selectinload(Game.genres))
        .where(
            func.lower(Game.playnite_id).in_(
                [playnite_id.casefold() for playnite_id in data.playnite_ids]
            )
        )
    ).all()
    games_by_id = {game.playnite_id.casefold(): game for game in games}

    result_games = []
    missing_ids = []
    for playnite_id in data.playnite_ids:
        game = games_by_id.get(playnite_id.casefold())
        if game is None:
            missing_ids.append(playnite_id)
            continue
        result_games.append(_playnite_pull_dict(game))

    return {
        "requested": len(data.playnite_ids),
        "found": len(result_games),
        "not_found": len(missing_ids),
        "games": result_games,
        "missing_playnite_ids": missing_ids,
    }
