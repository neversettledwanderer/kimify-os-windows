"""Stdin/stdout helpers for Kimify hooks."""
from __future__ import annotations
import json
import sys


def read_hook_input() -> dict:
    """Read JSON event payload from stdin."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def write_hook_output(data: dict) -> None:
    """Write structured JSON response to stdout."""
    sys.stdout.write(json.dumps(data))
