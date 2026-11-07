"""Back up the library and clean unused genres and abandoned-game interest."""
import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    if not args.database.is_file() or args.backup.exists():
        raise SystemExit("Banco inexistente ou backup já existe.")
    with sqlite3.connect(args.database, timeout=30) as connection:
        with sqlite3.connect(args.backup) as backup:
            connection.backup(backup)
        connection.execute("BEGIN IMMEDIATE")
        unused = [row[0] for row in connection.execute(
            "SELECT name FROM genres WHERE NOT EXISTS "
            "(SELECT 1 FROM game_genres WHERE genre_id = genres.id) ORDER BY name"
        )]
        removed = connection.execute(
            "DELETE FROM genres WHERE NOT EXISTS "
            "(SELECT 1 FROM game_genres WHERE genre_id = genres.id)"
        ).rowcount
        updated = connection.execute(
            "UPDATE games SET interest_rating = 1, updated_at = ? "
            "WHERE gameplay_status = ? AND interest_rating != 1",
            (datetime.now(timezone.utc).isoformat(), "Abandonado"),
        ).rowcount
        connection.commit()
        print(f"Backup: {args.backup}")
        print(f"Gêneros removidos ({removed}): {', '.join(unused)}")
        print(f"Jogos atualizados: {updated}")


if __name__ == "__main__":
    main()
