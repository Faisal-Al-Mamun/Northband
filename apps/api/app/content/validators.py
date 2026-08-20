"""Validate curated Reading/Listening items before publish."""

from __future__ import annotations

from typing import Any

ALLOWED_QTYPES = {
    "mcq",
    "tfng",
    "ynng",
    "matching",
    "matching_headings",
    "matching_features",
    "matching_information",
    "completion",
    "summary_completion",
    "note_completion",
    "table_completion",
    "flowchart_completion",
    "short_answer",
    "diagram_label",
    "multi_blank",
}

TFNG_VALUES = {"true", "false", "not given", "yes", "no"}


def validate_question(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    qtype = str(item.get("qtype") or "")
    if qtype not in ALLOWED_QTYPES:
        errors.append(f"Unsupported qtype: {qtype}")
    stem = str(item.get("stem") or "").strip()
    if len(stem) < 5:
        errors.append("Stem too short")
    canonical = item.get("canonical")
    multi = item.get("multi_blank") or {}
    if qtype in {"multi_blank", "table_completion"} and multi.get("blanks"):
        for blank in multi["blanks"]:
            if not str(blank.get("canonical") or "").strip():
                errors.append(f"Blank {blank.get('id')} missing canonical")
    elif not str(canonical or "").strip():
        errors.append("Missing canonical answer key")
    if qtype == "mcq":
        choices = (item.get("options") or {}).get("choices") or []
        if len(choices) < 2:
            errors.append("MCQ needs at least 2 choices")
    if qtype in {"tfng", "ynng"}:
        if normalize_enum(canonical) not in TFNG_VALUES:
            errors.append(f"TFNG/YNNG canonical must be enum, got {canonical!r}")
    word_limit = item.get("word_limit")
    if word_limit is not None and int(word_limit) < 1:
        errors.append("word_limit must be >= 1")
    return errors


def normalize_enum(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_content_set(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    skill = payload.get("skill")
    if skill not in {"reading", "listening"}:
        errors.append("skill must be reading or listening")
    module = payload.get("module")
    if module not in {"academic", "general", "shared"}:
        errors.append("module must be academic, general, or shared")
    if not str(payload.get("title") or "").strip():
        errors.append("title required")
    questions = payload.get("questions") or []
    if not questions:
        errors.append("at least one question required")
    for idx, question in enumerate(questions, start=1):
        for err in validate_question(question):
            errors.append(f"Q{idx}: {err}")
    if skill == "listening":
        audio = payload.get("audio") or []
        if not audio:
            errors.append("listening sets require audio assets")
        for asset in audio:
            if not asset.get("uri"):
                errors.append("audio uri required")
            duration = float(asset.get("duration_sec") or 0)
            if duration <= 0:
                errors.append("audio duration_sec must be > 0")
    if skill == "reading" and not (payload.get("passages") or []):
        errors.append("reading sets require passages")
    return errors


def ready_to_publish(payload: dict[str, Any]) -> bool:
    return not validate_content_set(payload)
