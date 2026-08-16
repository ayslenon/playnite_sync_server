from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func, Session

from app.database import get_session
from app.models import StorageDevice, Game
from app.schemas import CatalogCreate, CatalogUpdate

router = APIRouter(prefix="/api/storage-devices", tags=["storage"])


@router.get("")
def list_storage_devices(session: Session = Depends(get_session)):
    stmt = (
        select(
            StorageDevice.id,
            StorageDevice.name,
            func.count(Game.id).label("game_count"),
        )
        .outerjoin(Game, StorageDevice.id == Game.storage_device_id)
        .group_by(StorageDevice.id, StorageDevice.name)
        .order_by(StorageDevice.name)
    )
    results = session.exec(stmt).all()
    return [
        {"id": row.id, "name": row.name, "game_count": row.game_count}
        for row in results
    ]


@router.post("", status_code=201)
def create_storage_device(data: CatalogCreate, session: Session = Depends(get_session)):
    name = data.name
    existing = session.exec(
        select(StorageDevice).where(StorageDevice.name == name)
    ).first()
    if existing:
        raise HTTPException(409, f"Storage device '{name}' already exists")
    device = StorageDevice(name=name)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.put("/{device_id}")
def update_storage_device(
    device_id: int, data: CatalogUpdate, session: Session = Depends(get_session)
):
    device = session.get(StorageDevice, device_id)
    if not device:
        raise HTTPException(404, "Storage device not found")
    name = data.name
    existing = session.exec(
        select(StorageDevice).where(
            StorageDevice.name == name, StorageDevice.id != device_id
        )
    ).first()
    if existing:
        raise HTTPException(409, f"Storage device '{name}' already exists")
    device.name = name
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.delete("/{device_id}")
def delete_storage_device(device_id: int, session: Session = Depends(get_session)):
    device = session.get(StorageDevice, device_id)
    if not device:
        raise HTTPException(404, "Storage device not found")
    count = session.exec(
        select(func.count(Game.id)).where(Game.storage_device_id == device_id)
    ).one()
    if count > 0:
        raise HTTPException(
            409,
            f"Cannot delete storage device '{device.name}': it is used by {count} games.",
        )
    session.delete(device)
    session.commit()
    return {"ok": True}
