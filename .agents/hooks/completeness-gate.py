#!/usr/bin/env python3
"""PreToolUse completeness gate for Write|Edit tools.

Uses structured JSON output: exit 0 + JSON stdout for both allow and deny.

Validates content completeness for critical system files before allowing writes.
Each file path gets path-specific validation rules. Non-critical files pass through.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

from _lib.paths import project_dir, relative_path
from _lib.io import read_hook_input, write_hook_output
from _lib.logging import append_log
from _lib.guards import has_tbd_or_todo, has_deferred_decision, missing_provenance, contains_secret
from _lib.config import validate_toml_text


def block(file: str, reason: str, suggestion: str = "Fix the content, then retry the write.") -> int:
    append_log("incident-log", f"COMPLETENESS | MEDIUM | BLOCKED: {reason} → {file}")
    write_hook_output({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"COMPLETENESS GATE: {reason} | File: {file}",
            "additionalContext": f"Write blocked by completeness gate. Issue: {reason}. Suggestion: {suggestion}",
        }
    })
    return 0


def block_high(file: str, reason: str, suggestion: str = "Fix the content, then retry the write.") -> int:
    append_log("incident-log", f"COMPLETENESS | HIGH | BLOCKED: {reason} → {file}")
    write_hook_output({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"COMPLETENESS GATE [HIGH]: {reason} | File: {file}",
            "additionalContext": f"Write blocked by completeness gate (HIGH severity). Issue: {reason}. Suggestion: {suggestion}",
        }
    })
    return 0


def check_incomplete_markers(content: str, relative_path: str) -> int:
    if has_tbd_or_todo(content):
        block(
            relative_path,
            "Contains TBD/TODO/FIXME/PLACEHOLDER markers. Content must be investigation-complete.",
            "Replace all placeholder markers with actual values. Search for TBD, TODO, FIXME, [PLACEHOLDER], and [INSERT in your content.",
        )
        return 1
    if has_deferred_decision(content):
        block(
            relative_path,
            "Contains deferred decisions or open questions. Resolve all decisions before writing.",
            "Remove phrases like 'assess whether', 'decide later', 'need to determine', 'open question'. Make definitive statements instead.",
        )
        return 1
    return 0


def main() -> int:
    payload = read_hook_input()
    file_path = payload.get("tool_input", {}).get("file_path") or ""
    tool = payload.get("tool_name") or ""

    if not file_path:
        return 0

    relative = relative_path(file_path)

    # Get content based on tool type
    if tool == "Write":
        content = payload.get("tool_input", {}).get("content") or ""
    elif tool in ("Edit", "MultiEdit"):
        content = payload.get("tool_input", {}).get("new_string") or ""
    else:
        return 0

    if not content:
        return 0

    # ═══════════════════════════════════════════════════════
    # SECRET EXPOSURE CHECK (runs on ALL files)
    # ═══════════════════════════════════════════════════════
    is_env_file = relative.startswith(".env") or ".agents/backups/" in relative
    if not is_env_file and contains_secret(content):
        block_high(
            relative,
            "SECURITY: Content contains what appears to be an API key, token, or secret. Credentials must NEVER be written to non-.env files.",
            "Remove the credential from the content. Reference the secret by its variable name (e.g., STRIPE_SECRET_KEY) instead of its value. Secrets belong in .env files only.",
        )
        return 0

    # ═══════════════════════════════════════════════════════
    # PATH-SPECIFIC GATES
    # ═══════════════════════════════════════════════════════
    if relative == ".agents/knowledge-base.md":
        if check_incomplete_markers(content, relative):
            return 0

        if tool == "Write":
            missing = missing_provenance(content)
            if missing > 0:
                block_high(
                    relative,
                    f"Knowledge-base has {missing} entries missing [Source: ...] provenance. Every entry MUST cite its source.",
                    "Add [Source: user override MMDDYY] or [Source: empirical — description] or [Source: agent inference — description] to every entry line (- **...**:).",
                )
                return 0

            line_count = len(content.splitlines())
            if line_count > 200:
                block_high(
                    relative,
                    f"Knowledge-base is {line_count} lines (max 200). Curate: remove stale entries before adding new ones.",
                    "Read the current knowledge-base, identify entries older than 90 days or superseded by newer entries, remove them, then retry.",
                )
                return 0

    elif relative == ".agents/memory.md":
        if tool == "Write":
            line_count = len(content.splitlines())
            if line_count > 100:
                block(
                    relative,
                    f"memory.md is {line_count} lines (max 100). Prune stale items before writing.",
                    "Remove completed items from Now, resolved items from Open Threads, and outdated entries from Recent Decisions.",
                )
                return 0

    elif relative == "kimi-config.toml":
        if tool == "Write":
            if not validate_toml_text(content):
                block_high(
                    relative,
                    "kimi-config.toml would be invalid TOML. Syntax error will break ALL hooks once merged into ~/.local/share/kimi/config.toml.",
                    "Validate TOML syntax: check array-of-tables brackets ([[hooks]]), string quoting, and newline separation between entries. Use Edit instead of Write to make targeted changes.",
                )
                return 0

    elif re.match(r"\.agents/agents/[^/]+/system\.md$", relative):
        if check_incomplete_markers(content, relative):
            return 0

    elif re.match(r"\.agents/agents/[^/]+/agent\.yaml$", relative):
        if check_incomplete_markers(content, relative):
            return 0

    # All other files pass through
    return 0


if __name__ == "__main__":
    sys.exit(main())
