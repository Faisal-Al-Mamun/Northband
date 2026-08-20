from __future__ import annotations

import re
from typing import Any

WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]|[^.!?]+$")
FILLERS = {
    "um",
    "uh",
    "er",
    "erm",
    "like",
    "you know",
    "i mean",
    "kind of",
    "sort of",
    "basically",
}
LINKERS = (
    "however",
    "therefore",
    "although",
    "furthermore",
    "moreover",
    "whereas",
    "consequently",
    "in addition",
    "on the other hand",
    "for example",
    "for instance",
    "firstly",
    "secondly",
    "in conclusion",
    "overall",
    "in contrast",
    "as a result",
    "nevertheless",
)
OVERVIEW_MARKERS = (
    "overall",
    "in general",
    "it is clear",
    "the most",
    "the least",
    "increased",
    "decreased",
    "remained",
    "the highest",
    "the lowest",
)


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def sentence_count(text: str) -> int:
    parts = [part.strip() for part in SENTENCE_RE.findall(text or "") if part.strip()]
    return max(1, len(parts)) if (text or "").strip() else 0


def paragraph_count(text: str) -> int:
    parts = [part for part in re.split(r"\n\s*\n", text or "") if part.strip()]
    return len(parts) or (1 if (text or "").strip() else 0)


def linker_hits(text: str) -> list[str]:
    lowered = (text or "").lower()
    found = [item for item in LINKERS if item in lowered]
    return found


def filler_count(text: str) -> int:
    lowered = f" {(text or "").lower()} "
    total = 0
    for filler in FILLERS:
        total += lowered.count(f" {filler} ")
    return total


def overview_present(text: str, *, module: str = "academic", prompt: str = "") -> bool:
    lower = (text or "").lower()
    # GT Task 1 is a letter — look for purpose / tone markers instead of chart overview.
    if module == "general" or "in your letter" in (prompt or "").lower():
        return any(
            marker in lower
            for marker in ("i am writing", "i'm writing", "dear ", "yours ", "regarding")
        )
    markers = list(OVERVIEW_MARKERS) + [
        "the chart shows",
        "the graph shows",
        "the table shows",
        "the map shows",
        "the diagram shows",
    ]
    return any(marker in lower for marker in markers)


def _prompt_bullets(prompt: str) -> list[str]:
    bullets: list[str] = []
    for raw in re.split(r"(?:•|- |\n)", prompt or ""):
        item = raw.strip(" :.")
        if 12 <= len(item) <= 180:
            bullets.append(item)
    if "in your letter" in (prompt or "").lower():
        clauses = re.split(r",| and ", (prompt or "").split("in your letter", 1)[-1], flags=re.I)
        for clause in clauses:
            cleaned = clause.strip(" :.")
            if 8 <= len(cleaned) <= 120:
                bullets.append(cleaned)
    # de-dupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in bullets:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:8]


def bullet_coverage(prompt: str, response: str) -> dict[str, Any]:
    bullets = _prompt_bullets(prompt)
    lowered = (response or "").lower()
    covered = []
    missing = []
    for bullet in bullets:
        tokens = [tok for tok in WORD_RE.findall(bullet.lower()) if len(tok) > 4][:6]
        hit = bool(tokens) and sum(1 for tok in tokens if tok in lowered) >= max(1, len(tokens) // 2)
        (covered if hit else missing).append(bullet)
    return {
        "bullet_count": len(bullets),
        "covered": covered,
        "missing": missing,
        "coverage_ratio": (len(covered) / len(bullets)) if bullets else None,
    }


def analyze_text(*, text: str, skill: str, module: str, task: str, prompt: str) -> dict[str, Any]:
    words = word_count(text)
    sentences = sentence_count(text)
    avg = round(words / sentences, 1) if sentences else 0.0
    linkers = linker_hits(text)
    expected = 150 if task == "task1" else 250 if skill == "writing" else None
    speaking_coverage = bullet_coverage(prompt, text) if skill == "speaking" and task in {"part2", "full"} else None
    payload: dict[str, Any] = {
        "word_count": words,
        "sentence_count": sentences,
        "paragraph_count": paragraph_count(text),
        "avg_sentence_length": avg,
        "linkers_found": linkers,
        "linker_count": len(linkers),
        "expected_min_words": expected,
        "under_length": bool(expected and words < expected),
        "filler_count": filler_count(text) if skill == "speaking" else 0,
        "overview_present": overview_present(text, module=module, prompt=prompt)
        if skill == "writing" and task == "task1"
        else None,
        "task_coverage": bullet_coverage(prompt, text) if skill == "writing" and task == "task1" else speaking_coverage,
        "module": module,
        "task": task,
        "skill": skill,
    }
    return payload
