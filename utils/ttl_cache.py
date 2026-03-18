import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 5000) -> None:
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if not item:
            return None

        exp, val = item
        if exp < time.time():
            self._data.pop(key, None)
            return None

        return val

    def set(self, key: str, val: Any) -> None:
        # если данных слишком много — сначала пробуем удалить протухшие
        if len(self._data) >= self.max_size:
            now = time.time()
            for k in list(self._data.keys()):
                exp, _ = self._data[k]
                if exp < now:
                    self._data.pop(k, None)

        # если всё ещё много — удаляем первые N ключей
        if len(self._data) >= self.max_size:
            delete_count = max(1, self.max_size // 10)
            for k in list(self._data.keys())[:delete_count]:
                self._data.pop(k, None)

        self._data[key] = (time.time() + self.ttl, val)
