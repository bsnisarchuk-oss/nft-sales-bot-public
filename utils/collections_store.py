import os
from typing import Dict, List, Tuple

from utils.storage import ensure_file, load_json, save_json

# Collection = {"raw": "...", "b64url": "...", "name": "..."}
Collection = Dict[str, str]


def _default_path() -> str:
    data_dir = os.getenv("DATA_DIR", "data")
    return os.path.join(data_dir, "collections.json")


def load_collections(path: str | None = None) -> List[Collection]:
    path = path or _default_path()
    ensure_file(path, default_content=[])
    data = load_json(path, default=[])

    # миграция со старого формата (list[str])
    if isinstance(data, list) and (len(data) == 0 or isinstance(data[0], str)):
        return [{"raw": s, "b64url": "", "name": ""} for s in data if isinstance(s, str)]

    # нормализация: убеждаемся, что все ключи есть
    if isinstance(data, list):
        return [
            {
                "raw": str(x.get("raw", "")).strip(),
                "b64url": str(x.get("b64url", "")).strip(),
                "name": str(x.get("name", "")).strip(),
            }
            for x in data
            if isinstance(x, dict)
        ]

    return []


def save_collections(items: List[Collection], path: str | None = None) -> None:
    path = path or _default_path()
    save_json(path, items)


def collections_match_set(items: List[Collection]) -> set[str]:
    """Возвращает set из raw и b64url для быстрого поиска."""
    out = set()
    for it in items:
        if isinstance(it, dict):
            raw = it.get("raw", "").strip()
            b64url = it.get("b64url", "").strip()
            if raw:
                out.add(raw)
            if b64url:
                out.add(b64url)
    return out


def add_collection(
    items: List[Collection], raw: str, b64url: str, name: str = ""
) -> Tuple[List[Collection], bool]:
    """Добавляет коллекцию, если её ещё нет. Возвращает (новый список, успех)."""
    raw = raw.strip()
    b64url = b64url.strip()
    name = name.strip()

    match_set = collections_match_set(items)
    if raw in match_set or b64url in match_set:
        return items, False

    items.append({"raw": raw, "b64url": b64url, "name": name})
    return items, True


def remove_collection(items: List[Collection], raw_or_b64: str) -> Tuple[List[Collection], bool]:
    """Удаляет коллекцию по raw или b64url. Возвращает (новый список, был_удалён)."""
    key = raw_or_b64.strip()
    new_items = []
    removed = False
    for it in items:
        if isinstance(it, dict):
            if it.get("raw", "").strip() == key or it.get("b64url", "").strip() == key:
                removed = True
                continue
        new_items.append(it)
    return new_items, removed
