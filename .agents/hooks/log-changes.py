#!/usr/bin/env python3
"""PostToolUse hook — appends every Write|Edit to audit trail."""
from __future__ import annotations
import sys

from _lib.paths import project_dir, relative_path
from _lib.io import read_hook_input
from _lib.logging import now_str


def main() -> int:
    payload = read_hook_input()
    file_path = payload.get("tool_input", {}).get("file_path") or ""
    tool = payload.get("tool_name") or ""

    if not file_path:
        return 0

    relative = relative_path(file_path)
    proj = project_dir()

    log_dir = proj / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    audit_trail = log_dir / "audit-trail.md"
    with audit_trail.open("a", encoding="utf-8") as f:
        f.write(f"- `{now_str()}` | {tool} | {relative}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
