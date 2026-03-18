"""Tests for config.validate_config()."""

import pytest


def test_valid_config(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TONAPI_KEY", "key")
    monkeypatch.setenv("ADMIN_IDS", "111,222")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "15")

    from config import validate_config
    warnings = validate_config()
    assert isinstance(warnings, list)


def test_missing_bot_token(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "")
    monkeypatch.setenv("TONAPI_KEY", "key")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        validate_config()


def test_empty_tonapi_key_warns(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TONAPI_KEY", "")

    from config import validate_config
    warnings = validate_config()
    assert any("TONAPI_KEY" in w for w in warnings)


def test_empty_admin_ids_warns(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TONAPI_KEY", "key")
    monkeypatch.setenv("ADMIN_IDS", "")

    from config import validate_config
    warnings = validate_config()
    assert any("ADMIN_IDS" in w for w in warnings)


def test_non_numeric_admin_ids(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("ADMIN_IDS", "111,abc")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="non-numeric"):
        validate_config()


def test_poll_interval_too_low(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "0")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="POLL_INTERVAL_SEC"):
        validate_config()


def test_poll_interval_too_high(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "9999")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="POLL_INTERVAL_SEC"):
        validate_config()


def test_poll_interval_not_a_number(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "abc")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="POLL_INTERVAL_SEC"):
        validate_config()


def test_tonapi_min_interval_bounds(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TONAPI_MIN_INTERVAL", "0.01")

    from config import ConfigError, validate_config
    with pytest.raises(ConfigError, match="TONAPI_MIN_INTERVAL"):
        validate_config()


def test_valid_optional_vars(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("TONAPI_KEY", "key")
    monkeypatch.setenv("ADMIN_IDS", "111")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "30")
    monkeypatch.setenv("EVENTS_LIMIT", "50")
    monkeypatch.setenv("POLL_CONCURRENCY", "10")
    monkeypatch.setenv("TONAPI_MIN_INTERVAL", "2.0")

    from config import validate_config
    warnings = validate_config()
    assert warnings == []
