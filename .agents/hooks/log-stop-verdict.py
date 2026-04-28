#!/usr/bin/env python3
"""Stop hook — logs the quality verdict from the AI review.

Can be used standalone (reads JSON from stdin) or imported by ai-verdict.py.
"""
from __future__ import annotations
import sys

from _lib.stop_verdict import extract_json, write_verdict


def main() -> int:
    raw = sys.stdin.read()
    parsed = extract_json(raw)
    write_verdict(parsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
