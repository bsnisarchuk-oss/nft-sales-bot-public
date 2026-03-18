import logging

from utils.db import DB

log = logging.getLogger("db_instance")

_db: DB | None = None


async def init_db() -> DB:
    global _db
    if _db is not None:
        return _db

    # Check if PostgreSQL is configured
    from utils.db_postgres import is_postgres_configured
    if is_postgres_configured():
        from utils.db_postgres import PostgresDB
        pg = PostgresDB()
        await pg.open()
        _db = pg  # type: ignore[assignment]
        log.info("Using PostgreSQL backend")
        return _db  # type: ignore[return-value]

    _db = DB()
    await _db.open()
    log.info("Using SQLite backend")
    return _db


def get_db() -> DB | None:
    return _db


def db_ready() -> DB | None:
    """Returns DB instance if ready, None otherwise."""
    db = _db
    if db and db.conn:
        return db
    return None
