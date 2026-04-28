"""Shared stop-verdict logging logic used by ai-verdict.py and log-stop-verdict.py."""
from __future__ import annotations
import json
from datetime import datetime, timezone

from .paths import project_dir
from .logging import now_str, append_log


def extract_json(raw: str) -> dict:
    """Best-effort JSON extraction from Haiku-ish output."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def write_verdict(verdict: dict) -> None:
    """Log a parsed verdict dict to files."""
    proj = project_dir()
    log_dir = proj / ".agents" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    decision = verdict.get("decision") or "unknown"
    learning = verdict.get("learning")
    task_type = verdict.get("task_type") or "other"
    reason = verdict.get("reason")

    # Write JSONL
    verdict_log = log_dir / "verdicts.jsonl"
    entry = {
        "timestamp": now_str(),
        "decision": decision,
        "learning": learning,
        "task_type": task_type,
        "reason": reason,
    }
    with verdict_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Track blocks
    if decision == "block":
        session_date = datetime.now(timezone.utc).strftime("%m%d-%H")
        block_file = log_dir / f".session-blocks-{session_date}"
        count = 0
        if block_file.exists():
            try:
                count = int(block_file.read_text(encoding="utf-8").strip() or "0")
            except ValueError:
                pass
        count += 1
        block_file.write_text(str(count), encoding="utf-8")

        append_log("incident-log", f"VERDICT | BLOCK | {reason}")

        if count >= 2:
            (log_dir / ".quality-gate-active").touch()
            append_log(
                "incident-log",
                f"VERDICT | WARN | Quality gate activated — {count} blocks this session",
            )

    # Nominate learning
    if learning and str(learning).lower() not in ("null", "none", ""):
        nomination_date = datetime.now(timezone.utc).strftime("%m%d%y")
        nominations = proj / ".agents" / "knowledge-nominations.md"
        with nominations.open("a", encoding="utf-8") as f:
            f.write(
                f"- [{nomination_date}] stop-hook: {learning} | Evidence: session verdict ({task_type})\n"
            )
