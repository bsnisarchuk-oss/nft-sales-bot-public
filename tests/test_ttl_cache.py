"""Tests for utils/ttl_cache.py — TTL-кэш с ограничением по размеру."""

import time
from unittest.mock import patch

from utils.ttl_cache import TTLCache


def test_set_and_get():
    c = TTLCache(ttl_seconds=60, max_size=10)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"


def test_get_nonexistent():
    c = TTLCache(ttl_seconds=60, max_size=10)
    assert c.get("missing") is None


def test_overwrite():
    c = TTLCache(ttl_seconds=60, max_size=10)
    c.set("k1", "old")
    c.set("k1", "new")
    assert c.get("k1") == "new"


def test_expired_key():
    c = TTLCache(ttl_seconds=1, max_size=10)
    c.set("k1", "val")
    # Подменяем время — ключ протух
    with patch("utils.ttl_cache.time.time", return_value=time.time() + 10):
        assert c.get("k1") is None


def test_max_size_eviction():
    c = TTLCache(ttl_seconds=60, max_size=3)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    # 4-й ключ вызовет eviction
    c.set("d", 4)
    assert c.get("d") == 4
    # Размер не превышает max_size
    assert len(c._data) <= 3


def test_cleanup_expired_on_full():
    c = TTLCache(ttl_seconds=1, max_size=3)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    # Протухнем все ключи
    now = time.time()
    for k in c._data:
        c._data[k] = (now - 1, c._data[k][1])
    # Добавляем новый — протухшие должны удалиться
    c.set("d", 4)
    assert c.get("d") == 4
    # Протухшие удалены
    assert c.get("a") is None
    assert c.get("b") is None
    assert c.get("c") is None
