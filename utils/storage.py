import json
import os
import tempfile
from typing import Any


# JSON storage helpers: функции для безопасного чтения/записи данных в JSON-файлы.
def ensure_file(path: str, default_content: Any) -> None:
    """
    Гарантирует существование JSON-файла по указанному пути.
    Если файл отсутствует — создаёт его с переданным содержимым.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        save_json(path, default_content)


def load_json(path: str, default: Any) -> Any:
    """
    Загружает данные из JSON-файла.
    При ошибке или отсутствии файла возвращает значение по умолчанию.
    """
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return default


def save_json(path: str, data: Any) -> None:
    """
    Сохраняет данные в JSON-файл "атомарно":
    сначала пишет во временный файл, затем заменяет им основной.
    Это уменьшает риск порчи данных при сбое.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # atomic write
    dir_name = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_name, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name

    os.replace(tmp_path, path)
