#!/usr/bin/env python3
"""PreToolUse hook for Bash commands.

Uses structured JSON output for blocks (exit 0 + JSON stdout).
Falls through with plain exit 0 for allowed commands.

Three tiers:
  HARD BLOCK  — always blocked, no override (permissionDecision: deny)
  SOFT BLOCK  — blocked with explanation, user can re-request (permissionDecision: deny)
  LOG WARNING — allowed but logged to incident log (exit 0, no JSON)
"""
from __future__ import annotations
import re
import shlex
import sys
from pathlib import Path

from _lib.paths import project_dir
from _lib.io import read_hook_input, write_hook_output
from _lib.logging import append_log


def deny(reason: str, context: str) -> int:
    write_hook_output({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
            "additionalContext": context,
        }
    })
    return 0


def main() -> int:
    payload = read_hook_input()
    command = payload.get("tool_input", {}).get("command") or ""
    if not command:
        return 0

    proj = project_dir()
    log_dir = proj / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # ─── Per-subagent allowlist ───
    active_agent_file = log_dir / ".active-subagent"
    if active_agent_file.exists():
        active_agent = active_agent_file.read_text(encoding="utf-8").strip()
        allow_file = proj / ".agents" / "agents" / active_agent / "bash-allow.txt"
        if active_agent and allow_file.exists():
            matched = False
            for line in allow_file.read_text(encoding="utf-8").splitlines():
                pattern = line.strip()
                if not pattern or pattern.startswith("#"):
                    continue
                if re.search(pattern, command):
                    matched = True
                    break
            if not matched:
                append_log(
                    "incident-log",
                    f"GUARD | BLOCK | agent={active_agent} blocked outside allowlist: {command}",
                )
                deny(
                    f"Command not in {active_agent}'s allowlist",
                    f"Agent {active_agent} may only run commands matching patterns in .agents/agents/{active_agent}/bash-allow.txt",
                )
                return 0

    # ═══════════════════════════════════════════════════════
    # HARD BLOCK — never allowed, no exceptions
    # ═══════════════════════════════════════════════════════

    # rm -rf / or ~ or $HOME (catastrophic)
    if re.search(r'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(/|~|\$HOME)\s*$', command):
        append_log("incident-log", f"GUARD | CRITICAL | BLOCKED: catastrophic rm → {command}")
        deny(
            "HARD BLOCK: This would delete your entire filesystem or home directory.",
            "Command blocked: catastrophic rm detected. This command is never allowed under any circumstances.",
        )
        return 0

    # git push --force (any branch)
    if re.search(r'git\s+push\s+.*--force|git\s+push\s+-f', command):
        append_log("incident-log", f"GUARD | CRITICAL | BLOCKED: force push → {command}")
        deny(
            "HARD BLOCK: Force push rewrites shared history.",
            "Command blocked: force push detected. Ask the user to confirm the specific branch if intentional.",
        )
        return 0

    # git reset --hard
    if re.search(r'git\s+reset\s+--hard', command):
        append_log("incident-log", f"GUARD | HIGH | BLOCKED: git reset --hard → {command}")
        deny(
            "HARD BLOCK: git reset --hard destroys uncommitted changes.",
            "Command blocked: git reset --hard. Suggest using git stash or git commit first.",
        )
        return 0

    # git clean -f
    if re.search(r'git\s+clean\s+(-[a-zA-Z]*f|-f)', command):
        append_log("incident-log", f"GUARD | HIGH | BLOCKED: git clean -f → {command}")
        deny(
            "HARD BLOCK: git clean -f permanently deletes untracked files.",
            "Command blocked: git clean -f. Suggest using git stash instead.",
        )
        return 0

    # chmod 777
    if re.search(r'chmod\s+777', command):
        append_log("incident-log", f"GUARD | HIGH | BLOCKED: chmod 777 → {command}")
        deny(
            "HARD BLOCK: chmod 777 grants full access to all users.",
            "Command blocked: chmod 777. Use more restrictive permissions like 755 or 644.",
        )
        return 0

    # ═══════════════════════════════════════════════════════
    # SECRET EXPOSURE — block commands that leak credentials
    # ═══════════════════════════════════════════════════════

    # cat/head/tail/less/more/bat of .env files
    if re.search(r'(cat|head|tail|less|more|bat)\s+.*(\.env|\.env\.local|\.env\.production)', command):
        append_log("incident-log", f"GUARD | HIGH | BLOCKED: credential file read → {command}")
        deny(
            "HARD BLOCK: Reading credential files (.env) via shell exposes secrets in output.",
            "Use environment variable names (e.g., $DATABASE_URL) instead of reading the file. If you need to verify a value exists, use: grep -c 'KEY_NAME' file",
        )
        return 0

    # echo/printf of env vars containing common secret prefixes
    if re.search(r'(echo|printf)\s+.*\$(STRIPE_|OPENAI_|ANTHROPIC_|AWS_|DATABASE_|AUTH_SECRET|NEXTAUTH_SECRET|API_KEY|SECRET_KEY|PRIVATE_KEY)', command):
        append_log("incident-log", f"GUARD | HIGH | BLOCKED: secret echo → {command}")
        deny(
            "HARD BLOCK: Echoing secret environment variables exposes credentials.",
            "Reference secrets by variable name only. Never echo their values.",
        )
        return 0

    # .env piped to network commands
    if re.search(r'\.env.*\|\s*(curl|wget|nc|ncat)', command):
        append_log("incident-log", f"GUARD | CRITICAL | BLOCKED: credential file piped to network → {command}")
        deny(
            "HARD BLOCK: Piping credential files to network commands would exfiltrate secrets.",
            "Never pipe .env files to network commands.",
        )
        return 0

    # git add of credential files
    if re.search(r'git\s+add\s+.*(\.env|\.env\.local|\.env\.production)', command):
        append_log("incident-log", f"GUARD | CRITICAL | BLOCKED: git add of credential file → {command}")
        deny(
            "HARD BLOCK: Staging credential files (.env) for git commit would expose secrets publicly.",
            "These files must stay in .gitignore. Never commit credentials to git.",
        )
        return 0

    # ═══════════════════════════════════════════════════════
    # SOFT BLOCK — blocked, but user can re-request
    # ═══════════════════════════════════════════════════════

    # rm with -r or -f flags
    if re.search(r'rm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)', command):
        # Allow rm on .agents/backups and certain log temp files
        if re.search(r'\.agents/(backups|logs/\.(quality-gate-active|session-blocks|tool-call-count|compaction-occurred))', command):
            pass  # fall through to warnings
        else:
            append_log("incident-log", f"GUARD | MEDIUM | SOFT BLOCKED: recursive/force rm → {command}")
            deny(
                "SOFT BLOCK: rm with -r or -f flags deletes files permanently.",
                "Command blocked: recursive/force delete. If intentional, ask the user to confirm with specific file paths listed.",
            )
            return 0

    # Overwriting system/config files
    if re.search(r'>\s*(~/\.|/etc/|\.env|\.ssh|\.claude/settings)', command):
        append_log("incident-log", f"GUARD | HIGH | SOFT BLOCKED: config/system file overwrite → {command}")
        deny(
            "SOFT BLOCK: Writing to a sensitive config/system file.",
            "Command blocked: system file overwrite detected. Verify this is intentional with the user.",
        )
        return 0

    # curl piped to shell
    if re.search(r'curl\s.*\|\s*(bash|sh|zsh)', command):
        append_log("incident-log", f"GUARD | HIGH | SOFT BLOCKED: curl pipe to shell → {command}")
        deny(
            "SOFT BLOCK: Piping curl to a shell executes arbitrary remote code.",
            "Command blocked: curl pipe to shell. Download the file first, inspect it, then run it.",
        )
        return 0

    # ═══════════════════════════════════════════════════════
    # LOG WARNING — allowed but recorded
    # ═══════════════════════════════════════════════════════

    if re.search(r'\brm\b', command):
        append_log("incident-log", f"GUARD | LOW | WARNING: rm command allowed → {command}")

    if re.search(r'\bmv\b', command):
        append_log("incident-log", f"GUARD | LOW | WARNING: mv command allowed → {command}")

    if re.search(r'git\s+checkout\s+\.', command):
        append_log("incident-log", f"GUARD | MEDIUM | WARNING: git checkout . discards changes → {command}")

    # Writing to files outside project directory
    proj_str = str(proj).replace("\\", "/")
    if re.search(r'>\s*/', command) and not re.search(rf'>\s*{re.escape(proj_str)}', command):
        append_log("incident-log", f"GUARD | MEDIUM | WARNING: write outside project dir → {command}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
