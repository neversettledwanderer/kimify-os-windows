#!/usr/bin/env python3
"""SessionStart(compact) hook — restores context after auto-compaction."""
from __future__ import annotations
import sys

from _lib.paths import project_dir


def main() -> int:
    log_dir = project_dir() / ".agents" / "logs"
    marker = log_dir / ".compaction-occurred"

    if not marker.exists():
        return 0

    compact_time = marker.read_text(encoding="utf-8").strip() or "unknown"

    # Reset session counters
    for name in (".tool-call-count", ".quality-gate-active"):
        p = log_dir / name
        if p.exists():
            p.unlink()

    # Clean up marker
    marker.unlink(missing_ok=True)

    print(
        f"POST-COMPACTION RESUME: Context was auto-compacted at {compact_time}. "
        "Session state was preserved in memory.md and daily note. "
        "Read .agents/memory.md and the latest Daily Note (look for the latest Session Handoff) "
        "to reload context, then continue working on whatever task was in progress. "
        "Do not ask the user what to do — just resume seamlessly."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
