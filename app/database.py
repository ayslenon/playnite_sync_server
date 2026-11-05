from sqlmodel import SQLModel, create_engine
from sqlmodel import Session as DBSession

from app.config import settings
import logging
from sqlalchemy import inspect

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


def get_session():
    with DBSession(engine) as session:
        yield session
