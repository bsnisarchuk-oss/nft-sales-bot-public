# Deploy Guide

## Scope
Production deployment for `nft-sales-bot` using Docker Compose on a single host.

## Prerequisites
1. Docker Engine 24+ and Docker Compose v2.
2. Linux host (recommended) with persistent disk for `data/`.
3. Valid secrets:
   - `BOT_TOKEN`
   - `TONAPI_KEY`
   - `ADMIN_IDS`
4. Network egress to:
   - `https://tonapi.io`
   - `https://data-api.binance.vision` (or `api.binance.com` fallback)
   - Telegram Bot API.

## 1. Prepare Environment
```bash
cp .env.example .env
```

Fill required variables in `.env`:
1. `BOT_TOKEN`
2. `TONAPI_KEY`
3. `ADMIN_IDS` (comma-separated numeric Telegram user IDs)
4. Optional tuning:
   - `POLL_INTERVAL_SEC`
   - `PARSE_MAX_RETRIES`
   - `HEALTH_MAX_STALE_SEC`
   - `HEALTH_STARTUP_GRACE_SEC`

## 2. Start
```bash
docker compose up -d --build
```

Check status:
```bash
docker compose ps
docker compose logs -f bot
```

Container health should become `healthy` after startup grace period.

## 3. First-Time Runtime Setup
1. Add bot to target Telegram chat/channel.
2. Ensure bot can post messages in chat.
3. Execute `/bind` from admin user.
4. Add collections via `/add_collection` or admin UI button.
5. Validate with:
   - `/health`
   - `/status`
   - `/collections`

## 4. Upgrade Procedure
```bash
git pull
docker compose up -d --build
```

Post-upgrade checks:
1. `docker compose ps`
2. `docker compose logs --since=10m bot`
3. `/health` in Telegram admin chat

## 5. Rollback Procedure
1. Checkout previous release commit/tag.
2. Rebuild and restart:
```bash
docker compose up -d --build
```
3. If needed, restore DB from backup in `data/backups/` (see `docs/OPERATIONS.md`).

## 6. Security Baseline
Current deployment hardening:
1. Non-root container user.
2. `no-new-privileges`.
3. `cap_drop: ALL`.
4. `/tmp` mounted as `tmpfs`.
5. Healthcheck enabled.

Mandatory operational rule: do not commit `.env` with real secrets.
