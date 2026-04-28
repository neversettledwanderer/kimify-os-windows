"""Path resolution for Kimify hooks."""
from __future__ import annotations
import os
from pathlib import Path


def project_dir() -> Path:
    """Resolve project directory from env vars, or walk up from cwd."""
    env = os.environ.get("KIMI_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    # Walk up looking for project markers
    for p in [cwd, *cwd.parents]:
        if (p / ".agents" / "hooks").exists() or (p / "kimi-config.toml").exists():
            return p
    return cwd


def relative_path(file_path: str) -> str:
    """Return *file_path* relative to the project root, using POSIX separators."""
    proj = project_dir()
    p = Path(file_path)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(proj).as_posix()
        except ValueError:
            return str(file_path).replace("\\", "/")
    resolved = (proj / p).resolve()
    try:
        return resolved.relative_to(proj).as_posix()
    except ValueError:
        return str(file_path).replace("\\", "/")
