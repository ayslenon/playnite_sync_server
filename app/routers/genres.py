from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func, Session

from app.database import get_session
from app.models import Genre, GameGenreLink
from app.schemas import CatalogCreate, CatalogUpdate

router = APIRouter(prefix="/api/genres", tags=["genres"])


@router.get("")
def list_genres(session: Session = Depends(get_session)):
    stmt = (
        select(
            Genre.id, Genre.name, func.count(GameGenreLink.game_id).label("game_count")
        )
        .outerjoin(GameGenreLink, Genre.id == GameGenreLink.genre_id)
        .group_by(Genre.id, Genre.name)
        .order_by(Genre.name)
    )
    results = session.exec(stmt).all()
    return [
        {"id": row.id, "name": row.name, "game_count": row.game_count}
        for row in results
    ]


@router.post("", status_code=201)
def create_genre(data: CatalogCreate, session: Session = Depends(get_session)):
    name = data.name
    existing = session.exec(select(Genre).where(Genre.name == name)).first()
    if existing:
        raise HTTPException(409, f"Genre '{name}' already exists")
    genre = Genre(name=name)
    session.add(genre)
    session.commit()
    session.refresh(genre)
    return genre


@router.put("/{genre_id}")
def update_genre(
    genre_id: int, data: CatalogUpdate, session: Session = Depends(get_session)
):
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(404, "Genre not found")
    name = data.name
    existing = session.exec(
        select(Genre).where(Genre.name == name, Genre.id != genre_id)
    ).first()
    if existing:
        raise HTTPException(409, f"Genre '{name}' already exists")
    genre.name = name
    session.add(genre)
    session.commit()
    session.refresh(genre)
    return genre


@router.delete("/{genre_id}")
def delete_genre(genre_id: int, session: Session = Depends(get_session)):
    genre = session.get(Genre, genre_id)
    if not genre:
        raise HTTPException(404, "Genre not found")
    count = session.exec(
        select(func.count(GameGenreLink.game_id)).where(
            GameGenreLink.genre_id == genre_id
        )
    ).one()
    if count > 0:
        raise HTTPException(
            409, f"Cannot delete genre '{genre.name}': it is used by {count} games."
        )
    session.delete(genre)
    session.commit()
    return {"ok": True}
