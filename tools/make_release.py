"""
Создаёт zip-архив релиза проекта (без .git, .venv, data, .env и т.д.).
Запуск: из корня репозитория — python tools/make_release.py
"""
import fnmatch
import os
import time
import zipfile

PROJECT_NAME = "nft-sales-bot"
OUT = f"{PROJECT_NAME}-release-{time.strftime('%Y%m%d-%H%M')}.zip"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "data",  # runtime DB/data
}
EXCLUDE_FILES = {".env"}
EXCLUDE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.log",
    "processed_events*.json",
    "*cache*",
]


def is_excluded(rel_path: str) -> bool:
    for part in rel_path.split(os.sep):
        if part in EXCLUDE_DIRS:
            return True
    if os.path.basename(rel_path) in EXCLUDE_FILES:
        return True
    base = os.path.basename(rel_path)
    for pat in EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(base, pat):
            return True
    return False


def main() -> None:
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                path = os.path.join(root, f)
                rel = os.path.relpath(path, ".")
                if rel == OUT:
                    continue
                if is_excluded(rel):
                    continue
                z.write(path, rel)
    print("Created:", OUT)


if __name__ == "__main__":
    main()
