import json
import os
import sqlite3
import sys
import time
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"UNHEALTHY: {msg}")
    return 1


def main() -> int:
    data_dir = os.getenv("DATA_DIR", "data")
    poll_interval = int(os.getenv("POLL_INTERVAL_SEC", "15"))
    max_stale_default = max(120, poll_interval * 4)
    max_stale_sec = int(os.getenv("HEALTH_MAX_STALE_SEC", str(max_stale_default)))
    startup_grace_sec = int(os.getenv("HEALTH_STARTUP_GRACE_SEC", "180"))

    health_path = Path(data_dir) / "runtime_health.json"
    if not health_path.exists():
        return _fail(f"missing {health_path}")

    try:
        payload = json.loads(health_path.read_text(encoding="utf-8"))
    except Exception as e:
        return _fail(f"invalid health json: {type(e).__name__}")

    now = int(time.time())
    started_at = int(payload.get("started_at") or 0)
    last_loop_at = int(payload.get("last_loop_at") or 0)

    if started_at <= 0:
        return _fail("started_at is not set")

    uptime = now - started_at
    if last_loop_at <= 0:
        if uptime <= startup_grace_sec:
            print("HEALTHY: startup grace period")
            return 0
        return _fail("no loop heartbeat after startup grace")

    stale_for = now - last_loop_at
    if stale_for > max_stale_sec:
        return _fail(f"heartbeat is stale for {stale_for}s (limit={max_stale_sec}s)")

    db_path = os.getenv("DB_PATH", str(Path(data_dir) / "bot.db"))
    db_file = Path(db_path)
    if db_file.exists():
        try:
            con = sqlite3.connect(db_path, timeout=2)
            try:
                con.execute("SELECT 1").fetchone()
            finally:
                con.close()
        except Exception as e:
            return _fail(f"sqlite check failed: {type(e).__name__}")

    print("HEALTHY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
