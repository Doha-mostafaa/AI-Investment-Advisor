from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from loguru import logger
from ingestion.config import config

engine = create_engine(config.pg_dsn, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        session.close()

def execute(sql: str, params: dict = None):
    with get_session() as s:
        return s.execute(text(sql), params or {})

def fetchall(sql: str, params: dict = None):
    with get_session() as s:
        result = s.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]

def fetchone(sql: str, params: dict = None):
    rows = fetchall(sql, params)
    return rows[0] if rows else None

def healthcheck() -> bool:
    try:
        fetchone("SELECT 1 AS ok")
        return True
    except Exception as e:
        logger.error(f"Postgres healthcheck failed: {e}")
        return False