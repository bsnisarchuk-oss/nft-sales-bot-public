import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _git_ls_files() -> list[str]:
    try:
        cp = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""


def check_required_files() -> list[str]:
    required = [
        "LICENSE",
        ".github/workflows/ci.yml",
        "docs/DEPLOY.md",
        "docs/OPERATIONS.md",
        "docs/DATA_POLICY.md",
        "docs/SECRET_ROTATION.md",
        "docs/BUYER_HANDOVER.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/SMOKE_TEST.md",
        "tools/container_healthcheck.py",
        "tools/make_handover.py",
    ]
    fails: list[str] = []
    for rel in required:
        if not (ROOT / rel).exists():
            fails.append(f"missing required file: {rel}")
    return fails


def check_security_hygiene(tracked_files: list[str]) -> list[str]:
    fails: list[str] = []

    tracked = set(tracked_files)
    if ".env" in tracked:
        fails.append(".env is tracked by git")

    for forbidden in ("bot_stdout.log", "bot_stderr.log"):
        if forbidden in tracked:
            fails.append(f"runtime log is tracked by git: {forbidden}")

    token_re = re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{35}\b")
    private_key_markers = ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY")

    text_like_ext = {
        ".py",
        ".md",
        ".yml",
        ".yaml",
        ".toml",
        ".txt",
        ".json",
        ".ini",
        ".cfg",
        ".env",
        ".example",
        "",
    }
    skip_names = {".env.example", "tools/preflight.py"}

    for rel in tracked_files:
        if rel in skip_names:
            continue

        p = ROOT / rel
        if not p.exists() or p.is_dir():
            continue

        if p.suffix.lower() not in text_like_ext and p.name not in {".dockerignore", ".gitignore"}:
            continue

        text = _read_text(p)
        if not text:
            continue

        if token_re.search(text):
            fails.append(f"possible Telegram bot token in tracked file: {rel}")

        for marker in private_key_markers:
            if marker in text:
                fails.append(f"private key marker found in tracked file: {rel}")
                break

    return fails


def check_versions_consistency() -> list[str]:
    fails: list[str] = []
    pyproject = _read_text(ROOT / "pyproject.toml")
    readme = _read_text(ROOT / "README.md")

    if 'requires-python = ">=3.10"' not in pyproject:
        fails.append('pyproject.toml missing expected requires-python ">=3.10"')

    if "Python 3.10+" not in readme:
        fails.append("README.md missing expected Python 3.10+ requirement")

    return fails


def check_container_hardening() -> list[str]:
    fails: list[str] = []

    dockerfile = _read_text(ROOT / "Dockerfile")
    compose = _read_text(ROOT / "docker-compose.yml")

    docker_expect = [
        "USER app:app",
        "HEALTHCHECK",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONUNBUFFERED",
    ]
    compose_expect = [
        "healthcheck:",
        "security_opt:",
        "no-new-privileges:true",
        "cap_drop:",
        "tmpfs:",
    ]

    for token in docker_expect:
        if token not in dockerfile:
            fails.append(f"Dockerfile hardening token missing: {token}")

    for token in compose_expect:
        if token not in compose:
            fails.append(f"docker-compose hardening token missing: {token}")

    return fails


def check_ci_pipeline() -> list[str]:
    fails: list[str] = []
    ci = _read_text(ROOT / ".github/workflows/ci.yml")
    for token in ("Ruff", "Mypy", "Pytest"):
        if token not in ci:
            fails.append(f"CI job missing stage: {token}")
    return fails


def main() -> int:
    tracked_files = _git_ls_files()

    all_fails: list[str] = []
    checks = [
        ("required files", check_required_files()),
        ("security hygiene", check_security_hygiene(tracked_files)),
        ("version consistency", check_versions_consistency()),
        ("container hardening", check_container_hardening()),
        ("ci pipeline", check_ci_pipeline()),
    ]

    for name, fails in checks:
        if fails:
            _fail(f"{name}: {len(fails)} issue(s)")
            for msg in fails:
                _fail(f"  - {msg}")
            all_fails.extend(fails)
        else:
            _ok(f"{name}")

    if all_fails:
        print(f"\nPreflight: FAILED ({len(all_fails)} issue(s))")
        return 1

    print("\nPreflight: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
