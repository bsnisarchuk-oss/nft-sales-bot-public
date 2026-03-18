"""
Creates a handover archive with preflight validation, manifest, and SHA256 checksum.

Usage:
  python tools/make_handover.py
  python tools/make_handover.py --dry-run
  python tools/make_handover.py --skip-preflight
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_NAME = "nft-sales-bot"

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".claude",
    "data",
}

EXCLUDE_FILES = {
    ".env",
    "bot_stdout.log",
    "bot_stderr.log",
}

EXCLUDE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.log",
    "*.zip",
    "*.sha256",
    "processed_events*.json",
    "*cache*",
]


def _run_preflight(skip_preflight: bool) -> None:
    if skip_preflight:
        print("Preflight skipped by flag.")
        return
    cp = subprocess.run(
        [sys.executable, "tools/preflight.py"],
        cwd=ROOT,
        text=True,
    )
    if cp.returncode != 0:
        raise RuntimeError("Preflight failed. Fix issues before handover packaging.")


def _check_local_env_has_real_secrets(allow_local_secrets: bool) -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    bot_token = ""
    tonapi_key = ""
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k == "BOT_TOKEN":
            bot_token = v
        elif k == "TONAPI_KEY":
            tonapi_key = v

    looks_real_bot_token = bool(bot_token and "YOUR_" not in bot_token and ":" in bot_token)
    looks_real_tonapi = bool(tonapi_key and "YOUR_" not in tonapi_key)

    if (looks_real_bot_token or looks_real_tonapi) and not allow_local_secrets:
        raise RuntimeError(
            "Local .env contains real-looking secrets. Rotate/review secrets first or pass "
            "--allow-local-secrets intentionally."
        )


def _is_excluded(rel_path: str) -> bool:
    parts = rel_path.split(os.sep)
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if os.path.basename(rel_path) in EXCLUDE_FILES:
        return True
    base = os.path.basename(rel_path)
    return any(fnmatch.fnmatch(base, p) for p in EXCLUDE_PATTERNS)


def _collect_files(out_name: str) -> list[Path]:
    files: list[Path] = []
    for root, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in fs:
            p = Path(root) / f
            rel = p.relative_to(ROOT)
            rel_str = str(rel)
            if rel_str == out_name or rel_str == f"{out_name}.sha256":
                continue
            if _is_excluded(rel_str):
                continue
            files.append(p)
    files.sort(key=lambda p: str(p.relative_to(ROOT)))
    return files


def _git_commit() -> str:
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return cp.stdout.strip()
    except Exception:
        return "unknown"


def _manifest(files: list[Path]) -> str:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rels = [str(p.relative_to(ROOT)).replace("\\", "/") for p in files]
    lines = [
        "Handover Manifest",
        f"project: {PROJECT_NAME}",
        f"generated_at_utc: {ts}",
        f"git_commit: {_git_commit()}",
        f"file_count: {len(rels)}",
        "",
        "files:",
    ]
    lines.extend([f"- {r}" for r in rels])
    return "\n".join(lines) + "\n"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--allow-local-secrets", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--name", default=f"{PROJECT_NAME}-handover-{time.strftime('%Y%m%d-%H%M')}.zip")
    args = parser.parse_args()

    _run_preflight(skip_preflight=args.skip_preflight)
    _check_local_env_has_real_secrets(allow_local_secrets=args.allow_local_secrets)

    out = ROOT / args.name
    files = _collect_files(out.name)
    manifest = _manifest(files)

    if args.dry_run:
        print(f"Dry-run OK. Files to include: {len(files)}")
        print(f"Archive name: {out.name}")
        return 0

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as zf:
        for p in files:
            rel = p.relative_to(ROOT)
            zf.write(p, rel)
        zf.writestr("HANDOVER_MANIFEST.txt", manifest)

    digest = _sha256(out)
    sha_path = Path(f"{out}.sha256")
    sha_path.write_text(f"{digest}  {out.name}\n", encoding="utf-8")

    print(f"Created: {out}")
    print(f"Created: {sha_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
