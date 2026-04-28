#!/usr/bin/env python3
"""PreCompact hook — saves a marker before auto-compaction."""
from __future__ import annotations
import sys

from _lib.paths import project_dir
from _lib.logging import append_log, now_str


def main() -> int:
    log_dir = project_dir() / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    marker = log_dir / ".compaction-occurred"
    marker.write_text(now_str(), encoding="utf-8")
    append_log("incident-log", "COMPACTION | INFO | Auto-compaction triggered — state saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
