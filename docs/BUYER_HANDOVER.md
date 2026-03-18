# Buyer Handover Checklist

## 1. Artifacts Included
1. Source code repository.
2. `Dockerfile` and `docker-compose.yml`.
3. `.env.example`.
4. `LICENSE`.
5. Operational docs:
   - `docs/DEPLOY.md`
   - `docs/OPERATIONS.md`
   - `docs/DATA_POLICY.md`

## 2. Mandatory Actions Before Transfer
1. Rotate production `BOT_TOKEN`.
2. Rotate production `TONAPI_KEY`.
3. Review and update `ADMIN_IDS`.
4. Remove any real secrets from local `.env` before packaging.
5. Follow `docs/SECRET_ROTATION.md`.

## 3. Acceptance Test (Buyer)
1. Start stack: `docker compose up -d --build`.
2. Check health: `docker compose ps`.
3. Bind test chat with `/bind`.
4. Add one collection.
5. Verify `/health` returns OK.
6. Trigger demo/test route and confirm message delivery.

## 4. Data Handover Options
1. Code only (recommended default).
2. Code + sanitized DB.
3. Code + full DB + backups (requires explicit agreement and secure transfer).

## 5. Known Operational Risks to Communicate
1. External dependency on TonAPI and Telegram availability.
2. Event parser may quarantine unknown new formats; requires maintenance.
3. SQLite single-node model (no multi-node horizontal scaling out of the box).

## 6. Suggested Commercial SLA Baseline
1. Response time for critical incidents.
2. Update window for parser/API compatibility fixes.
3. Backup retention period and restore RTO/RPO targets.

## 7. Packaging Command
Generate transfer-ready archive:
```bash
python tools/make_handover.py
```
Outputs:
1. `nft-sales-bot-handover-*.zip`
2. matching `.sha256` checksum file
