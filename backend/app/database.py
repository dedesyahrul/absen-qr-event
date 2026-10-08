from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_database() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema()


def _ensure_schema() -> None:
    """Add columns/indexes that create_all won't alter on existing tables."""
    statements = [
        "ALTER TABLE participants ADD COLUMN IF NOT EXISTS qr_group_token VARCHAR(100)",
        "CREATE INDEX IF NOT EXISTS ix_participants_qr_group_token ON participants (qr_group_token)",
        "ALTER TABLE participants ADD COLUMN IF NOT EXISTS attended_by VARCHAR(150)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
