# Smoke Test

## Goal
Fast end-to-end validation that deployment is healthy and bot can process and send events.

## 1. Infrastructure
1. Start stack:
```bash
docker compose up -d --build
```
2. Verify container:
```bash
docker compose ps
docker compose logs --since=5m bot
```
Expected:
1. Service is `Up`.
2. Health is `healthy`.
3. No startup exceptions.

## 2. Telegram Admin Path
From an `ADMIN_IDS` user in target chat:
1. `/bind`
2. `/health`
3. `/status`

Expected:
1. `/bind` confirms chat linked.
2. `/health` shows DB OK and TonAPI OK.
3. `/status` shows live ticks after polling cycle.

## 3. Routing Path
1. Ensure at least one collection is present (`/collections`).
2. Trigger test route:
```text
/test_route
```
Expected:
1. Bot reports at least one destination chat (or explicit routing reason).
2. Test message appears in chat.

## 4. Parser Failure Path
1. Check quarantine table is not growing unexpectedly:
```bash
sqlite3 data/bot.db "SELECT COUNT(*) FROM parse_failures WHERE quarantined=1;"
```
Expected:
1. Count is stable or zero for normal operation.

## 5. Recovery Check
1. Restart service:
```bash
docker compose restart bot
```
2. Re-check:
```bash
docker compose ps
docker compose logs --since=3m bot
```
Expected:
1. Service returns to `healthy`.
2. Polling resumes without manual intervention.
