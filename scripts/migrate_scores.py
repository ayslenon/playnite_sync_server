"""Convert legacy score strings to SQLite REAL; create a backup first.

Run with the server stopped: python scripts/migrate_scores.py /path/to/game_library.db
"""
import argparse
import re
import sqlite3
from datetime import datetime
from pathlib import Path


def convert(value):
    if value is None or str(value).strip() == '':
        return None
    text = str(value).strip().replace(',', '.')
    if not re.fullmatch(r'\d+(?:\.\d+)?(?:\s*/\s*10)?', text):
        raise ValueError(f'Nota inválida: {value!r}')
    number = float(text.split('/')[0].strip())
    if not 0 <= number <= 10:
        raise ValueError(f'Nota fora da escala: {value!r}')
    return number


def migrate(path):
    path = Path(path).resolve(strict=True)
    connection = sqlite3.connect(path)
    try:
        columns = connection.execute('PRAGMA table_info(games)').fetchall()
        score_column = next((col for col in columns if col[1] == 'score'), None)
        if not score_column:
            raise ValueError('Tabela games ou coluna score não encontrada')
        if score_column[2].upper() in ('REAL', 'FLOAT'):
            print('O banco já usa score numérico; nenhuma alteração realizada.')
            return
        rows = connection.execute('SELECT id, score FROM games').fetchall()
        converted = [(convert(score), game_id) for game_id, score in rows]
        backup_path = path.with_name(f'{path.name}.before-score-{datetime.now():%Y%m%d-%H%M%S-%f}.bak')
        with sqlite3.connect(backup_path) as backup:
            connection.backup(backup)
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('ALTER TABLE games RENAME COLUMN score TO score_legacy')
            connection.execute('ALTER TABLE games ADD COLUMN score REAL')
            connection.executemany('UPDATE games SET score = ? WHERE id = ?', converted)
            connection.execute('ALTER TABLE games DROP COLUMN score_legacy')
        print(f'Migração concluída: {len(rows)} jogos. Backup: {backup_path}')
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', help='Caminho do banco SQLite ativo')
    migrate(parser.parse_args().database)
