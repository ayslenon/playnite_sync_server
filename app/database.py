from sqlmodel import SQLModel, create_engine
from sqlmodel import Session as DBSession

from app.config import settings
import logging
from sqlalchemy import inspect, text

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)


def init_db():
    logging.getLogger('uvicorn.error').info('Banco de dados: %s', engine.url.database)
    inspector = inspect(engine)
    if inspector.has_table('games'):
        score = next((c for c in inspector.get_columns('games') if c['name'] == 'score'), None)
        if score and str(score['type']).upper() not in ('REAL', 'FLOAT'):
            raise RuntimeError('Banco com score antigo. Pare o servidor e execute scripts/migrate_scores.py no banco ativo.')
    SQLModel.metadata.create_all(engine)
    # Upgrade existing SQLite databases in a single transaction; reruns are safe.
    with engine.begin() as connection:
        columns = {c["name"] for c in inspect(connection).get_columns("games")}
        if "multiplayer_mode" not in columns:
            connection.execute(text("ALTER TABLE games ADD COLUMN multiplayer_mode TEXT NOT NULL DEFAULT '[]'"))
            columns.add("multiplayer_mode")

        # Preserve o significado do legado "Tela: Versus" antes de remover a coluna.
        if "coop_screen_type" in columns:
            import json
            rows = connection.execute(text(
                "SELECT id, multiplayer_mode FROM games WHERE coop_screen_type = 'Versus'"
            )).all()
            for game_id, raw_modes in rows:
                try:
                    modes = json.loads(raw_modes or "[]")
                except (TypeError, ValueError):
                    modes = []
                if "Competitivo/Versus" not in modes:
                    modes.append("Competitivo/Versus")
                    connection.execute(
                        text("UPDATE games SET multiplayer_mode = :modes WHERE id = :id"),
                        {"modes": json.dumps(modes, ensure_ascii=False), "id": game_id},
                    )

        rows = connection.execute(text("SELECT id, coop_type FROM games")).all()
        import json
        for game_id, raw in rows:
            try:
                values = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if isinstance(values, list) and "Um Jogador" in values:
                connection.execute(text("UPDATE games SET coop_type = :value WHERE id = :id"),
                                   {"value": json.dumps([v for v in values if v != "Um Jogador"], ensure_ascii=False), "id": game_id})

        # Campos removidos do produto. DROP COLUMN é idempotente pela inspeção.
        columns = {c["name"] for c in inspect(connection).get_columns("games")}
        if "replay_score" in columns:
            connection.execute(text("ALTER TABLE games DROP COLUMN replay_score"))
        if "coop_screen_type" in columns:
            connection.execute(text("ALTER TABLE games DROP COLUMN coop_screen_type"))


def get_session():
    with DBSession(engine) as session:
        yield session
