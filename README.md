# NFT Sales Bot — TON Blockchain

A production-ready Telegram bot that monitors NFT collection sales on the TON blockchain in real-time and delivers per-chat notifications with filtering, whale detection, and multi-language support.

> Russian documentation: [README_RU.md](README_RU.md)

---

## Overview

NFT projects and communities need instant visibility into their secondary market activity. This bot tracks TON NFT collections directly via the TonAPI events API and delivers formatted sale alerts to one or more Telegram chats, each with its own configuration.

Unlike simpler trackers that rely on a single hardcoded collection, this bot is multi-tenant: each Telegram chat independently manages its own list of tracked collections and its own notification settings.

**Who it is for:**
- NFT project owners who want to alert their community on every sale
- Traders and collectors monitoring multiple collections
- Developers building TON ecosystem tooling
- Anyone looking for a self-hosted alternative to subscription-based NFT alert services

---

## Features

### Core
- Real-time sale monitoring via TonAPI events API (configurable polling interval, default 15 sec)
- Multi-chat support — bind the bot to multiple Telegram chats, each with independent settings
- Per-collection filtering — each chat tracks only the collections it subscribed to
- TON → USD price conversion via Binance (60-second cache)
- Persistent retry queue — failed Telegram sends are retried automatically; no sales are silently dropped
- Parallel collection polling with configurable concurrency (semaphore-based, default 5)
- Warm start — skips historical backlog on first run to avoid notification floods
- Daily SQLite auto-backup
- Config export and import (JSON)

### Advanced
- **Sweep / whale detection** — alerts when the same buyer purchases 3+ NFTs within 5 minutes
- **Quiet hours** — suppress notifications during a configured time range (e.g. 23:00–07:00); whale alerts override quiet hours
- **Message batching** — group multiple rapid sales into a single Telegram message
- **Address filters** — per-chat whitelist or blacklist for buyer and seller addresses
- **Custom message templates** — replace the default format with your own using variables like `{price_ton}`, `{buyer}`, `{nft_name}`
- **Digest mode** — periodic sale summary instead of (or in addition to) individual alerts
- **Circuit breaker** — automatically pauses TonAPI polling after repeated failures; self-recovers
- **Prometheus metrics** — export `sales_total`, `poll_duration`, `circuit_breaker_state`, and more (optional)
- **Web dashboard** — lightweight FastAPI UI with `/api/status`, `/api/chats`, `/api/health` endpoints (optional)
- **PostgreSQL support** — drop-in replacement for SQLite via `DATABASE_URL` (optional)
- **i18n** — full English and Russian localization; language is set per chat

### Supported Event Types
| Event | Marketplace |
|-------|-------------|
| `NftPurchase` | GetGems, and any standard TON marketplace |
| `TelemintDeployV2` | Fragment (Telegram Numbers, Usernames) |
| `AuctionBid` | Fragment auctions |

---

## How It Works

```
Polling loop (every N seconds)
  │
  ├─ Fetch all tracked collections from active chats
  │
  ├─ For each collection (parallel, max POLL_CONCURRENCY):
  │   ├─ Get last processed logical time (lt) from DB
  │   ├─ Fetch new events from TonAPI (paginated)
  │   ├─ Deduplicate via event_id
  │   ├─ Parse NftPurchase / TelemintDeployV2 / AuctionBid
  │   ├─ On parse failure: retry up to 3×, then quarantine
  │   └─ Update lt cursor
  │
  └─ For each parsed sale, route to subscribed chats:
      ├─ Collection filter
      ├─ Min price filter
      ├─ Quiet hours check (whales bypass)
      ├─ Cooldown
      ├─ Address whitelist / blacklist
      ├─ Batch accumulator
      ├─ Format message (custom template or default HTML)
      ├─ Send to Telegram
      └─ On failure: enqueue for retry (retried every 30 sec)
```

The bot also maintains a JSON fallback store alongside the database, so the polling cursor survives a database outage.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Telegram framework | aiogram 3.24 (async) |
| HTTP client | aiohttp 3.13 |
| Primary database | SQLite via aiosqlite |
| Optional database | PostgreSQL via asyncpg |
| Blockchain data | TonAPI v2 events API |
| Price feed | Binance REST API |
| Metrics (optional) | prometheus-client |
| Dashboard (optional) | FastAPI + uvicorn |
| Containerization | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio (510+ tests, 86% coverage) |
| Linting / types | Ruff, mypy |

---

## Project Structure

```
.
├── app.py                      # Entry point: polling loop + Telegram dispatcher
├── config.py                   # Environment variable loading and validation
├── admin/
│   ├── commands.py             # /start, /help, /bind, /status, /health, ...
│   ├── settings_handlers.py    # /settings inline keyboard
│   ├── config_handlers.py      # /export_config, /import_config
│   ├── demo_handlers.py        # /demo — send a test notification
│   ├── keyboards.py            # Localized inline keyboards
│   └── states.py               # FSM states
├── utils/
│   ├── event_sales.py          # Parse NftPurchase / TelemintDeploy / AuctionBid events
│   ├── sale_dispatcher.py      # Route sales to chats with full filter pipeline
│   ├── sale_queue.py           # Persistent retry queue
│   ├── notifier.py             # Message formatting and sending
│   ├── tonapi.py               # TonAPI client (rate limiting, retry, caching, circuit breaker)
│   ├── ton_usd_rate.py         # TON/USD rate from Binance
│   ├── circuit_breaker.py      # CLOSED / OPEN / HALF_OPEN pattern
│   ├── whale_detector.py       # Sweep detection (3+ NFTs, 5-min window)
│   ├── quiet_hours.py          # Notification suppression by time range
│   ├── batch_accumulator.py    # Group rapid sales into one message
│   ├── address_filter_db.py    # Buyer / seller whitelists and blacklists
│   ├── digest.py               # Periodic sale summaries
│   ├── metrics.py              # Prometheus metrics (optional, no-op if not installed)
│   ├── i18n.py                 # Localization: t(key, lang, **kwargs)
│   ├── db.py                   # SQLite schema, connection, auto-migration
│   ├── db_postgres.py          # PostgreSQL backend
│   ├── db_protocol.py          # Abstract database interface
│   ├── db_instance.py          # Backend selection (SQLite vs PostgreSQL)
│   ├── chat_settings_db.py     # Per-chat settings dataclass
│   ├── chat_store_bridge.py    # Dual-write bridge (DB primary, JSON fallback)
│   └── config_io.py            # Config export / import
├── locales/
│   ├── ru.py                   # Russian strings (~170 keys)
│   └── en.py                   # English strings (~170 keys)
├── dashboard/
│   └── app.py                  # FastAPI web dashboard + JSON API
├── docs/                       # Deployment, operations, handover guides
├── tools/                      # Helper scripts (container healthcheck, etc.)
├── tests/                      # Full test suite
├── Dockerfile
├── docker-compose.yml
└── data/                       # Auto-created at runtime (DB, backups, state)
```

---

## Quick Start

### 1. Install dependencies

```bash
python3.10 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Configure `.env`

Open `.env` and fill in the three required variables:

```env
BOT_TOKEN=your_telegram_bot_token    # from @BotFather
TONAPI_KEY=your_tonapi_key           # from tonapi.io
ADMIN_IDS=123456789                  # your Telegram user ID
```

All other settings have sensible defaults. See [Environment Variables](#environment-variables) for the full list.

### 3. Run

```bash
python app.py
```

The `data/` directory and SQLite database are created automatically on first run. Schema migrations are applied automatically — no manual migration steps required.

**First-time setup in Telegram:**
1. Add the bot to your chat
2. Send `/bind` to register the chat
3. Send `/start` → **+ Add collection** → paste a collection address (e.g. `EQ...` or `0:...`)
4. The bot will start sending sale notifications immediately

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token (from @BotFather) |
| `TONAPI_KEY` | TonAPI authentication key |
| `ADMIN_IDS` | Comma-separated Telegram user IDs with admin access |

### Polling

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_SEC` | `15` | Seconds between polling cycles |
| `POLL_CONCURRENCY` | `5` | Max parallel TonAPI requests per cycle |
| `POLL_TICK_TIMEOUT_SEC` | `120` | Hard timeout for a single polling tick |
| `EVENTS_LIMIT` | `20` | Events fetched per API request |
| `MAX_PAGES_PER_TICK` | `5` | Max pagination depth per collection per tick |
| `WARM_START_SKIP_HISTORY` | `1` | Skip existing events on first run (recommended) |
| `TONAPI_BASE_URL` | `https://tonapi.io` | TonAPI base URL |
| `TONAPI_MIN_INTERVAL` | `1.1` | Min seconds between TonAPI requests (rate limiting) |

### Circuit Breaker

| Variable | Default | Description |
|----------|---------|-------------|
| `CB_FAILURE_THRESHOLD` | `5` | Consecutive failures before circuit opens |
| `CB_RECOVERY_TIMEOUT` | `60` | Seconds to wait before attempting recovery |

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data` | Directory for database and state files |
| `DB_PATH` | `data/bot.db` | SQLite database path |
| `DATABASE_URL` | — | PostgreSQL DSN (enables PostgreSQL backend if set) |

### Price Feed

| Variable | Default | Description |
|----------|---------|-------------|
| `TON_USD_CACHE_TTL` | `60` | Binance rate cache lifetime (seconds) |

### Logging and Monitoring

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `METRICS_PORT` | `0` | Prometheus metrics port (`0` = disabled) |
| `DASHBOARD_PORT` | `0` | Web dashboard port (`0` = disabled) |

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/help` | Command reference |
| `/bind` | Register the current chat |
| `/unbind` | Remove the current chat |
| `/collections` | List collections tracked by this chat |
| `/chats` | List all registered chats |
| `/settings` | Open per-chat settings (inline keyboard) |
| `/status` | Bot status: uptime, sales processed, queue size |
| `/health` | Self-diagnostics: DB, TonAPI connectivity, bot permissions |
| `/pause` / `/resume` | Pause or resume notifications for this chat |
| `/backup_now` | Trigger a manual database backup |
| `/export_config` | Export current configuration as JSON |
| `/import_config` | Import configuration (merge mode) |
| `/import_config_replace` | Import configuration (full replace) |
| `/refresh_names` | Refresh collection display names from TonAPI |
| `/demo` | Send a test sale notification to verify the setup |

---

## Per-Chat Settings

Each chat has independent configuration accessible via `/settings`:

| Setting | Description |
|---------|-------------|
| Min price (TON) | Ignore sales below this threshold |
| Cooldown (sec) | Minimum gap between messages to this chat |
| Show link preview | Toggle Telegram link previews in messages |
| Send photos | Attach NFT thumbnail to notifications |
| Whale threshold (TON) | Trigger sweep alert above this price |
| Ping admins on whale | Mention admins when a whale alert fires |
| Language | `en` or `ru` |
| Quiet hours | Suppress notifications between two times (e.g. `23:00`–`07:00`) |
| Batch window (sec) | Accumulate sales and send as one message |
| Message template | Custom Jinja-style template with `{price_ton}`, `{buyer}`, `{nft_name}`, etc. |

Address-level filters (whitelist/blacklist for buyers and sellers) are configurable per chat via inline keyboard.

---

## Docker Deployment

The included `docker-compose.yml` handles the full lifecycle:

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop
docker-compose down
```

**Container highlights:**
- Non-root user (uid 10001)
- `cap_drop: ALL`, `no-new-privileges: true`
- Healthcheck via `tools/container_healthcheck.py` (30 sec interval)
- Log rotation: JSON driver, 10 MB max, 3 files
- Resource limits: 256 MB RAM, 0.5 CPU
- Data volume: `./data:/app/data` (persists database and backups)

For server deployment, see [docs/DEPLOY.md](docs/DEPLOY.md).

---

## Optional Features

### PostgreSQL

The bot defaults to SQLite. To use PostgreSQL instead:

```bash
pip install asyncpg
```

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/nft_sales_bot
```

The backend is selected automatically at startup. Tables are created on first run.

### Prometheus Metrics

```bash
pip install prometheus-client
```

```env
METRICS_PORT=9090
```

Exported metrics include: `nft_sales_total`, `nft_sales_sent`, `nft_sales_skipped`, `nft_poll_duration_seconds`, `nft_circuit_breaker_state`, `nft_active_chats`, `nft_tracked_collections`.

### Web Dashboard

```bash
pip install fastapi uvicorn
```

```env
DASHBOARD_PORT=8080
```

Endpoints:
- `GET /` — HTML status page (uptime, sales, errors)
- `GET /api/status` — JSON bot status
- `GET /api/chats` — registered chats list
- `GET /api/health` — database and TonAPI health check

---

## Testing

```bash
# Install dev dependencies
pip install -r requirements.txt  # includes pytest, pytest-asyncio, pytest-cov

# Run tests
pytest -q tests/

# Run with coverage report
pytest --cov=admin --cov=utils --cov-report=term-missing tests/

# Lint and type check
ruff check .
mypy app.py admin/ utils/ --ignore-missing-imports
```

The test suite has 510+ tests covering 86% of the codebase, including unit tests for every major component: event parsing, sale routing, database operations, circuit breaker, whale detection, batch accumulation, quiet hours, i18n, and Prometheus metrics.

---

## Business Value

This project is useful beyond a single deployment:

- **Multi-tenant architecture** — one bot instance serves any number of Telegram chats, each with its own tracked collections and settings. No per-project forks needed.
- **Production-grade resilience** — circuit breaker, retry queue, deduplication, and JSON fallback storage make the bot tolerant of API and database failures without losing data.
- **Observability built in** — Prometheus metrics and a REST status API are available out of the box. Both are optional dependencies, so they add zero overhead when not used.
- **Clean extension points** — the database interface is abstracted behind a protocol, making it straightforward to add a new storage backend. Notification formatting and filtering steps are well-separated.
- **Fully localized** — English and Russian are included; adding a new language requires only a single locale file.
- **Documented for handover** — the `docs/` folder includes deployment guides, operations runbooks, secret rotation procedures, a smoke test checklist, and a buyer handover document.

---

## Customization

Common customization scenarios:

- **Different blockchain or API** — replace `utils/tonapi.py` and `utils/event_sales.py` while keeping the dispatcher, queue, and notification layers
- **Additional marketplaces** — add new event type parsers in `event_sales.py`; the rest of the pipeline is marketplace-agnostic
- **New notification channels** — swap or extend `utils/notifier.py` (e.g. add Discord webhooks alongside Telegram)
- **New database backend** — implement `utils/db_protocol.py` and register it in `utils/db_instance.py`
- **Additional locale** — add `locales/{lang}.py` with a `STRINGS` dict matching the existing key set

---

## Limitations

- **Single-process** — designed to run as one process per environment. Running multiple instances against the same database will cause duplicate notifications.
- **TON blockchain only** — the event parsing layer is specific to TonAPI's event schema. Supporting Ethereum or Solana would require replacing the client and parser.
- **Admin via Telegram** — all configuration is done through bot commands. There is no standalone web admin UI beyond the read-only dashboard.
- **TonAPI dependency** — the bot requires a TonAPI key. A free-tier key is sufficient for moderate polling volumes; high-frequency deployments may need a paid plan.
- **Quiet hours are per-chat, not per-collection** — if a chat has quiet hours configured, all collections in that chat follow the same schedule.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | Server deployment guide |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Monitoring and troubleshooting |
| [docs/DATA_POLICY.md](docs/DATA_POLICY.md) | Data retention and storage details |
| [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md) | Rotating API keys and tokens |
| [docs/BUYER_HANDOVER.md](docs/BUYER_HANDOVER.md) | Project handover guide |
| [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) | Release process |
| [docs/SMOKE_TEST.md](docs/SMOKE_TEST.md) | Post-deployment verification steps |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Bot does not respond to commands | No permissions in chat | Grant the bot permission to send messages |
| Commands fail with "not authorized" | Wrong `ADMIN_IDS` value | Check your Telegram user ID via [@userinfobot](https://t.me/userinfobot) |
| `TonAPI 429` errors in logs | Rate limit exceeded | Increase `TONAPI_MIN_INTERVAL` (e.g. `2.0`) |
| No notifications arriving | Chat not bound, or no collections added | Run `/bind`, then add a collection via `/start` |
| `DB locked` on startup | Another bot process is running | Stop the existing process before restarting |
| `CircuitOpenError` in logs | TonAPI is unreachable | Bot will self-recover after `CB_RECOVERY_TIMEOUT` seconds |
| Duplicate notifications | Multiple bot instances running | Ensure only one instance is active per database |

---

## License

MIT
