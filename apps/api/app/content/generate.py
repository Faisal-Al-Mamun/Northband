"""Generate original writing/speaking papers. Never used for Reading/Listening keys."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.prompt_bank import (
    SPEAK_P1_EXAMINER,
    SPEAK_P2_EXAMINER,
    T1_AC_INSTRUCTION,
    T2_INSTRUCTION,
    format_speaking_prompt,
    format_writing_prompt,
)
from app.db.models import PromptItem, User
from app.llm.router import live_llm_configured, llm_router

BANK_SYSTEM = """You write original IELTS-style practice papers for a test-prep studio.
Rules:
- Invent new topics. Do not copy Cambridge, British Council, IDP, or any real exam paper.
- Do not reuse famous stock prompts (community service in high schools, crime/prison, unpaid internships) unless the user request forces a different angle.
- Match official task types: Academic Task 1 (chart/table), Academic/GT Task 2 (essay), GT Task 1 (letter), Speaking Parts 1–3.
- Keep language exam-like, clear, and specific.
- For Academic Task 1 include a small invented data table in `topic` (numbers that add up sensibly) AND a `visual` object.
- Return JSON only.
"""


class GeneratedVisual(BaseModel):
    kind: str = "bar"
    title: str
    xKey: str = "label"
    yLabel: str | None = None
    series: list[dict[str, str]] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class GeneratedWriting(BaseModel):
    title: str
    topic: str
    instruction: str = ""
    bullets: list[str] = Field(default_factory=list)
    bullet_lead: str = ""
    visual: GeneratedVisual | None = None


class GeneratedSpeaking(BaseModel):
    title: str
    part1_topic: str
    part1_questions: list[str] = Field(min_length=3, max_length=6)
    part2_topic: str
    part2_bullets: list[str] = Field(min_length=3, max_length=5)
    part2_explain: str
    part3_questions: list[str] = Field(min_length=3, max_length=6)


def _slug(prefix: str, title: str, user_id: UUID) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "paper"
    tag = hashlib.sha256(f"{user_id}:{title}".encode()).hexdigest()[:8]
    return f"{prefix}-{stem}-{tag}"


def _visual_payload(visual: GeneratedVisual | None) -> dict[str, Any] | None:
    if visual is None or not visual.rows or not visual.series:
        return None
    kind = visual.kind if visual.kind in {"line", "bar", "pie"} else "bar"
    return {
        "id": f"gen-{uuid4().hex[:8]}",
        "kind": kind,
        "title": visual.title[:180],
        "xKey": visual.xKey or "label",
        "yLabel": visual.yLabel,
        "series": visual.series[:4],
        "rows": visual.rows[:8],
    }


async def generate_prompt_item(
    db: AsyncSession,
    *,
    user: User,
    skill: str,
    module: str,
    task: str,
) -> PromptItem | None:
    if skill not in {"writing", "speaking"}:
        return None
    if not live_llm_configured():
        return None
    try:
        if skill == "writing":
            user_msg = (
                f"Create one original IELTS Writing {module} {task} paper. "
                "Avoid topics already common in generic IELTS lists. "
                f"Student first name (do not mention in the paper): {user.display_name}."
            )
            parsed = await llm_router.complete_json(
                agent="bank",
                system=BANK_SYSTEM,
                user=user_msg,
                schema=GeneratedWriting,
            )
            assert isinstance(parsed, GeneratedWriting)
            instruction = parsed.instruction or (T1_AC_INSTRUCTION if task == "task1" and module == "academic" else T2_INSTRUCTION)
            if task == "task1" and module == "general" and not parsed.bullets:
                parsed.bullets = ["describe the situation", "explain why you are writing", "say what you would like to happen"]
            visual = _visual_payload(parsed.visual) if task == "task1" and module == "academic" else None
            item = PromptItem(
                skill="writing",
                module=module,
                task=task,
                slug=_slug(f"gen-w-{module}-{task}", parsed.title, user.id),
                title=parsed.title[:255],
                prompt=format_writing_prompt(
                    topic=parsed.topic,
                    instruction=instruction,
                    bullets=parsed.bullets or None,
                    bullet_lead=parsed.bullet_lead,
                ),
                payload={"visual": visual} if visual else {},
                source="generated",
                review_status="published",
                owner_user_id=user.id,
                meta={"generated": True},
            )
        else:
            user_msg = (
                "Create one original IELTS Speaking set (Part 1 interview, Part 2 cue card, Part 3 discussion). "
                "Part 1 should be everyday; Part 2 a personal long turn; Part 3 abstract. "
                f"Student first name (do not mention in the paper): {user.display_name}."
            )
            parsed = await llm_router.complete_json(
                agent="bank",
                system=BANK_SYSTEM,
                user=user_msg,
                schema=GeneratedSpeaking,
            )
            assert isinstance(parsed, GeneratedSpeaking)
            pack = {
                "id": "generated",
                "title": parsed.title,
                "part1": {
                    "topic": parsed.part1_topic,
                    "examiner": SPEAK_P1_EXAMINER,
                    "questions": parsed.part1_questions,
                },
                "part2": {
                    "topic": parsed.part2_topic,
                    "examiner": SPEAK_P2_EXAMINER,
                    "bullets": parsed.part2_bullets,
                    "explain": parsed.part2_explain,
                },
                "part3": {
                    "examiner": (
                        f"We've been talking about {parsed.part2_topic.rstrip('.')}, "
                        "and I'd like to discuss with you one or two more general questions related to this."
                    ),
                    "questions": parsed.part3_questions,
                },
            }
            pack["id"] = _slug("gen-s", parsed.title, user.id)
            item = PromptItem(
                skill="speaking",
                module="shared",
                task="pack",
                slug=pack["id"],
                title=parsed.title[:255],
                prompt=format_speaking_prompt("full", pack),
                payload={"speaking": pack},
                source="generated",
                review_status="published",
                owner_user_id=user.id,
                meta={"generated": True},
            )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
    except Exception:
        await db.rollback()
        return None
