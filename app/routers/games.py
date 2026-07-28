import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, func, Session
from sqlalchemy.orm import selectinload
from sqlalchemy import or_

from app.database import get_session
from app.models import Game, GameGenreLink, Genre, Platform, StorageDevice
from app.schemas import GameCreate, GameUpdate, BatchCreateRequest

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
        "favorite": game.favorite,
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


SORT_FIELDS = frozenset(
    {
        "title",
        "interest_rating",
        "score",
        "gameplay_status",
        "hltb_main",
        "hltb_main_extra",
        "hltb_full",
        "playtime_seconds",
        "coop_players",
        "updated_at",
        "created_at",
    }
)

SORT_WHITELIST = {
    "title": Game.title,
    "interest_rating": Game.interest_rating,
    "score": Game.score,
    "gameplay_status": Game.gameplay_status,
    "hltb_main": Game.hltb_main,
    "hltb_main_extra": Game.hltb_main_extra,
    "hltb_full": Game.hltb_full,
    "playtime_seconds": Game.playtime_seconds,
    "coop_players": Game.coop_players,
    "updated_at": Game.updated_at,
    "created_at": Game.created_at,
}


@router.get("")
def list_games(
    limit: int = Query(default=60, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    hds: str | None = Query(default=None),
    coop_type: str | None = Query(default=None),
    interest_min: int | None = Query(default=None, ge=1, le=5),
    interest_max: int | None = Query(default=None, ge=1, le=5),
    favorite: bool | None = Query(default=None),
    sort: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    base_stmt = select(Game)

    if search:
        base_stmt = base_stmt.where(Game.title.ilike(f"%{search}%"))

    if status:
        status_list = [s.strip() for s in status.split(",") if s.strip()]
        if status_list:
            base_stmt = base_stmt.where(Game.gameplay_status.in_(status_list))

    if platform:
        platform_names = [p.strip() for p in platform.split(",") if p.strip()]
        if platform_names:
            plats = session.exec(
                select(Platform.id).where(Platform.name.in_(platform_names))
            ).all()
            if plats:
                base_stmt = base_stmt.where(Game.platform_id.in_(plats))

    if genre:
        genre_names = [g.strip() for g in genre.split(",") if g.strip()]
        if genre_names:
            matched = session.exec(
                select(Genre.id).where(Genre.name.in_(genre_names))
            ).all()
            if matched:
                base_stmt = base_stmt.where(
                    Game.id.in_(
                        select(GameGenreLink.game_id).where(
                            GameGenreLink.genre_id.in_(matched)
                        )
                    )
                )

    if hds:
        hd_list = [h.strip() for h in hds.split(",") if h.strip()]
        if hd_list:
            hd_conditions = []
            uninstalled = "__uninstalled__" in hd_list
            named = [h for h in hd_list if h != "__uninstalled__"]
            if named:
                devices = session.exec(
                    select(StorageDevice.id).where(StorageDevice.name.in_(named))
                ).all()
                if devices:
                    hd_conditions.append(Game.storage_device_id.in_(devices))
            if uninstalled:
                hd_conditions.append(Game.storage_device_id.is_(None))
            if hd_conditions:
                base_stmt = base_stmt.where(or_(*hd_conditions))

    if coop_type:
        coop_list = [c.strip() for c in coop_type.split(",") if c.strip()]
        if coop_list:
            coop_conditions = [Game.coop_type.contains(f'"{c}"') for c in coop_list]
            base_stmt = base_stmt.where(or_(*coop_conditions))

    if interest_min is not None:
        base_stmt = base_stmt.where(Game.interest_rating >= interest_min)
    if interest_max is not None:
        base_stmt = base_stmt.where(Game.interest_rating <= interest_max)

    if favorite is not None:
        base_stmt = base_stmt.where(Game.favorite == favorite)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = session.exec(count_stmt).one()

    stmt = base_stmt.options(
        selectinload(Game.platform),
        selectinload(Game.storage_device),
        selectinload(Game.genres),
    )

    if sort:
        sort_fields = [s.strip() for s in sort.split(",") if s.strip()]
        invalid = [
            sf for sf in sort_fields if sf.split(":")[0].strip() not in SORT_FIELDS
        ]
        if invalid:
            raise HTTPException(422, f"Invalid sort fields: {', '.join(invalid)}")
        order_cols = []
        for sf in sort_fields:
            parts = sf.split(":")
            field = parts[0].strip()
            direction = parts[1].strip().lower() if len(parts) > 1 else "asc"
            col = SORT_WHITELIST.get(field)
            if col is None:
                continue
            order_cols.append(col.desc() if direction == "desc" else col.asc())
        if order_cols:
            stmt = stmt.order_by(*order_cols)
        else:
            stmt = stmt.order_by(Game.updated_at.desc())
    else:
        stmt = stmt.order_by(Game.updated_at.desc())

    stmt = stmt.offset(offset).limit(limit)
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


def _create_single_game(session: Session, data: GameCreate) -> Game:
    platform = _resolve_platform(session, data.platform)
    storage_device = _resolve_storage_device(session, data.storage_device)
    genres = _resolve_genres(session, data.genres)

    game_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    game = Game(
        id=game_id,
        title=data.title,
        playnite_id=data.playnite_id,
        cover_url=data.cover_url,
        background_url=data.background_url,
        platform_id=platform.id,
        storage_device_id=storage_device.id if storage_device else None,
        gameplay_status=data.gameplay_status,
        interest_rating=data.interest_rating,
        replay_score=data.replay_score,
        score=data.score,
        must_test=data.must_test,
        favorite=data.favorite,
        finish_hours=data.finish_hours,
        finish_date=data.finish_date,
        hltb_main=data.hltb_main,
        hltb_main_extra=data.hltb_main_extra,
        hltb_full=data.hltb_full,
        coop_players=data.coop_players,
        coop_type=Game.coop_type_str(data.coop_type),
        coop_screen_type=data.coop_screen_type,
        input_recommendation=data.input_recommendation,
        playtime_seconds=data.playtime_seconds,
        notes=data.notes,
        created_at=now,
        updated_at=now,
    )

    if game.gameplay_status == "Finalizado" and game.replay_score is None:
        game.replay_score = 3

    session.add(game)
    session.flush()

    for genre in genres:
        session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    return game


def _update_game_from_create(session: Session, game: Game, data: GameCreate) -> Game:
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
    game.interest_rating = data.interest_rating
    game.replay_score = data.replay_score
    game.score = data.score
    game.must_test = data.must_test
    game.favorite = data.favorite
    game.finish_hours = data.finish_hours
    game.finish_date = data.finish_date
    game.hltb_main = data.hltb_main
    game.hltb_main_extra = data.hltb_main_extra
    game.hltb_full = data.hltb_full
    game.coop_players = data.coop_players
    game.coop_type = Game.coop_type_str(data.coop_type)
    game.coop_screen_type = data.coop_screen_type
    game.input_recommendation = data.input_recommendation
    game.playtime_seconds = data.playtime_seconds
    game.notes = data.notes
    game.updated_at = datetime.now(timezone.utc).isoformat()

    if game.gameplay_status == "Finalizado" and game.replay_score is None:
        game.replay_score = 3

    existing_links = session.exec(
        select(GameGenreLink).where(GameGenreLink.game_id == game.id)
    ).all()
    for link in existing_links:
        session.delete(link)
    for genre in genres:
        session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    return game


def _reload_game(session: Session, game_id: str) -> Game:
    return session.exec(
        select(Game)
        .options(
            selectinload(Game.platform),
            selectinload(Game.storage_device),
            selectinload(Game.genres),
        )
        .where(Game.id == game_id)
    ).first()


@router.post("", status_code=201)
def create_game(data: GameCreate, session: Session = Depends(get_session)):
    game = _create_single_game(session, data)
    session.commit()
    session.refresh(game)
    return _game_to_dict(_reload_game(session, game.id))


@router.post("/batch", status_code=201)
def upsert_games_batch(
    data: BatchCreateRequest, session: Session = Depends(get_session)
):
    results = []
    errors = []
    for i, game_data in enumerate(data.games):
        try:
            existing = None
            if game_data.playnite_id:
                existing = session.exec(
                    select(Game).where(Game.playnite_id == game_data.playnite_id)
                ).first()

            if existing:
                game = _update_game_from_create(session, existing, game_data)
                session.flush()
                results.append(
                    {
                        "index": i,
                        "id": game.id,
                        "title": game.title,
                        "action": "updated",
                    }
                )
            else:
                game = _create_single_game(session, game_data)
                results.append(
                    {
                        "index": i,
                        "id": game.id,
                        "title": game.title,
                        "action": "created",
                    }
                )
        except Exception as e:
            errors.append({"index": i, "title": game_data.title, "error": str(e)})
            session.rollback()
            raise HTTPException(
                400,
                f"Error at index {i} ('{game_data.title}'): {e}. "
                f"{len(results)} games processed before failure were rolled back.",
            )
    session.commit()
    return {"processed": len(results), "games": results, "errors": errors}


@router.put("/{game_id}")
def update_game(
    game_id: str, data: GameUpdate, session: Session = Depends(get_session)
):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")

    if data.title is not None:
        game.title = data.title

    if data.platform is not None:
        platform = _resolve_platform(session, data.platform)
        game.platform_id = platform.id

    if data.storage_device is not None:
        device = _resolve_storage_device(session, data.storage_device)
        game.storage_device_id = device.id if device else None

    if data.genres is not None:
        existing_links = session.exec(
            select(GameGenreLink).where(GameGenreLink.game_id == game_id)
        ).all()
        for link in existing_links:
            session.delete(link)
        genres = _resolve_genres(session, data.genres)
        for genre in genres:
            session.add(GameGenreLink(game_id=game.id, genre_id=genre.id))

    scalar_fields = {
        "cover_url": data.cover_url,
        "background_url": data.background_url,
        "gameplay_status": data.gameplay_status,
        "interest_rating": data.interest_rating,
        "replay_score": data.replay_score,
        "score": data.score,
        "must_test": data.must_test,
        "favorite": data.favorite,
        "finish_hours": data.finish_hours,
        "finish_date": data.finish_date,
        "hltb_main": data.hltb_main,
        "hltb_main_extra": data.hltb_main_extra,
        "hltb_full": data.hltb_full,
        "coop_players": data.coop_players,
        "coop_screen_type": data.coop_screen_type,
        "input_recommendation": data.input_recommendation,
        "notes": data.notes,
        "playtime_seconds": data.playtime_seconds,
    }
    for field, value in scalar_fields.items():
        if value is not None:
            setattr(game, field, value)

    if data.coop_type is not None:
        game.coop_type = Game.coop_type_str(data.coop_type)

    if game.gameplay_status == "Finalizado" and game.replay_score is None:
        game.replay_score = 3

    game.updated_at = datetime.now(timezone.utc).isoformat()
    session.add(game)
    session.commit()

    return _game_to_dict(_reload_game(session, game.id))


@router.delete("/{game_id}")
def delete_game(game_id: str, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    session.delete(game)
    session.commit()
    return {"ok": True}
