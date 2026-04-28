"""TOML validation helpers."""
from __future__ import annotations
import tomllib
from pathlib import Path


def validate_toml(path: Path) -> bool:
    """Return True if *path* is valid TOML."""
    try:
        with path.open("rb") as f:
            tomllib.load(f)
        return True
    except Exception:
        return False


def validate_toml_text(text: str) -> bool:
    """Return True if *text* is valid TOML."""
    try:
        tomllib.loads(text)
        return True
    except Exception:
        return False
