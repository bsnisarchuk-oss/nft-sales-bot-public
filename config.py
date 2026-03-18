# config.py: загрузка конфигурации из переменных окружения
import logging
import os

log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TONAPI_KEY = os.getenv("TONAPI_KEY", "")
TONAPI_BASE_URL = os.getenv("TONAPI_BASE_URL", "https://tonapi.io")
TONAPI_MIN_INTERVAL = float(os.getenv("TONAPI_MIN_INTERVAL", "1.1"))

# DEPRECATED: коллекции теперь мониторятся напрямую через events API.
# Оставлено для обратной совместимости (diagnostics fallback).
GETGEMS_ADDRESSES = [a.strip() for a in os.getenv("GETGEMS_ADDRESSES", "").split(",") if a.strip()]


class ConfigError(SystemExit):
    """Fatal config error — stops the bot at startup."""


def _validate_int(name: str, lo: int, hi: int) -> str | None:
    val = os.getenv(name)
    if val is None:
        return None
    try:
        n = int(val)
        if not (lo <= n <= hi):
            return f"{name} must be in [{lo}, {hi}], got {n}"
    except ValueError:
        return f"{name} must be an integer, got {val!r}"
    return None


def _validate_float(name: str, lo: float, hi: float) -> str | None:
    val = os.getenv(name)
    if val is None:
        return None
    try:
        n = float(val)
        if not (lo <= n <= hi):
            return f"{name} must be in [{lo}, {hi}], got {n}"
    except ValueError:
        return f"{name} must be a number, got {val!r}"
    return None


def validate_config() -> list[str]:
    """Validate all env vars at startup.

    Returns list of warnings. Raises ConfigError on fatal issues.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Required — re-read from env to catch runtime overrides
    bot_token = os.getenv("BOT_TOKEN", "")
    tonapi_key = os.getenv("TONAPI_KEY", "")

    if not bot_token:
        errors.append("BOT_TOKEN is required")
    if not tonapi_key:
        warnings.append("TONAPI_KEY is empty — API requests will be unauthenticated")

    # ADMIN_IDS
    admin_raw = os.getenv("ADMIN_IDS", "")
    if not admin_raw.strip():
        warnings.append("ADMIN_IDS is empty — no one can use admin commands")
    else:
        for part in admin_raw.split(","):
            part = part.strip()
            if part and not part.isdigit():
                errors.append(f"ADMIN_IDS contains non-numeric value: {part!r}")

    # Numeric bounds
    checks = [
        _validate_int("POLL_INTERVAL_SEC", 1, 3600),
        _validate_int("EVENTS_LIMIT", 1, 100),
        _validate_int("POLL_CONCURRENCY", 1, 50),
        _validate_int("MAX_PAGES_PER_TICK", 1, 50),
        _validate_int("PARSE_MAX_RETRIES", 1, 20),
        _validate_float("TONAPI_MIN_INTERVAL", 0.1, 60.0),
        _validate_int("NFT_CACHE_TTL", 0, 86400),
        _validate_int("ADDR_CACHE_TTL", 0, 86400),
        _validate_int("TON_USD_CACHE_TTL", 0, 3600),
    ]
    for err in checks:
        if err:
            errors.append(err)

    if errors:
        msg = "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ConfigError(msg)

    return warnings
