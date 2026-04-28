#!/usr/bin/env python3
"""SessionStart(user) hook — resets stale state on fresh session start."""
from __future__ import annotations
import sys
from pathlib import Path

from _lib.paths import project_dir
from _lib.logging import now_str, append_log


def main() -> int:
    proj = project_dir()
    log_dir = proj / ".agents" / "logs"
    agents_dir = proj / ".agents" / "agents"
    hooks_dir = proj / ".agents" / "hooks"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 1. Reset stale gate files
    for name in (".quality-gate-active", ".tool-call-count", ".compaction-occurred"):
        (log_dir / name).unlink(missing_ok=True)

    # Clean up stale session-blocks files (older than 2 hours)
    import time
    now = time.time()
    for child in log_dir.glob(".session-blocks-*"):
        try:
            if child.is_file() and now - child.stat().st_mtime > 7200:
                child.unlink()
        except OSError:
            pass

    # 2. Validate hook scripts exist (no chmod on Windows — just check)
    if hooks_dir.exists():
        hook_issues = 0
        for hook in hooks_dir.glob("*.py"):
            if not hook.is_file():
                continue
            # On Windows, executable bit isn't meaningful; just check readability
            try:
                with hook.open("rb"):
                    pass
            except OSError:
                hook_issues += 1
        if hook_issues:
            append_log("incident-log", f"SESSION | INFO | {hook_issues} hook script(s) unreadable")

    # 3. Validate agent definitions have frontmatter
    if agents_dir.exists():
        issues = []
        for agent_dir in agents_dir.iterdir():
            md = agent_dir / "system.md"
            if md.exists():
                try:
                    first_line = md.read_text(encoding="utf-8").splitlines()[0] if md.stat().st_size else ""
                    if first_line.strip() != "---":
                        issues.append(f"{agent_dir.name}(no-frontmatter)")
                except OSError:
                    pass
        if issues:
            append_log("incident-log", f"SESSION | WARN | Agent issues: {' '.join(issues)}")

    # 4. Ensure required directories exist
    for sub in (
        proj / ".agents" / "agent-memory",
        proj / ".agents" / "backups",
        proj / ".agents" / "skills",
        proj / "Daily Notes",
    ):
        sub.mkdir(parents=True, exist_ok=True)

    # 5. Prune audit trail if > 5000 lines
    audit = log_dir / "audit-trail.md"
    if audit.exists():
        try:
            lines = audit.read_text(encoding="utf-8").splitlines()
            if len(lines) > 5000:
                audit.write_text("\n".join(lines[-2000:]) + "\n", encoding="utf-8")
                append_log(
                    "incident-log",
                    f"SESSION | INFO | Pruned audit trail from {len(lines)} to 2000 lines",
                )
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
