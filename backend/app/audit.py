"""Append-only audit log: every dashboard action is recorded here."""
import json
import time
from pathlib import Path
from threading import Lock

from app.config import get_settings

_lock = Lock()


def record(user: str, action: str, params: dict, status: str, detail: str = "") -> None:
    settings = get_settings()
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "user": user,
        "action": action,
        "params": params,
        "status": status,
        "detail": detail,
    }
    line = json.dumps(entry, default=str)
    with _lock:
        path = Path(settings.audit_log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def read_recent(limit: int = 200) -> list[dict]:
    settings = get_settings()
    path = Path(settings.audit_log_file)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
