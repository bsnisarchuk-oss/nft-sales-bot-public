"""Minimal web dashboard for NFT Sales Bot.

Run standalone: uvicorn dashboard.app:app --port 8080
Or integrate into main app with DASHBOARD_PORT env var.

Requires: pip install fastapi uvicorn
"""

from __future__ import annotations

import time

from utils.runtime_state import snapshot as rt_snapshot


def create_app():
    """Create and return the FastAPI app. Lazy import to avoid hard dependency."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI is required for the dashboard. "
            "Install: pip install fastapi uvicorn"
        )

    app = FastAPI(title="NFT Sales Bot Dashboard", version="1.0.0")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        s = rt_snapshot()
        uptime_sec = int(time.time() - s["started_at"])
        uptime_min = uptime_sec // 60

        html = f"""<!DOCTYPE html>
<html><head><title>NFT Sales Bot</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 16px 0; }}
.stat {{ display: inline-block; margin: 8px 16px 8px 0; }}
.label {{ color: #8b949e; font-size: 0.9em; }}
.value {{ font-size: 1.4em; font-weight: bold; color: #58a6ff; }}
.ok {{ color: #3fb950; }}
.warn {{ color: #d29922; }}
.err {{ color: #f85149; }}
</style>
</head><body>
<h1>NFT Sales Bot Dashboard</h1>
<div class="card">
  <div class="stat"><span class="label">Uptime</span><br><span class="value">{uptime_min} min</span></div>
  <div class="stat"><span class="label">Sales sent</span><br><span class="value ok">{s['total_sales']}</span></div>
  <div class="stat"><span class="label">Traces processed</span><br><span class="value">{s['total_traces']}</span></div>
  <div class="stat"><span class="label">Errors (1h)</span><br><span class="value {'err' if s['errors_last_hour'] > 0 else 'ok'}">{s['errors_last_hour']}</span></div>
</div>
<div class="card">
  <p><span class="label">Last tick:</span> {_ago(s['last_tick_at'])}</p>
  <p><span class="label">Last sale:</span> {_ago(s['last_sale_at'])}</p>
  <p><span class="label">Last error:</span> <code>{s['last_error'] or 'none'}</code></p>
</div>
<div class="card">
  <p><span class="label">API:</span> <a href="/api/status">/api/status</a> | <a href="/api/chats">/api/chats</a></p>
</div>
</body></html>"""
        return HTMLResponse(html)

    @app.get("/api/status")
    async def api_status():
        s = rt_snapshot()
        s["uptime_sec"] = int(time.time() - s["started_at"])
        return JSONResponse(s)

    @app.get("/api/chats")
    async def api_chats():
        try:
            from utils.chat_store_bridge import list_chats
            chats = await list_chats()
            return JSONResponse({"chats": chats})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/health")
    async def api_health():
        from utils.diagnostics import check_db, check_tonapi
        db_ok, db_msg = await check_db()
        api_ok, api_msg = await check_tonapi()
        return JSONResponse({
            "db": {"ok": db_ok, "message": db_msg},
            "tonapi": {"ok": api_ok, "message": api_msg},
        })

    return app


def _ago(ts: float) -> str:
    if not ts:
        return "never"
    sec = int(time.time() - ts)
    if sec < 60:
        return f"{sec}s ago"
    mins = sec // 60
    if mins < 60:
        return f"{mins}m ago"
    hrs = mins // 60
    return f"{hrs}h ago"


# Lazy singleton
app = None
try:
    app = create_app()
except ImportError:
    pass
