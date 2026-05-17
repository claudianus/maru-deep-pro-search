"""Self-update utilities for maru-deep-pro-search.

Checks PyPI for newer versions and can optionally auto-update
via `pip` or `uv pip` (when `uv` is on PATH). Respects cooldown periods
to avoid excessive checks.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

PACKAGE_NAME = "maru-deep-pro-search"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"

SETUP_REPAIR_HINT = "다음: maru-deep-pro-search setup --repair (또는 update --with-setup)"


def _get_installed_version() -> str:
    """Return the currently installed version."""
    try:
        from importlib.metadata import version

        return version(PACKAGE_NAME)
    except Exception:
        # Fallback: parse from pyproject.toml if running from source
        try:
            import tomllib

            pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
            if pyproject.exists():
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                    return str(data["project"]["version"])
        except Exception:
            pass
    return "0.0.0"


def _get_latest_version() -> str | None:
    """Query PyPI for the latest released version."""
    try:
        req = Request(
            PYPI_URL,
            headers={
                "Accept": "application/json",
                "User-Agent": f"{PACKAGE_NAME}/{_get_installed_version()}",
            },
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return str(data["info"]["version"])
    except Exception as exc:
        logger.debug("Failed to check latest version: %s", exc)
        return None


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a semantic version string into a sortable tuple."""
    # Remove any pre-release suffixes for comparison
    v = re.split(r"[-+]", v)[0]
    parts = v.split(".")
    return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])


def _version_is_newer(current: str, latest: str) -> bool:
    """Return True if latest is strictly newer than current."""
    return _parse_version(latest) > _parse_version(current)


@dataclass
class UpdateCheckResult:
    """Result of an update check."""

    current_version: str
    latest_version: str | None
    update_available: bool
    error: str | None = None


def check_for_update() -> UpdateCheckResult:
    """Check whether a newer version is available on PyPI."""
    current = _get_installed_version()
    latest = _get_latest_version()

    if latest is None:
        return UpdateCheckResult(
            current_version=current,
            latest_version=None,
            update_available=False,
            error="Could not reach PyPI or parse response.",
        )

    return UpdateCheckResult(
        current_version=current,
        latest_version=latest,
        update_available=_version_is_newer(current, latest),
    )


def should_check_update() -> bool:
    """Return True unless the user has explicitly disabled update checks."""
    return not os.getenv("MARU_SKIP_UPDATE_CHECK")


def get_update_notice(result: UpdateCheckResult) -> str | None:
    """Return a human-readable update notice, or None if no update."""
    if not result.update_available or result.latest_version is None:
        return None

    return (
        f"\n"
        f"┌─────────────────────────────────────────────────────────────┐\n"
        f"│  🔔 Update available for {PACKAGE_NAME}\n"
        f"│     Installed: {result.current_version}\n"
        f"│     Latest:    {result.latest_version}\n"
        f"│\n"
        f"│  Run:  maru-deep-pro-search update --with-setup\n"
        f"│     or  pip install -U {PACKAGE_NAME} && setup --repair\n"
        f"└─────────────────────────────────────────────────────────────┘\n"
    )


def auto_setup_enabled(cli_with_setup: bool = False) -> bool:
    """True when post-update agent repair should run."""
    if cli_with_setup:
        return True
    return os.environ.get("MARU_UPDATE_AUTO_SETUP", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def perform_update(dry_run: bool = False, *, with_setup: bool = False) -> tuple[bool, str]:
    """Attempt to update the package in-place.

    Returns (success, message).
    """
    current = _get_installed_version()
    latest = _get_latest_version()

    if latest is None:
        return False, "❌ Could not determine latest version. Check your network."

    if not _version_is_newer(current, latest):
        return True, f"✅ Already up to date ({current})."

    if dry_run:
        return True, f"📦 Would update {current} → {latest}"

    # Determine the best install command
    cmds: list[list[str]] = []

    # Prefer uv if available (fast, reliable)
    if shutil.which("uv"):
        cmds.append(["uv", "pip", "install", "--upgrade", PACKAGE_NAME])
    # Also try pipx if it looks like a pipx install
    if shutil.which("pipx"):
        cmds.append(["pipx", "upgrade", PACKAGE_NAME])
    # Fallback to pip
    cmds.append([sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME])

    for cmd in cmds:
        try:
            logger.info("Running: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            if result.returncode == 0:
                msg = (
                    f"✅ {PACKAGE_NAME} 업데이트 완료\n"
                    f"   {current} → {latest}\n"
                    f"   MCP를 쓰는 에이전트(Cursor, Claude 등)를 재시작하세요."
                )
                if not auto_setup_enabled(with_setup):
                    msg += f"\n   {SETUP_REPAIR_HINT}"
                return True, msg
            else:
                logger.debug("Command failed: %s", result.stderr)
                continue
        except Exception as exc:
            logger.debug("Update attempt failed: %s", exc)
            continue

    return False, (
        f"❌ Update failed ({current} → {latest}).\n   Try manually: pip install -U {PACKAGE_NAME}"
    )


# Auto-check on startup (non-blocking)
def maybe_notify_update() -> str | None:
    """Perform a background update check and return notice if available.

    Skipped if MARU_SKIP_UPDATE_CHECK is set.
    """
    if not should_check_update():
        return None

    result = check_for_update()
    return get_update_notice(result)
