from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func, Session

from app.database import get_session
from app.models import Platform, Game
from app.schemas import CatalogCreate, CatalogUpdate

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("")
def list_platforms(session: Session = Depends(get_session)):
    stmt = (
        select(Platform.id, Platform.name, func.count(Game.id).label("game_count"))
        .outerjoin(Game, Platform.id == Game.platform_id)
        .group_by(Platform.id, Platform.name)
        .order_by(Platform.name)
    )
    results = session.exec(stmt).all()
    return [
        {"id": row.id, "name": row.name, "game_count": row.game_count}
        for row in results
    ]


@router.post("", status_code=201)
def create_platform(data: CatalogCreate, session: Session = Depends(get_session)):
    name = data.name
    existing = session.exec(select(Platform).where(Platform.name == name)).first()
    if existing:
        raise HTTPException(409, f"Platform '{name}' already exists")
    platform = Platform(name=name)
    session.add(platform)
    session.commit()
    session.refresh(platform)
    return platform


@router.put("/{platform_id}")
def update_platform(
    platform_id: int, data: CatalogUpdate, session: Session = Depends(get_session)
):
    platform = session.get(Platform, platform_id)
    if not platform:
        raise HTTPException(404, "Platform not found")
    name = data.name
    existing = session.exec(
        select(Platform).where(Platform.name == name, Platform.id != platform_id)
    ).first()
    if existing:
        raise HTTPException(409, f"Platform '{name}' already exists")
    platform.name = name
    session.add(platform)
    session.commit()
    session.refresh(platform)
    return platform


@router.delete("/{platform_id}")
def delete_platform(platform_id: int, session: Session = Depends(get_session)):
    platform = session.get(Platform, platform_id)
    if not platform:
        raise HTTPException(404, "Platform not found")
    count = session.exec(
        select(func.count(Game.id)).where(Game.platform_id == platform_id)
    ).one()
    if count > 0:
        raise HTTPException(
            409,
            f"Cannot delete platform '{platform.name}': it is used by {count} games.",
        )
    session.delete(platform)
    session.commit()
    return {"ok": True}
