import math

from howlongtobeatpy import HowLongToBeat


def round_up_hltb(value: float) -> float:
    if value <= 0:
        return 0.0
    return math.ceil(value * 2) / 2


async def search_hltb(title: str) -> dict | None:
    hltb = HowLongToBeat()
    results = await hltb.async_search(title)
    if not results:
        return None

    entries = [r for r in results if r.game_type == "game"]
    if not entries:
        return None

    best = max(entries, key=lambda r: r.similarity)
    if best.similarity < 0.5:
        return None

    main = round_up_hltb(best.main_story or 0)
    main_extra = round_up_hltb(best.main_extra or 0)
    full = round_up_hltb(best.completionist or 0)

    return {
        "title": best.game_name,
        "hltb_main": main,
        "hltb_main_extra": main_extra,
        "hltb_full": full,
        "cover_url": best.game_image_url,
    }
