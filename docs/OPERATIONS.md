# Operations Runbook

## Runtime Health
Primary signals:
1. Docker healthcheck (`docker compose ps`).
2. Application logs (`docker compose logs -f bot`).
3. Telegram commands:
   - `/health`
   - `/status`

Heartbeat file:
1. `data/runtime_health.json`
2. Updated in polling loop with status and loop timestamps.

## Routine Commands
```bash
docker compose ps
docker compose logs --since=15m bot
docker compose restart bot
```

## Backups
Automatic:
1. Daily SQLite backup to `data/backups/bot-YYYY-MM-DD.db`.

Manual:
1. Telegram admin command `/backup_now`
2. Or stop bot and copy DB files:
   - `data/bot.db`
   - `data/bot.db-wal`
   - `data/bot.db-shm`

## Restore Procedure (SQLite)
1. Stop service:
```bash
docker compose down
```
2. Replace current DB with selected backup:
```bash
cp data/backups/bot-YYYY-MM-DD.db data/bot.db
```
3. Start service:
```bash
docker compose up -d
```
4. Validate:
1. `docker compose ps`
2. `/health`
3. `/chats` and `/collections`

## Parse-Error Quarantine
When parser repeatedly fails on an event, it is quarantined after `PARSE_MAX_RETRIES`.

Table:
1. `parse_failures` in SQLite (`data/bot.db`)

Key fields:
1. `attempts`
2. `last_error`
3. `payload_json`
4. `quarantined`

Inspection example:
```bash
sqlite3 data/bot.db "SELECT address,trace_id,attempts,last_error,quarantined,last_failed_at FROM parse_failures ORDER BY last_failed_at DESC LIMIT 20;"
```

## Incident Handling
### Bot unhealthy
1. Check logs.
2. Verify `runtime_health.json` updates.
3. Verify disk space and DB accessibility.
4. Restart container.

### TonAPI failures
1. Validate `TONAPI_KEY`.
2. Check external connectivity.
3. Watch retry/backoff behavior in logs.

### Telegram send failures
1. Ensure bot still has permission to post.
2. Re-run `/health` in target chat.
3. Validate chat remains bound and enabled.

## Recommended Monitoring
1. Container health status.
2. Restart count.
3. Error count from logs.
4. Quarantined event count in `parse_failures`.
