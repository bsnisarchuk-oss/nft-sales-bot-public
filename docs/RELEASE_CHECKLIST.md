# Release Checklist

## Pre-Release
1. Rotate secrets for transfer scope:
   - `BOT_TOKEN`
   - `TONAPI_KEY`
2. Follow `docs/SECRET_ROTATION.md`.
3. Verify `.env` is not committed.
4. Run static checks:
```bash
python tools/preflight.py
```
5. Run quality gates:
```bash
ruff check .
mypy app.py admin utils
pytest -q tests
```
6. Build and test Docker image locally:
```bash
docker compose up -d --build
docker compose ps
docker compose logs --since=5m bot
```
7. Confirm container is `healthy`.

## Functional Validation
1. Run smoke scenario from `docs/SMOKE_TEST.md`.
2. Validate:
   - `/health`
   - `/status`
   - message dispatch in bound chat.
3. Ensure no unexpected parse quarantines in `parse_failures`.

## Packaging
1. Include:
   - source code
   - `LICENSE`
   - `README.md`
   - `docs/*`
2. Exclude:
   - `.env`
   - local logs
   - temporary/debug files
3. Optional: create release archive with `tools/make_release.py`.
4. Create handover archive:
```bash
python tools/make_handover.py
```

## Handover
1. Deliver buyer checklist: `docs/BUYER_HANDOVER.md`.
2. Deliver deploy and operations guides.
3. Align SLA and support window in writing.
