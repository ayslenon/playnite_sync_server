import sqlite3
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError
from app.schemas import GameUpdate, PlaynitePullGame
from scripts.migrate_scores import migrate


class ScoreTests(unittest.TestCase):
    def test_api_accepts_numeric_bounds_and_rejects_invalid_values(self):
        for score in (0, 8.5, 10, None):
            self.assertEqual(GameUpdate(score=score).score, score)
        for score in (-1, 10.1, '8/10', float('nan')):
            with self.subTest(score=score), self.assertRaises(ValidationError):
                GameUpdate(score=score)

    def test_migration_preserves_rows_and_sorts_numerically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'library.db'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE games (id TEXT PRIMARY KEY, score VARCHAR)')
                db.executemany('INSERT INTO games VALUES (?, ?)', [('a', '10/10'), ('b', '1'), ('c', '7.5/10'), ('d', None)])
            migrate(path)
            with sqlite3.connect(path) as db:
                rows = db.execute('SELECT score FROM games WHERE score IS NOT NULL ORDER BY score').fetchall()
                self.assertEqual(rows, [(1.0,), (7.5,), (10.0,)])
                self.assertEqual(next(c[2] for c in db.execute('PRAGMA table_info(games)') if c[1] == 'score'), 'REAL')
            self.assertEqual(len(list(Path(directory).glob('*.bak'))), 1)

    def test_migration_rejects_invalid_values_without_modifying_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'library.db'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE games (id TEXT PRIMARY KEY, score VARCHAR)')
                db.execute('INSERT INTO games VALUES (?, ?)', ('a', '11/10'))
            with self.assertRaises(ValueError):
                migrate(path)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute('SELECT score FROM games').fetchone()[0], '11/10')
            self.assertFalse(list(Path(directory).glob('*.bak')))


if __name__ == '__main__':
    unittest.main()
