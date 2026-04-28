#!/usr/bin/env python3
"""Generate shell aliases for Kimify slash commands.

Usage:
    python .agents/scripts/generate-shell-aliases.py [--shell bash|zsh|powershell|cmd]

Pipe / dot-source / eval the output as appropriate for your shell.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path


def detect_shell() -> str:
    if os.environ.get("PSModulePath"):
        return "powershell"
    if os.environ.get("COMSPEC") and not os.environ.get("SHELL"):
        return "cmd"
    shell = os.environ.get("SHELL", "").lower()
    if "zsh" in shell:
        return "zsh"
    if "bash" in shell:
        return "bash"
    return "bash"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate shell aliases for Kimify commands")
    ap.add_argument(
        "--shell",
        choices=["bash", "zsh", "powershell", "cmd"],
        default=detect_shell(),
        help="Target shell (auto-detected if omitted)",
    )
    args = ap.parse_args()

    proj = os.environ.get("KIMI_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or str(Path.cwd())
    cmd_dir = Path(proj) / ".agents" / "commands"

    if not cmd_dir.exists():
        print(f"# Error: {cmd_dir} not found", file=sys.stderr)
        return 1

    print(f"# Kimify shell aliases — generated from {cmd_dir}")

    for cmd_file in sorted(cmd_dir.glob("*.md")):
        name = cmd_file.stem
        if args.shell in ("bash", "zsh"):
            # Use double-quoted alias body; expand $cmd_file at alias definition time
            print(f"alias 'kimi-{name}'='kimi -p \"$(cat {cmd_file})\"'")
        elif args.shell == "powershell":
            # PowerShell functions handle arguments better than aliases
            print(f"function kimi-{name} {{ kimi -p (Get-Content -Raw {cmd_file}) }}")
        elif args.shell == "cmd":
            # cmd uses doskey for session aliases
            print(f"doskey kimi-{name}=kimi -p \"$({cmd_file})\"")

    return 0


if __name__ == "__main__":
    sys.exit(main())
