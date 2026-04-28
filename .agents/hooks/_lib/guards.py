"""Content-validation guards used by completeness-gate and guard-bash."""
from __future__ import annotations
import re
from pathlib import Path


INCOMPLETE_RE = re.compile(
    r"\bTBD\b|\bTODO\b|\bFIXME\b|\[PLACEHOLDER\]|\[INSERT ",
    re.IGNORECASE,
)

DEFERRED_RE = re.compile(
    r"assess whether|decide later|need to determine|open question|to be decided|deferred decision",
    re.IGNORECASE,
)

SECRET_RE = re.compile(
    r"(sk[-_]?(live|test|ant|proj)[-_][A-Za-z0-9]{20,}|"
    r"ghp_[A-Za-z0-9]{36}|"
    r"ghs_[A-Za-z0-9]{36}|"
    r"eyJhbGci[A-Za-z0-9+/=]{50,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"xox[bpsar]-[A-Za-z0-9-]{20,})",
    re.IGNORECASE,
)


def has_tbd_or_todo(text: str) -> bool:
    return bool(INCOMPLETE_RE.search(text))


def has_deferred_decision(text: str) -> bool:
    return bool(DEFERRED_RE.search(text))


def missing_provenance(text: str) -> int:
    """Return count of entries missing [Source: ...] provenance."""
    entries = re.findall(r"^\s*-\s+\*\*", text, re.MULTILINE)
    sources = re.findall(r"\[Source:", text)
    return max(0, len(entries) - len(sources))


def line_count_exceeds(path: Path, limit: int) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f) > limit
    except OSError:
        return False


def contains_secret(text: str) -> bool:
    return bool(SECRET_RE.search(text))
