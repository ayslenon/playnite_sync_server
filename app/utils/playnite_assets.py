"""Helpers for converting Playnite image paths to API-relative URLs."""

from urllib.parse import unquote, urlsplit


def _filename_from_playnite_value(value: str | None) -> str | None:
    if not value:
        return None

    raw = value.strip()
    if not raw:
        return None

    # This also handles legacy localhost/IP URLs while keeping only the file
    # name. Playnite normally sends a filesystem path, not an HTTP URL.
    parsed = urlsplit(raw)
    candidate = parsed.path if parsed.scheme in {"http", "https", "file"} else raw
    candidate = unquote(candidate).replace("\\", "/").rstrip("/")
    filename = candidate.rsplit("/", 1)[-1].strip()

    if not filename or filename in {".", ".."}:
        return None
    if "/" in filename or "\\" in filename:
        return None
    return filename


def playnite_asset_url(playnite_id: str | None, value: str | None) -> str | None:
    """Return the canonical relative URL for a Playnite cover/background."""

    if not playnite_id:
        return None

    filename = _filename_from_playnite_value(value)
    if not filename:
        return None
    return f"/api/covers/playnite/{playnite_id}/{filename}"


def is_playnite_asset_url(value: str | None) -> bool:
    """Identify URLs that belong to the local Playnite cover endpoint."""

    if not value:
        return False
    return urlsplit(value).path.startswith("/api/covers/playnite/")
