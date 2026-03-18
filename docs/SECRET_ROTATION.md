# Secret Rotation Procedure

## Scope
Mandatory before ownership transfer, environment migration, or any suspected leak.

## Secrets
1. `BOT_TOKEN`
2. `TONAPI_KEY`
3. Any external credentials used in host/CI/CD.

## Rotation Order
1. Prepare new owner/operator account and environment.
2. Rotate `TONAPI_KEY`.
3. Rotate `BOT_TOKEN`.
4. Update runtime `.env` on target host.
5. Restart service and validate `/health`.
6. Revoke and archive old credentials.

## Telegram Bot Token Rotation
1. Open `@BotFather`.
2. Select target bot.
3. Revoke current token (`/revoke`) and generate a new one (`/token`).
4. Update `BOT_TOKEN` in `.env`.
5. Restart bot:
```bash
docker compose up -d --build
```
6. Validate in Telegram:
1. `/health`
2. `/status`

## TonAPI Key Rotation
1. Generate new key in TonAPI dashboard.
2. Replace `TONAPI_KEY` in `.env`.
3. Restart bot.
4. Validate TonAPI status via `/health`.

## Verification Checklist
1. New secrets are active.
2. Old secrets are revoked.
3. No real secrets in files prepared for transfer.
4. `python tools/preflight.py` passes.

## Incident Response (if leak suspected)
1. Immediate token/key revocation.
2. Force rotation and redeploy.
3. Review logs for abnormal activity window.
4. Notify stakeholders and document incident.
