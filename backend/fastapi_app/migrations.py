from __future__ import annotations

import logging
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from .database import SessionLocal


logger = logging.getLogger(__name__)
ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


def _is_sqlite_database(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def wait_for_database(database_url: str, retries: int = 20, delay_seconds: int = 2) -> None:
    if _is_sqlite_database(database_url):
        return

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return
        except Exception as exc:  # pragma: no cover - exercised through integration startup
            last_error = exc
            logger.warning("Database unavailable, retrying (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay_seconds)

    raise RuntimeError(f"Database not available after {retries} attempts") from last_error


def run_migrations(database_url: str) -> None:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("script_location", str((ALEMBIC_INI_PATH.parent / "alembic").resolve()))
    command.upgrade(config, "head")
