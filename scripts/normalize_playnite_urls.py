#!/usr/bin/env python3
"""Normalize legacy local Playnite image URLs in the configured SQLite DB.

The command is dry-run by default. Use --apply only after stopping the server
and making a copy of the database.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from sqlmodel import Session, select

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.config import settings
from app.database import engine
from app.models import Game
from app.utils.playnite_assets import is_playnite_asset_url, playnite_asset_url


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError("A migração exige DATABASE_URL SQLite")
    return Path(database_url[len(prefix) :])


def _legacy_local_playnite_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlsplit(value)
    if not parsed.path.startswith("/api/covers/playnite/"):
        return False
    return parsed.scheme in {"", "http", "https"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="grava as alterações")
    args = parser.parse_args()

    database_path = _sqlite_path(settings.database_url)
    if args.apply:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = database_path.with_name(f"{database_path.name}.before-relative-{timestamp}.bak")
        shutil.copy2(database_path, backup)
        print(f"Backup criado: {backup}")

    changed = 0
    with Session(engine) as session:
        for game in session.exec(select(Game)).all():
            for field in ("cover_url", "background_url"):
                value = getattr(game, field)
                if not value or not (_legacy_local_playnite_url(value) or is_playnite_asset_url(value)):
                    continue

                normalized = playnite_asset_url(game.playnite_id, value)
                if normalized and normalized != value:
                    print(f"{game.id} {field}: {value} -> {normalized}")
                    if args.apply:
                        setattr(game, field, normalized)
                    changed += 1

        if args.apply:
            session.commit()

    mode = "alterações aplicadas" if args.apply else "alterações encontradas (dry-run)"
    print(f"{changed} {mode}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
