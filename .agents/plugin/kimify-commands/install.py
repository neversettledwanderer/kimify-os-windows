#!/usr/bin/env python3
"""Install the Kimify Commands plugin into Kimi CLI.

Copies this directory to ~/.kimi/plugins/kimify-commands/
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path


def main() -> int:
    plugin_dir = Path(__file__).resolve().parent
    home = Path.home()
    dest_dir = home / ".kimi" / "plugins" / "kimify-commands"

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(plugin_dir, dest_dir)

    print(f"Installed kimify-commands plugin to {dest_dir}")
    print("Run 'kimi plugin list' to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
