import json
import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlmodel import create_engine

from app.database import init_db


class MultiplayerMigrationTests(unittest.TestCase):
    def test_existing_values_are_migrated_idempotently(self):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id TEXT PRIMARY KEY, score REAL, replay_score INTEGER, coop_type TEXT, coop_screen_type TEXT)"))
            connection.execute(text("INSERT INTO games VALUES (:id, NULL, 4, :coop, :screen)"), [
                {"id": "a", "coop": '["Um Jogador", "Sofá"]', "screen": "Versus"},
                {"id": "b", "coop": '["Um Jogador"]', "screen": "Tela Inteira"},
                {"id": "c", "coop": '["Online"]', "screen": "Tela Dividida"},
            ])
        with patch("app.database.engine", engine):
            init_db()
            init_db()
        with engine.connect() as connection:
            rows = {row.id: row for row in connection.execute(text("SELECT id, coop_type, multiplayer_mode FROM games"))}
            columns = {row.name for row in connection.execute(text("PRAGMA table_info(games)"))}
        self.assertEqual(json.loads(rows["a"].coop_type), ["Sofá"])
        self.assertEqual(json.loads(rows["a"].multiplayer_mode), ["Competitivo/Versus"])
        self.assertEqual(json.loads(rows["b"].coop_type), [])
        self.assertEqual(json.loads(rows["c"].multiplayer_mode), [])
        self.assertNotIn("replay_score", columns)
        self.assertNotIn("coop_screen_type", columns)
