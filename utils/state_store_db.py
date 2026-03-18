import json
import sqlite3

from utils.db import DB


async def get_last_lt(db: DB, address: str) -> int:
    assert db.conn
    cur = await db.conn.execute("SELECT last_lt FROM state_by_address WHERE address=?", (address,))
    row = await cur.fetchone()
    return int(row[0]) if row else 0


async def set_last_lt(db: DB, address: str, last_lt: int) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            "INSERT INTO state_by_address(address,last_lt) VALUES (?,?) "
            "ON CONFLICT(address) DO UPDATE SET last_lt=excluded.last_lt, updated_at=strftime('%s','now')",
            (address, int(last_lt)),
        )
        await db.conn.commit()


async def is_trace_seen(db: DB, address: str, trace_id: str) -> bool:
    assert db.conn
    cur = await db.conn.execute(
        "SELECT 1 FROM recent_traces WHERE address=? AND trace_id=? LIMIT 1",
        (address, trace_id),
    )
    row = await cur.fetchone()
    return row is not None


async def mark_trace_seen(db: DB, address: str, trace_id: str, lt: int = 0) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            "INSERT OR IGNORE INTO recent_traces(address, trace_id, lt) VALUES (?,?,?)",
            (address, trace_id, int(lt)),
        )
        await db.conn.commit()


async def seen_trace(db: DB, address: str, trace_id: str, lt: int = 0) -> bool:
    """
    True если trace уже был (дубликат). False если новый и мы его записали.
    """
    assert db.conn
    async with db.write_lock:
        try:
            await db.conn.execute(
                "INSERT INTO recent_traces(address, trace_id, lt) VALUES (?,?,?)",
                (address, trace_id, int(lt)),
            )
            await db.conn.commit()
            return False
        except sqlite3.IntegrityError:
            await db.conn.rollback()
            return True
        except Exception:
            await db.conn.rollback()
            raise


async def register_parse_failure(
    db: DB,
    address: str,
    trace_id: str,
    lt: int,
    error_name: str,
    payload: dict,
) -> int:
    """
    Регистрирует неуспешный parse event и возвращает текущее число попыток.
    """
    assert db.conn
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    async with db.write_lock:
        await db.conn.execute(
            """
            INSERT INTO parse_failures(address, trace_id, lt, attempts, last_error, payload_json, quarantined)
            VALUES (?,?,?,?,?,?,0)
            ON CONFLICT(address, trace_id) DO UPDATE SET
                lt=excluded.lt,
                attempts=parse_failures.attempts + 1,
                last_error=excluded.last_error,
                payload_json=excluded.payload_json,
                last_failed_at=strftime('%s','now')
            """,
            (address, trace_id, int(lt), 1, error_name, payload_json),
        )
        cur = await db.conn.execute(
            "SELECT attempts FROM parse_failures WHERE address=? AND trace_id=?",
            (address, trace_id),
        )
        row = await cur.fetchone()
        await db.conn.commit()
    return int(row[0]) if row else 1


async def quarantine_parse_failure(db: DB, address: str, trace_id: str) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            """
            UPDATE parse_failures
            SET quarantined=1, last_failed_at=strftime('%s','now')
            WHERE address=? AND trace_id=?
            """,
            (address, trace_id),
        )
        await db.conn.commit()


async def clear_parse_failure(db: DB, address: str, trace_id: str) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            "DELETE FROM parse_failures WHERE address=? AND trace_id=?",
            (address, trace_id),
        )
        await db.conn.commit()


async def prune_recent_traces(db: DB, address: str, keep: int = 2000) -> None:
    """
    Оставляем только последние keep trace для адреса.
    """
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            """
            DELETE FROM recent_traces
            WHERE address=? AND trace_id NOT IN (
                SELECT trace_id FROM recent_traces
                WHERE address=?
                ORDER BY seen_at DESC
                LIMIT ?
            )
            """,
            (address, address, int(keep)),
        )
        await db.conn.commit()
