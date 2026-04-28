#!/usr/bin/env python3
"""PreToolUse async hook — creates timestamped backups before Write|Edit."""
from __future__ import annotations
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from _lib.paths import project_dir, relative_path
from _lib.io import read_hook_input


def main() -> int:
    payload = read_hook_input()
    file_path = payload.get("tool_input", {}).get("file_path") or ""

    if not file_path:
        return 0

    proj = project_dir()
    src = (proj / file_path).resolve()
    if not src.is_file():
        return 0

    rel = relative_path(file_path)
    if ".agents/logs/" in rel or ".agents/backups/" in rel:
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    backup_dir = proj / ".agents" / "backups" / today
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
    dst = backup_dir / f"{src.name}.{timestamp}.bak"
    shutil.copy2(src, dst)

    # Prune backup directories older than 7 days
    backups_root = proj / ".agents" / "backups"
    if backups_root.exists():
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for child in backups_root.iterdir():
            if child.is_dir():
                try:
                    mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        shutil.rmtree(child)
                except OSError:
                    pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
