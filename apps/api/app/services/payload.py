import json
from pathlib import Path
from typing import Any

from app.config import settings


def payload_path(job_id: str) -> Path:
    return settings.upload_path / f"{job_id}.json"


def write_job_payload(job_id: str, data: dict[str, Any]) -> None:
    payload_path(job_id).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def read_job_payload(job_id: str) -> dict[str, Any]:
    path = payload_path(job_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
