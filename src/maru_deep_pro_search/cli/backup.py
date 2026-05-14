"""Config backup and restore utilities."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup of a file. Returns backup path or None."""
    if not path.exists():
        return None
    backup_path = path.with_suffix(f"{path.suffix}.bak.{_timestamp()}")
    shutil.copy2(path, backup_path)
    return backup_path


def restore_file(path: Path, backup_path: Path) -> bool:
    """Restore a file from its backup. Returns True on success."""
    if not backup_path.exists():
        return False
    shutil.copy2(backup_path, path)
    return True


def read_json_safe(path: Path) -> dict[str, Any]:
    """Read a JSON file, return {} if missing or corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_json_safe(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_text_safe(path: Path) -> str:
    """Read a text file, return "" if missing."""
    if not path.exists():
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def write_text_safe(path: Path, content: str) -> None:
    """Write a text file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def backup_dir(path: Path) -> Path | None:
    """Create a timestamped backup of a directory. Returns backup path or None."""
    if not path.exists():
        return None
    backup_path = path.with_suffix(f".bak.{_timestamp()}")
    shutil.copytree(path, backup_path)
    return backup_path


def restore_dir(path: Path, backup_path: Path) -> bool:
    """Restore a directory from its backup. Returns True on success."""
    if not backup_path.exists():
        return False
    if path.exists():
        shutil.rmtree(path)
    shutil.copytree(backup_path, path)
    return True
