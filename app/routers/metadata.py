from fastapi import APIRouter, HTTPException, Query

from app.schemas import HltbSearchResult
from app.services.hltb import search_hltb

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.get("/hltb", response_model=HltbSearchResult)
async def hltb_search(title: str = Query(min_length=1)):
    result = await search_hltb(title)
    if not result:
        raise HTTPException(404, f"No HLTB data found for '{title}'")
    return result
