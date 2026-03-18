"""Tests for utils/collections_store.py — pure collection list functions."""


from utils.collections_store import (
    add_collection,
    collections_match_set,
    load_collections,
    remove_collection,
    save_collections,
)

# ── load_collections ──

def test_load_empty_file(tmp_path):
    path = str(tmp_path / "cols.json")
    result = load_collections(path)
    assert result == []


def test_load_migration_from_string_list(tmp_path):
    import json
    path = str(tmp_path / "cols.json")
    with open(path, "w") as f:
        json.dump(["0:abc", "0:def"], f)
    result = load_collections(path)
    assert len(result) == 2
    assert result[0]["raw"] == "0:abc"
    assert result[0]["b64url"] == ""


def test_load_migration_empty_list(tmp_path):
    import json
    path = str(tmp_path / "cols.json")
    with open(path, "w") as f:
        json.dump([], f)
    result = load_collections(path)
    assert result == []


def test_load_normalizes_dicts(tmp_path):
    import json
    path = str(tmp_path / "cols.json")
    with open(path, "w") as f:
        json.dump([{"raw": "0:x", "b64url": "EQx", "name": "Test"}], f)
    result = load_collections(path)
    assert result[0]["raw"] == "0:x"
    assert result[0]["name"] == "Test"


def test_load_skips_non_dict_items(tmp_path):
    import json
    path = str(tmp_path / "cols.json")
    # Mixed: one valid dict, one invalid
    with open(path, "w") as f:
        json.dump([{"raw": "0:x", "b64url": "", "name": ""}, "not_a_dict"], f)
    result = load_collections(path)
    # Only the dict is included
    assert len(result) == 1


def test_load_invalid_json_returns_empty(tmp_path):
    path = str(tmp_path / "cols.json")
    with open(path, "w") as f:
        f.write("INVALID")
    result = load_collections(path)
    assert result == []


def test_load_non_list_json_returns_empty(tmp_path):
    import json
    path = str(tmp_path / "cols.json")
    with open(path, "w") as f:
        json.dump({"not": "a list"}, f)
    result = load_collections(path)
    assert result == []


# ── save_collections ──

def test_save_and_reload(tmp_path):
    path = str(tmp_path / "cols.json")
    items = [{"raw": "0:abc", "b64url": "EQabc", "name": "Test"}]
    save_collections(items, path)
    result = load_collections(path)
    assert result == items


# ── collections_match_set ──

def test_match_set_includes_raw_and_b64():
    items = [{"raw": "0:abc", "b64url": "EQabc", "name": ""}]
    s = collections_match_set(items)
    assert "0:abc" in s
    assert "EQabc" in s


def test_match_set_empty():
    assert collections_match_set([]) == set()


def test_match_set_skips_empty_values():
    items = [{"raw": "", "b64url": "", "name": ""}]
    assert collections_match_set(items) == set()


def test_match_set_skips_non_dicts():
    items = ["not_a_dict", {"raw": "0:x", "b64url": "EQx", "name": ""}]  # type: ignore
    s = collections_match_set(items)
    assert "0:x" in s


# ── add_collection ──

def test_add_new():
    items = []
    new_items, ok = add_collection(items, "0:new", "EQnew", "Name")
    assert ok is True
    assert len(new_items) == 1
    assert new_items[0]["raw"] == "0:new"


def test_add_dedup_by_raw():
    items = [{"raw": "0:dup", "b64url": "EQ1", "name": ""}]
    new_items, ok = add_collection(items, "0:dup", "EQ2", "")
    assert ok is False
    assert len(new_items) == 1


def test_add_dedup_by_b64url():
    items = [{"raw": "0:x", "b64url": "EQsame", "name": ""}]
    new_items, ok = add_collection(items, "0:y", "EQsame", "")
    assert ok is False


def test_add_strips_whitespace():
    items = []
    new_items, ok = add_collection(items, "  0:abc  ", "  EQabc  ", "  Name  ")
    assert ok is True
    assert new_items[0]["raw"] == "0:abc"
    assert new_items[0]["name"] == "Name"


# ── remove_collection ──

def test_remove_by_raw():
    items = [{"raw": "0:rm", "b64url": "EQrm", "name": ""}]
    new_items, ok = remove_collection(items, "0:rm")
    assert ok is True
    assert new_items == []


def test_remove_by_b64url():
    items = [{"raw": "0:x", "b64url": "EQremove", "name": ""}]
    new_items, ok = remove_collection(items, "EQremove")
    assert ok is True
    assert new_items == []


def test_remove_not_found():
    items = [{"raw": "0:x", "b64url": "EQx", "name": ""}]
    new_items, ok = remove_collection(items, "0:other")
    assert ok is False
    assert len(new_items) == 1


def test_remove_skips_non_dicts():
    items = ["not_a_dict"]  # type: ignore
    new_items, ok = remove_collection(items, "0:x")
    assert ok is False
    assert new_items == ["not_a_dict"]


def test_remove_strips_whitespace():
    items = [{"raw": "0:abc", "b64url": "EQabc", "name": ""}]
    new_items, ok = remove_collection(items, "  0:abc  ")
    assert ok is True
    assert new_items == []
