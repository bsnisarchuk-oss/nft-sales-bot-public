import os
import time
from typing import List

from utils.storage import ensure_file, load_json, save_json


def _path() -> str:
    data_dir = os.getenv("DATA_DIR", "data")
    return os.path.join(data_dir, "chats_config.json")


def load_cfg() -> dict:
    ensure_file(_path(), default_content={"version": 1, "chats": {}})
    cfg = load_json(_path(), default={"version": 1, "chats": {}})
    if not isinstance(cfg, dict):
        cfg = {"version": 1, "chats": {}}
    if "chats" not in cfg or not isinstance(cfg["chats"], dict):
        cfg["chats"] = {}
    return cfg


def save_cfg(cfg: dict) -> None:
    save_json(_path(), cfg)


def bind_chat(chat_id: int, title: str = "", added_by: int = 0) -> None:
    cfg = load_cfg()
    chats = cfg["chats"]
    key = str(chat_id)
    if key not in chats:
        chats[key] = {
            "enabled": True,
            "title": title,
            "added_by": added_by,
            "added_at": int(time.time()),
            "collections": [],  # ВАЖНО: отдельные коллекции на чат
        }
    else:
        chats[key]["enabled"] = True
        if title:
            chats[key]["title"] = title
    save_cfg(cfg)


def unbind_chat(chat_id: int) -> bool:
    cfg = load_cfg()
    removed = cfg["chats"].pop(str(chat_id), None) is not None
    save_cfg(cfg)
    return removed


def set_enabled(chat_id: int, enabled: bool) -> None:
    cfg = load_cfg()
    key = str(chat_id)
    if key not in cfg["chats"]:
        cfg["chats"][key] = {
            "enabled": bool(enabled),
            "title": "",
            "added_by": 0,
            "added_at": int(time.time()),
            "collections": [],
        }
    cfg["chats"][key]["enabled"] = bool(enabled)
    save_cfg(cfg)


def enabled_chats() -> List[int]:
    cfg = load_cfg()
    out = []
    for k, v in cfg["chats"].items():
        if isinstance(v, dict) and v.get("enabled", True):
            out.append(int(k))
    return out


def list_chats() -> List[dict]:
    cfg = load_cfg()
    out = []
    for k, v in cfg["chats"].items():
        if not isinstance(v, dict):
            continue
        cols = v.get("collections") or []
        out.append(
            {
                "chat_id": int(k),
                "enabled": bool(v.get("enabled", True)),
                "title": str(v.get("title", "")),
                "collections_count": len(cols) if isinstance(cols, list) else 0,
            }
        )
    def _sort_key(item: dict) -> int:
        v = item.get("chat_id")
        return int(v) if isinstance(v, (int, str)) else 0

    out.sort(key=_sort_key)
    return out


def get_collections(chat_id: int) -> List[dict]:
    cfg = load_cfg()
    v = cfg["chats"].get(str(chat_id))
    if not isinstance(v, dict):
        return []
    cols = v.get("collections") or []
    if not isinstance(cols, list):
        return []
    # гарантируем формат {"raw","b64url","name"}
    out = []
    for x in cols:
        if isinstance(x, dict):
            out.append(
                {
                    "raw": str(x.get("raw", "")).strip(),
                    "b64url": str(x.get("b64url", "")).strip(),
                    "name": str(x.get("name", "")).strip(),
                }
            )
    return out


def tracked_set(chat_id: int) -> set[str]:
    items = get_collections(chat_id)
    s = set()
    for it in items:
        if it.get("raw"):
            s.add(it["raw"])
        if it.get("b64url"):
            s.add(it["b64url"])
    return s


def add_collection(chat_id: int, raw: str, b64url: str, name: str = "") -> bool:
    cfg = load_cfg()
    key = str(chat_id)
    if key not in cfg["chats"]:
        cfg["chats"][key] = {
            "enabled": True,
            "title": "",
            "added_by": 0,
            "added_at": int(time.time()),
            "collections": [],
        }

    cols = get_collections(chat_id)

    # дедуп
    for it in cols:
        if it.get("raw") == raw or (b64url and it.get("b64url") == b64url):
            return False

    cols.append({"raw": raw, "b64url": b64url, "name": name})
    cfg["chats"][key]["collections"] = cols
    save_cfg(cfg)
    return True


def remove_collection(chat_id: int, raw_or_b64: str) -> bool:
    cfg = load_cfg()
    key = str(chat_id)
    if key not in cfg["chats"]:
        return False

    cols = get_collections(chat_id)
    new_cols = []
    removed = False
    for it in cols:
        if it.get("raw") == raw_or_b64 or it.get("b64url") == raw_or_b64:
            removed = True
            continue
        new_cols.append(it)

    cfg["chats"][key]["collections"] = new_cols
    save_cfg(cfg)
    return removed


def set_collection_name(chat_id: int, raw: str, name: str) -> bool:
    raw = str(raw).strip()
    name = str(name).strip()
    if not raw or not name:
        return False

    cfg = load_cfg()
    key = str(chat_id)

    if key not in cfg.get("chats", {}):
        return False

    cols = cfg["chats"][key].get("collections") or []
    if not isinstance(cols, list):
        return False

    updated = False
    for it in cols:
        if isinstance(it, dict) and str(it.get("raw", "")).strip() == raw:
            it["name"] = name
            updated = True

    if updated:
        cfg["chats"][key]["collections"] = cols
        save_cfg(cfg)

    return updated


def all_tracked_collections() -> set[str]:
    """Все уникальные raw-адреса коллекций из всех enabled чатов (JSON fallback)."""
    cfg = load_cfg()
    result: set[str] = set()
    for k, v in cfg["chats"].items():
        if not isinstance(v, dict):
            continue
        if not v.get("enabled", True):
            continue
        for col in v.get("collections") or []:
            if isinstance(col, dict):
                raw = (col.get("raw") or "").strip()
                if raw:
                    result.add(raw)
    return result


def clear_chat_collections(chat_id: int) -> int:
    cfg = load_cfg()
    key = str(chat_id)
    if key not in cfg.get("chats", {}):
        return 0
    cols = cfg["chats"][key].get("collections", [])
    n = len(cols) if isinstance(cols, list) else 0
    cfg["chats"][key]["collections"] = []
    save_cfg(cfg)
    return n
