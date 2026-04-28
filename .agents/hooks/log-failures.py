#!/usr/bin/env python3
"""PostToolUseFailure hook — categorises and logs tool failures."""
from __future__ import annotations
import sys

from _lib.paths import project_dir
from _lib.io import read_hook_input
from _lib.logging import now_str, append_log


def categorize(error: str) -> tuple[str, str]:
    error_lc = error.lower()
    if "enoent" in error_lc or "no such file" in error_lc or "not found" in error_lc:
        return "FILESYSTEM", "WARN"
    if "eacces" in error_lc or "permission denied" in error_lc or "eperm" in error_lc:
        return "PERMISSION", "ERROR"
    if "econnrefused" in error_lc or "etimedout" in error_lc or "fetch failed" in error_lc or "network" in error_lc:
        return "NETWORK", "ERROR"
    if "401" in error or "403" in error or "429" in error or "500" in error or "api" in error_lc or "rate limit" in error_lc:
        return "API", "ERROR"
    if "build" in error_lc or "compile" in error_lc or "syntax" in error_lc or "typeerror" in error_lc or "referenceerror" in error_lc:
        return "BUILD", "ERROR"
    if "critical" in error_lc or "fatal" in error_lc or "panic" in error_lc:
        return "OTHER", "CRITICAL"
    return "OTHER", "ERROR"


def main() -> int:
    payload = read_hook_input()
    tool = payload.get("tool_name") or ""
    error = payload.get("error") or payload.get("tool_result") or ""

    if isinstance(error, list):
        error = "\n".join(str(x) for x in error)
    else:
        error = str(error)

    short_error = error.splitlines()[0][:200] if error else ""

    category, severity = categorize(error)

    proj = project_dir()
    log_dir = proj / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    failure_log = log_dir / "failure-log.md"
    with failure_log.open("a", encoding="utf-8") as f:
        f.write(f"- `{now_str()}` | {severity} | {category} | {tool} | {short_error}\n")

    if severity in ("ERROR", "CRITICAL"):
        append_log("incident-log", f"FAILURE | {severity} | {category} | {tool} | {short_error}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
