"""Deterministic IELTS Reading/Listening answer grading — no LLM."""

from __future__ import annotations

import re
from typing import Any


def normalize_answer(value: Any, *, strip_articles: bool = True) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"\ba\.?\s*m\.?\b", "am", text)
    text = re.sub(r"\bp\.?\s*m\.?\b", "pm", text)
    text = re.sub(r"[^\w\s'\-/]", " ", text)
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()
    if strip_articles:
        text = re.sub(r"^(a|an|the)\s+", "", text)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _letter_aliases(qtype: str, canonical: str) -> list[str]:
    """Map A/B/C radio letters to TFNG / YNNG keys (computer-delivered UI)."""
    key = normalize_answer(canonical, strip_articles=False)
    if qtype == "tfng":
        if key == "true":
            return ["A", "T", "TRUE"]
        if key == "false":
            return ["B", "F", "FALSE"]
        if key == "not given":
            return ["C", "NG", "NOT GIVEN"]
    if qtype == "ynng":
        if key == "yes":
            return ["A", "Y", "YES"]
        if key == "no":
            return ["B", "N", "NO"]
        if key == "not given":
            return ["C", "NG", "NOT GIVEN"]
    return []


def _matches(candidate: str, canonical: str, variants: list[str], norms: dict[str, Any]) -> bool:
    strip_articles = bool(norms.get("strip_articles", True))
    left = normalize_answer(candidate, strip_articles=strip_articles)
    pool = [canonical, *variants]
    return left in {normalize_answer(item, strip_articles=strip_articles) for item in pool if item is not None}


def grade_item(
    *,
    qtype: str,
    student_answer: Any,
    canonical: str,
    variants: list[str] | None = None,
    normalization: dict[str, Any] | None = None,
    multi_blank: dict[str, Any] | None = None,
    word_limit: int | None = None,
    marks: int = 1,
) -> dict[str, Any]:
    variants = variants or []
    norms = normalization or {}
    multi = multi_blank or {}

    if qtype in {"multi_blank", "table_completion"} and multi.get("blanks"):
        blanks = multi["blanks"]
        answers = student_answer if isinstance(student_answer, dict) else {}
        earned = 0
        details = []
        for blank in blanks:
            key = str(blank.get("id") or blank.get("key") or "")
            got = answers.get(key, "")
            ok = _matches(got, blank.get("canonical", ""), blank.get("variants") or [], norms)
            if ok:
                earned += int(blank.get("marks") or 1)
            details.append({"blank": key, "correct": ok, "given": got})
        total = sum(int(b.get("marks") or 1) for b in blanks) or marks
        return {
            "correct": earned == total,
            "earned_marks": earned,
            "max_marks": total,
            "details": details,
        }

    if qtype.startswith("matching") and isinstance(student_answer, dict) and multi.get("pairs"):
        pairs = multi["pairs"]
        earned = 0
        details = []
        for pair in pairs:
            key = str(pair.get("id") or pair.get("left") or "")
            got = student_answer.get(key, "")
            ok = _matches(got, pair.get("canonical", ""), pair.get("variants") or [], norms)
            if ok:
                earned += int(pair.get("marks") or 1)
            details.append({"pair": key, "correct": ok, "given": got})
        total = sum(int(p.get("marks") or 1) for p in pairs) or marks
        return {
            "correct": earned == total,
            "earned_marks": earned,
            "max_marks": total,
            "details": details,
        }

    if word_limit and isinstance(student_answer, str):
        words = [w for w in student_answer.strip().split() if w]
        if len(words) > word_limit:
            return {
                "correct": False,
                "earned_marks": 0,
                "max_marks": marks,
                "details": {"reason": "word_limit", "limit": word_limit},
            }

    extra = _letter_aliases(qtype, canonical)
    ok = _matches(student_answer, canonical, [*variants, *extra], norms)
    return {
        "correct": ok,
        "earned_marks": marks if ok else 0,
        "max_marks": marks,
        "details": {},
    }


def grade_attempt(
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
) -> dict[str, Any]:
    """questions: list of dicts with id, qtype, marks, word_limit, answer_key fields."""
    per_item: list[dict[str, Any]] = []
    earned = 0
    maximum = 0
    by_type: dict[str, dict[str, int]] = {}

    for question in questions:
        qid = str(question["id"])
        key = question.get("answer_key") or {}
        result = grade_item(
            qtype=question.get("qtype", "short_answer"),
            student_answer=answers.get(qid, answers.get(str(question.get("number")), "")),
            canonical=str(key.get("canonical", "")),
            variants=list(key.get("acceptable_variants") or []),
            normalization=dict(key.get("normalization") or {}),
            multi_blank=dict(key.get("multi_blank") or {}),
            word_limit=question.get("word_limit"),
            marks=int(question.get("marks") or 1),
        )
        earned += result["earned_marks"]
        maximum += result["max_marks"]
        qtype = question.get("qtype", "unknown")
        bucket = by_type.setdefault(qtype, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if result["correct"]:
            bucket["correct"] += 1
        per_item.append(
            {
                "question_id": qid,
                "number": question.get("number"),
                "qtype": qtype,
                "skill_tags": question.get("skill_tags") or [],
                "stem": question.get("stem"),
                "given": answers.get(qid, answers.get(str(question.get("number")), "")),
                "canonical": key.get("canonical"),
                "key_version": key.get("key_version", 1),
                **result,
            }
        )

    misses = [item for item in per_item if not item["correct"]]
    return {
        "earned_marks": earned,
        "max_marks": maximum or 40,
        "raw_correct": sum(1 for item in per_item if item["correct"]),
        "question_count": len(per_item),
        "by_type": by_type,
        "per_item": per_item,
        "misses": misses,
    }
