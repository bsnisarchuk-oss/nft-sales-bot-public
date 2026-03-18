"""Tests for utils/chat_config_store.py — JSON-based chat/collection storage."""

import pytest

from utils import chat_config_store as store


@pytest.fixture(autouse=True)
def tmp_data_dir(tmp_path, monkeypatch):
    """Each test gets a fresh isolated data directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    yield tmp_path


# ── load_cfg ──

def test_load_cfg_creates_default():
    cfg = store.load_cfg()
    assert isinstance(cfg, dict)
    assert "chats" in cfg
    assert isinstance(cfg["chats"], dict)


def test_load_cfg_handles_corrupt_file(tmp_path):
    path = tmp_path / "chats_config.json"
    path.write_text("NOT JSON", encoding="utf-8")
    cfg = store.load_cfg()
    assert "chats" in cfg


# ── bind_chat ──

def test_bind_chat_new():
    store.bind_chat(100, "Test Chat", 999)
    cfg = store.load_cfg()
    assert "100" in cfg["chats"]
    assert cfg["chats"]["100"]["enabled"] is True
    assert cfg["chats"]["100"]["title"] == "Test Chat"


def test_bind_chat_existing_updates_enabled():
    store.bind_chat(200, "Chat", 1)
    # Disable it
    store.set_enabled(200, False)
    # Re-bind should re-enable
    store.bind_chat(200, "Chat New", 2)
    cfg = store.load_cfg()
    assert cfg["chats"]["200"]["enabled"] is True
    assert cfg["chats"]["200"]["title"] == "Chat New"


def test_bind_chat_existing_no_title_keeps_old():
    store.bind_chat(300, "Old Title", 1)
    store.bind_chat(300, "", 2)
    cfg = store.load_cfg()
    assert cfg["chats"]["300"]["title"] == "Old Title"


# ── unbind_chat ──

def test_unbind_existing():
    store.bind_chat(400, "T", 0)
    result = store.unbind_chat(400)
    assert result is True
    assert "400" not in store.load_cfg()["chats"]


def test_unbind_nonexistent():
    result = store.unbind_chat(9999)
    assert result is False


# ── set_enabled ──

def test_set_enabled_existing():
    store.bind_chat(500, "T", 0)
    store.set_enabled(500, False)
    cfg = store.load_cfg()
    assert cfg["chats"]["500"]["enabled"] is False


def test_set_enabled_creates_new_entry():
    # Chat not bound yet — set_enabled still creates it
    store.set_enabled(600, True)
    cfg = store.load_cfg()
    assert "600" in cfg["chats"]
    assert cfg["chats"]["600"]["enabled"] is True


# ── enabled_chats ──

def test_enabled_chats_returns_enabled_only():
    store.bind_chat(700, "A", 0)
    store.bind_chat(701, "B", 0)
    store.set_enabled(701, False)
    result = store.enabled_chats()
    assert 700 in result
    assert 701 not in result


def test_enabled_chats_empty():
    result = store.enabled_chats()
    assert result == []


# ── list_chats ──

def test_list_chats_sorted():
    store.bind_chat(30, "C", 0)
    store.bind_chat(10, "A", 0)
    store.bind_chat(20, "B", 0)
    chats = store.list_chats()
    ids = [c["chat_id"] for c in chats]
    assert ids == sorted(ids)


def test_list_chats_includes_collections_count():
    store.bind_chat(800, "T", 0)
    store.add_collection(800, "0:abc", "EQabc", "NFT")
    chats = store.list_chats()
    c = next(x for x in chats if x["chat_id"] == 800)
    assert c["collections_count"] == 1


# ── get_collections ──

def test_get_collections_empty():
    store.bind_chat(900, "T", 0)
    result = store.get_collections(900)
    assert result == []


def test_get_collections_nonexistent_chat():
    result = store.get_collections(9999)
    assert result == []


def test_get_collections_returns_normalized():
    store.bind_chat(1000, "T", 0)
    store.add_collection(1000, "0:abc", "EQabc", "TestNFT")
    cols = store.get_collections(1000)
    assert len(cols) == 1
    assert cols[0]["raw"] == "0:abc"
    assert cols[0]["b64url"] == "EQabc"
    assert cols[0]["name"] == "TestNFT"


# ── tracked_set ──

def test_tracked_set_includes_both_raw_and_b64():
    store.bind_chat(1100, "T", 0)
    store.add_collection(1100, "0:abc", "EQabc", "")
    s = store.tracked_set(1100)
    assert "0:abc" in s
    assert "EQabc" in s


def test_tracked_set_empty_chat():
    assert store.tracked_set(9999) == set()


# ── add_collection ──

def test_add_collection_success():
    store.bind_chat(1200, "T", 0)
    ok = store.add_collection(1200, "0:new", "EQnew", "Name")
    assert ok is True
    assert len(store.get_collections(1200)) == 1


def test_add_collection_dedup_by_raw():
    store.bind_chat(1300, "T", 0)
    store.add_collection(1300, "0:dup", "EQ1", "N")
    ok = store.add_collection(1300, "0:dup", "EQ2", "N2")
    assert ok is False
    assert len(store.get_collections(1300)) == 1


def test_add_collection_dedup_by_b64url():
    store.bind_chat(1400, "T", 0)
    store.add_collection(1400, "0:x", "EQsame", "N")
    ok = store.add_collection(1400, "0:y", "EQsame", "N2")
    assert ok is False


def test_add_collection_creates_chat_if_missing():
    ok = store.add_collection(1500, "0:abc", "EQabc", "N")
    assert ok is True
    assert len(store.get_collections(1500)) == 1


# ── remove_collection ──

def test_remove_collection_by_raw():
    store.bind_chat(1600, "T", 0)
    store.add_collection(1600, "0:rm", "EQrm", "N")
    ok = store.remove_collection(1600, "0:rm")
    assert ok is True
    assert store.get_collections(1600) == []


def test_remove_collection_by_b64url():
    store.bind_chat(1700, "T", 0)
    store.add_collection(1700, "0:x", "EQremove", "N")
    ok = store.remove_collection(1700, "EQremove")
    assert ok is True


def test_remove_collection_not_found():
    store.bind_chat(1800, "T", 0)
    ok = store.remove_collection(1800, "0:none")
    assert ok is False


def test_remove_collection_chat_not_bound():
    ok = store.remove_collection(9999, "0:x")
    assert ok is False


# ── set_collection_name ──

def test_set_collection_name_success():
    store.bind_chat(1900, "T", 0)
    store.add_collection(1900, "0:named", "EQnamed", "OldName")
    ok = store.set_collection_name(1900, "0:named", "NewName")
    assert ok is True
    cols = store.get_collections(1900)
    assert cols[0]["name"] == "NewName"


def test_set_collection_name_chat_missing():
    ok = store.set_collection_name(9999, "0:x", "Name")
    assert ok is False


def test_set_collection_name_empty_args():
    ok = store.set_collection_name(1900, "", "Name")
    assert ok is False
    ok2 = store.set_collection_name(1900, "0:x", "")
    assert ok2 is False


# ── all_tracked_collections ──

def test_all_tracked_collections_multiple_chats():
    store.bind_chat(2000, "A", 0)
    store.bind_chat(2001, "B", 0)
    store.add_collection(2000, "0:col1", "EQ1", "")
    store.add_collection(2001, "0:col2", "EQ2", "")
    result = store.all_tracked_collections()
    assert "0:col1" in result
    assert "0:col2" in result


def test_all_tracked_collections_skips_disabled():
    store.bind_chat(2100, "T", 0)
    store.add_collection(2100, "0:disabled", "EQd", "")
    store.set_enabled(2100, False)
    result = store.all_tracked_collections()
    assert "0:disabled" not in result


# ── clear_chat_collections ──

def test_clear_chat_collections():
    store.bind_chat(2200, "T", 0)
    store.add_collection(2200, "0:a", "EQa", "")
    store.add_collection(2200, "0:b", "EQb", "")
    n = store.clear_chat_collections(2200)
    assert n == 2
    assert store.get_collections(2200) == []


def test_clear_chat_collections_missing_chat():
    n = store.clear_chat_collections(9999)
    assert n == 0
