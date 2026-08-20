"""Process-local cache for writing/speaking + grammar analyses.

Identical (skill, module, task, prompt, text) reuses specialist JSON so a re-sit
or retry does not pay for the same LLM calls. Coach agents still run — history
and memory change even when the essay does not.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

_TTL_SECONDS = 24 * 3600
_store: dict[str, tuple[float, dict[str, Any]]] = {}


def make_key(skill: str, module: str, task: str, prompt: str, text: str) -> str:
    raw = json.dumps(
        {
            "skill": skill,
            "module": module,
            "task": task,
            "prompt": prompt or "",
            "text": text or "",
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(key: str) -> dict[str, Any] | None:
    row = _store.get(key)
    if row is None:
        return None
    expires, payload = row
    if expires < time.time():
        _store.pop(key, None)
        return None
    return dict(payload)


def put(key: str, payload: dict[str, Any]) -> None:
    _store[key] = (time.time() + _TTL_SECONDS, dict(payload))


def clear() -> None:
    _store.clear()
