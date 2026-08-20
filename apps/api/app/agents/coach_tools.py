"""Tool-using coach for Reading/Listening. Marks stay key-based."""

from __future__ import annotations

import re
from typing import Any


def list_misses(misses: list[dict[str, Any]]) -> str:
    if not misses:
        return "No missed items."
    lines = ["Missed items:"]
    for miss in misses:
        lines.append(
            f"- id={miss.get('question_id')} Q{miss.get('number')} type={miss.get('qtype')} "
            f"given={miss.get('given')!r} key={miss.get('canonical')!r} tags={miss.get('skill_tags')}"
        )
    return "\n".join(lines)


def inspect_item(question_id: str, questions: list[dict[str, Any]], misses: list[dict[str, Any]]) -> str:
    question = next((q for q in questions if str(q.get("id")) == str(question_id)), None)
    miss = next((m for m in misses if str(m.get("question_id")) == str(question_id)), None)
    if question is None and miss is None:
        return f"Unknown question_id {question_id}"
    data = {**(question or {}), **(miss or {})}
    return (
        f"Q{data.get('number')} [{data.get('qtype')}]\n"
        f"Stem: {data.get('stem')}\n"
        f"Given: {data.get('given')!r}\n"
        f"Canonical: {data.get('canonical')!r}\n"
        f"Tags: {data.get('skill_tags')}\n"
        f"Word limit: {data.get('word_limit')}"
    )


def quote_context(context: str, query: str, window: int = 220) -> str:
    text = context or ""
    if not text.strip():
        return "No passage or transcript available."
    terms = [part for part in re.findall(r"[A-Za-z0-9']+", query or "") if len(part) > 2]
    lower = text.lower()
    index = -1
    for term in terms:
        index = lower.find(term.lower())
        if index != -1:
            break
    if index == -1:
        snippet = " ".join(text.split())[:window]
        return f"No exact keyword hit. Opening context: {snippet}"
    start = max(0, index - window // 3)
    end = min(len(text), index + window)
    snippet = text[start:end].strip()
    return f"…{snippet}…"


def run_coach_tool(
    action: str,
    *,
    question_id: str = "",
    query: str = "",
    questions: list[dict[str, Any]],
    misses: list[dict[str, Any]],
    context: str,
) -> str:
    if action == "list_misses":
        return list_misses(misses)
    if action == "inspect_item":
        target = question_id or (str(misses[0]["question_id"]) if misses else "")
        return inspect_item(target, questions, misses)
    if action == "quote_context":
        qid = question_id
        miss = next((m for m in misses if str(m.get("question_id")) == str(qid)), None) if qid else None
        blob = " ".join(
            str(part)
            for part in (
                query,
                (miss or {}).get("stem"),
                (miss or {}).get("canonical"),
                (miss or {}).get("given"),
            )
            if part
        )
        return quote_context(context, blob)
    if action == "finish":
        return "Loop complete."
    return f"Unknown action {action}"
