"""Log appenders for Kimify hooks."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from .paths import project_dir


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def append_log(category: str, entry: str) -> None:
    """Append a timestamped line to .agents/logs/<category>.md."""
    log_dir = project_dir() / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{category}.md"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"- `{now_str()}` | {entry}\n")
