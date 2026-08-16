from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.database import get_session
from app.utils.xlsx import export_games

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/xlsx")
def export_xlsx(session: Session = Depends(get_session)):
    try:
        output = export_games(session)
        content = output.getvalue()
        return StreamingResponse(
            iter([content]),
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": ("attachment; filename=biblioteca_jogos.xlsx"),
                "Content-Length": str(len(content)),
            },
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to generate spreadsheet: {e}")
