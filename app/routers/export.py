from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.database import get_session
from app.utils.xlsx import export_games

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/xlsx")
def export_xlsx(session: Session = Depends(get_session)):
    output = export_games(session)
    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": ("attachment; filename=biblioteca_jogos.xlsx"),
        },
    )
