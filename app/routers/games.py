import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func, Session
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Game, GameGenreLink, Genre, Platform, StorageDevice

router = APIRouter(prefix="/api/games", tags=["games"])


def _resolve_platform(session: Session, name: str) -> Platform:
    platform = session.exec(select(Platform).where(Platform.name == name)).first()
    if not platform:
        platform = Platform(name=name)
        session.add(platform)
        session.flush()
    return platform


def _resolve_storage_device(session: Session, name: str | None) -> StorageDevice | None:
    if not name:
        return None
    device = session.exec(
        select(StorageDevice).where(StorageDevice.name == name)
    ).first()
    if not device:
        device = StorageDevice(name=name)
        session.add(device)
        session.flush()
    return device


def _resolve_genres(session: Session, names: list[str]) -> list[Genre]:
    genres = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        genre = session.exec(select(Genre).where(Genre.name == name)).first()
        if not genre:
            genre = Genre(name=name)
            session.add(genre)
            session.flush()
        genres.append(genre)
    return genres


def _game_to_dict(game: Game) -> dict:
    return {
        "id": game.id,
        "playnite_id": game.playnite_id,
        "title": game.title,
        "cover_url": game.cover_url,
        "background_url": game.background_url,
        "genres": [g.name for g in (game.genres or [])],
        "platform": (
            {"id": game.platform.id, "name": game.platform.name}
            if game.platform
            else None
        ),
        "storage_device": (
            {"id": game.storage_device.id, "name": game.storage_device.name}
            if game.storage_device
            else None
        ),
        "gameplay_status": game.gameplay_status,
        "interest_rating": game.interest_rating,
        "replay_score": game.replay_score,
        "score": game.score,
        "must_test": game.must_test,
        "finish_hours": game.finish_hours,
        "finish_date": game.finish_date,
        "hltb_main": game.hltb_main,
        "hltb_main_extra": game.hltb_main_extra,
        "hltb_full": game.hltb_full,
        "coop_players": game.coop_players,
        "coop_type": game.coop_type_list(),
        "coop_screen_type": game.coop_screen_type,
        "input_recommendation": game.input_recommendation,
        "playtime_seconds": game.playtime_seconds,
        "notes": game.notes,
        "created_at": game.created_at,
        "updated_at": game.updated_at,
    }


@router.get("")
def list_games(
    limit: int = Query(default=60, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    platform_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    genre_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
):
    base_stmt = select(Game)

    if search:
        base_stmt = base_stmt.where(Game.title.ilike(f"%{search}%"))
    if platform_id is not None:
        base_stmt = base_stmt.where(Game.platform_id == platform_id)
    if status:
        base_stmt = base_stmt.where(Game.gameplay_status == status)
    if genre_id is not None:
        base_stmt = base_stmt.where(
            Game.id.in_(
                select(GameGenreLink.game_id).where(GameGenreLink.genre_id == genre_id)
            )
        )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = session.exec(count_stmt).one()

    stmt = (
        base_stmt.options(
            selectinload(Game.platform),
            selectinload(Game.storage_device),
            selectinload(Game.genres),
        )
        .order_by(Game.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    games = session.exec(stmt).all()

    return {
        "items": [_game_to_dict(g) for g in games],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/{game_id}")
def get_game(game_id: str, session: Session = Depends(get_session)):
    game = session.exec(
        select(Game)
        .options(
            selectinload(Game.platform),
            selectinload(Game.storage_device),
            selectinload(Game.genres),
        )
        .where(Game.id == game_id)
    ).first()
    if not game:
        raise HTTPException(404, "Game not found")
    return _game_to_dict(game)


@router.post("", status_code=201)
def create_game(data: dict, session: Session = Depends(get_session)):
    title = data.get("title", "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    genres_in = data.get("genres", [])
    if not genres_in:
        raise HTTPException(400, "At least one genre is required")
    platform_name = data.get("platform", "").strip()
    if not platform_name:
        raise HTTPException(400, "platform is required")

    platform = _resolve_platform(session, platform_name)
    storage_device = _resolve_storage_device(session, data.get("storage_device"))
    genres = _resolve_genres(session, genres_in)

    game_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    game = Game(
        id=game_id,
        title=title,
        cover_url=data.get("cover_url"),
        background_url=data.get("background_url"),
        platform_id=platform.id,
        storage_device_id=storage_device.id if storage_device else None,
        gameplay_status=data.get("gameplay_status", "Backlog"),
        interest_rating=data.get("interest_rating", 3),
        replay_score=data.get("replay_score"),
        score=data.get("score"),
        must_test=data.get("must_test", False),
        finish_hours=data.get("finish_hours"),
        finish_date=data.get("finish_date"),
        hltb_main=data.get("hltb_main", 0),
        hltb_main_extra=data.get("hltb_main_extra", 0),
        hltb_full=data.get("hltb_full", 0),
        coop_players=data.get("coop_players", "1 (Singleplayer)"),
        coop_type=Game.coop_type_str(data.get("coop_type", ["Um Jogador"])),
        coop_screen_type=data.get("coop_screen_type", "tela inteira"),
        input_recommendation=data.get("input_recommendation", "Controle"),
        playtime_seconds=data.get("playtime_seconds", 0),
        notes=data.get("notes"),
        created_at=now,
        updated_at=now,
    )

    if game.gameplay_status == "Finalizado" and game.replay_score is None:
        game.replay_score = 3

    session.add(game)
    session.flush()

    for genre in genres:
        session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    session.commit()
    session.refresh(game)

    game = session.exec(
        select(Game)
        .options(
            selectinload(Game.platform),
            selectinload(Game.storage_device),
            selectinload(Game.genres),
        )
        .where(Game.id == game.id)
    ).first()

    return _game_to_dict(game)


@router.put("/{game_id}")
def update_game(game_id: str, data: dict, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")

    if "title" in data:
        title = data["title"].strip()
        if not title:
            raise HTTPException(400, "title cannot be empty")
        game.title = title

    if "platform" in data:
        platform = _resolve_platform(session, data["platform"].strip())
        game.platform_id = platform.id

    if "storage_device" in data:
        device = _resolve_storage_device(session, data["storage_device"])
        game.storage_device_id = device.id if device else None

    if "genres" in data:
        existing_links = session.exec(
            select(GameGenreLink).where(GameGenreLink.game_id == game_id)
        ).all()
        for link in existing_links:
            session.delete(link)

        genres = _resolve_genres(session, data["genres"])
        for genre in genres:
            session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    scalar_fields = [
        "cover_url",
        "background_url",
        "gameplay_status",
        "interest_rating",
        "replay_score",
        "score",
        "must_test",
        "finish_hours",
        "finish_date",
        "hltb_main",
        "hltb_main_extra",
        "hltb_full",
        "coop_players",
        "coop_screen_type",
        "input_recommendation",
        "notes",
        "playtime_seconds",
    ]
    for field in scalar_fields:
        if field in data:
            setattr(game, field, data[field])

    if "coop_type" in data:
        game.coop_type = Game.coop_type_str(data["coop_type"])

    if game.gameplay_status == "Finalizado" and game.replay_score is None:
        game.replay_score = 3

    game.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(game)
    session.commit()

    game = session.exec(
        select(Game)
        .options(
            selectinload(Game.platform),
            selectinload(Game.storage_device),
            selectinload(Game.genres),
        )
        .where(Game.id == game.id)
    ).first()

    return _game_to_dict(game)


@router.delete("/{game_id}")
def delete_game(game_id: str, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    session.delete(game)
    session.commit()
    return {"ok": True}
