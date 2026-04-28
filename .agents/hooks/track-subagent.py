#!/usr/bin/env python3
"""Tracks the currently active subagent for per-agent scoping in guard-bash."""
from __future__ import annotations
import sys

from _lib.paths import project_dir
from _lib.io import read_hook_input


def main() -> int:
    payload = read_hook_input()
    event = payload.get("hook_event_name") or ""
    agent = payload.get("agent_name") or ""

    state_dir = project_dir() / ".agents" / "logs"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / ".active-subagent"

    if event == "SubagentStart":
        if agent:
            state_file.write_text(agent, encoding="utf-8")
    elif event == "SubagentStop":
        state_file.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
