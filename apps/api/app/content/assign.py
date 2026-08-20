"""Pick the next unused paper for a user.

Order is shuffled per user so two accounts do not walk the bank in the same
sequence. Reading/Listening never use LLM generation — keys must stay gold.
Writing/Speaking may inject an original generated paper when a live LLM is
configured.
"""

from __future__ import annotations

import hashlib
import random
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.content.prompt_bank import format_speaking_prompt
from app.db.models import Attempt, ContentSet, MockBlueprint, MockSession, PromptItem, User


def slot_key(skill: str, module: str, task: str) -> str:
    return f"{skill}:{module}:{task}"


def shuffle_ids(user_id: str, slot: str, item_ids: list[str]) -> list[str]:
    seed = int(hashlib.sha256(f"{user_id}:{slot}".encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    ordered = list(item_ids)
    rng.shuffle(ordered)
    return ordered


EXAM_MIN_QUESTIONS = 35


def pack_kind(item: ContentSet, question_count: int = 0) -> str:
    meta = item.meta or {}
    kind = str(meta.get("kind") or "").strip().lower()
    if kind in {"exam", "drill"}:
        return kind
    if question_count >= EXAM_MIN_QUESTIONS or int(item.time_limit_sec or 0) >= 1800 and question_count >= 30:
        return "exam"
    return "drill"


def exam_first_ids(user_id: str, slot: str, sets: list[ContentSet]) -> list[str]:
    """Shuffle exam papers first, then drills, so 'next unused' is never a 3-question sit."""
    counts = {str(item.id): len(item.questions or []) for item in sets}
    exam = [item for item in sets if pack_kind(item, counts.get(str(item.id), 0)) == "exam"]
    drill = [item for item in sets if pack_kind(item, counts.get(str(item.id), 0)) != "exam"]
    return [
        *shuffle_ids(user_id, f"{slot}:exam", [str(item.id) for item in exam]),
        *shuffle_ids(user_id, f"{slot}:drill", [str(item.id) for item in drill]),
    ]


def first_unused(ordered: list[str], completed: set[str], exclude: set[str] | None = None) -> str | None:
    skip = set(completed)
    if exclude:
        skip |= exclude
    for item_id in ordered:
        if item_id not in skip:
            return item_id
    return None


def should_inject_generated(user_id: str, slot: str, completed_count: int) -> bool:
    if completed_count < 1:
        return False
    n = int(hashlib.sha256(f"{user_id}:{slot}:gen:{completed_count}".encode()).hexdigest()[:8], 16)
    return n % 4 == 0


def speaking_assign_task(task: str) -> str:
    if task in {"part1", "part2", "part3", "full"}:
        return task
    return "full"


def _prompt_for_task(item: PromptItem, task: str) -> str:
    if item.skill == "speaking":
        pack = (item.payload or {}).get("speaking") or {}
        if pack:
            return format_speaking_prompt(speaking_assign_task(task), pack)
    return item.prompt


async def _prompt_pool(db: AsyncSession, *, skill: str, module: str, user_id: UUID) -> list[PromptItem]:
    query = select(PromptItem).where(
        PromptItem.skill == skill,
        PromptItem.review_status == "published",
        or_(PromptItem.owner_user_id.is_(None), PromptItem.owner_user_id == user_id),
    )
    if skill == "speaking":
        query = query.where(PromptItem.task == "pack")
    else:
        query = query.where(PromptItem.module == module)
    rows = (await db.scalars(query.order_by(PromptItem.slug))).all()
    return list(rows)


async def _completed_prompt_ids(
    db: AsyncSession,
    *,
    user_id: UUID,
    skill: str,
    module: str,
    task: str,
    items: list[PromptItem],
) -> set[str]:
    query = select(Attempt).where(
        Attempt.user_id == user_id,
        Attempt.skill == skill,
        Attempt.parent_attempt_id.is_(None),
        Attempt.overall_band.is_not(None),
    )
    if skill != "speaking":
        query = query.where(Attempt.module == module, Attempt.task == task)
    else:
        query = query.where(Attempt.task == task)
    attempts = (await db.scalars(query)).all()
    by_id = {str(item.id): item for item in items}
    done: set[str] = set()
    for attempt in attempts:
        ref = str(attempt.bank_item_id) if attempt.bank_item_id else ""
        if ref and ref in by_id:
            done.add(ref)
            continue
        text = (attempt.prompt or "").strip()
        if not text:
            continue
        for item in items:
            if text == _prompt_for_task(item, task).strip() or text == (item.prompt or "").strip():
                done.add(str(item.id))
                break
    return done


async def next_prompt(
    db: AsyncSession,
    user: User,
    *,
    skill: str,
    module: str,
    task: str,
    exclude_id: str | None = None,
    allow_generate: bool = True,
) -> dict:
    from app.content.generate import generate_prompt_item, live_llm_configured

    if skill == "speaking":
        module = "shared"
        assign_task = speaking_assign_task(task)
        pool_task = "pack"
    else:
        assign_task = task
        pool_task = task

    items = await _prompt_pool(db, skill=skill, module=module if skill != "speaking" else "shared", user_id=user.id)
    if skill == "writing":
        items = [item for item in items if item.task == pool_task]
    if not items:
        return {
            "id": None,
            "skill": skill,
            "module": module if skill != "speaking" else user.preferred_module,
            "task": assign_task,
            "slug": "",
            "title": "",
            "prompt": "",
            "source": "none",
            "generated": False,
            "recycled": False,
            "remaining": 0,
            "completed": 0,
            "total": 0,
            "visual": None,
            "speaking": None,
        }

    slot = slot_key(skill, module if skill != "speaking" else "shared", assign_task)
    ordered = shuffle_ids(str(user.id), slot, [str(item.id) for item in items])
    completed = await _completed_prompt_ids(
        db, user_id=user.id, skill=skill, module=module if skill != "speaking" else "shared", task=assign_task, items=items
    )
    exclude = {exclude_id} if exclude_id else set()
    unused_id = first_unused(ordered, completed, exclude)
    recycled = False
    generated = False
    chosen: PromptItem | None = None

    if (
        allow_generate
        and live_llm_configured()
        and should_inject_generated(str(user.id), slot, len(completed))
    ):
        created = await generate_prompt_item(
            db,
            user=user,
            skill=skill,
            module="academic" if skill == "speaking" else module,
            task=assign_task if skill == "writing" else "pack",
        )
        if created:
            chosen = created
            generated = True

    if chosen is None and unused_id:
        chosen = next((item for item in items if str(item.id) == unused_id), None)

    if chosen is None:
        recycled = True
        cycle = [item_id for item_id in ordered if item_id not in exclude] or ordered
        pick = cycle[len(completed) % len(cycle)]
        chosen = next(item for item in items if str(item.id) == pick)
        if allow_generate and live_llm_configured():
            created = await generate_prompt_item(
                db,
                user=user,
                skill=skill,
                module="academic" if skill == "speaking" else module,
                task=assign_task if skill == "writing" else "pack",
            )
            if created:
                chosen = created
                generated = True
                recycled = False

    remaining = max(0, len(items) - len(completed))
    if unused_id is None and not generated:
        remaining = 0
    if skill == "writing" and chosen.task != pool_task:
        fallback = next((item for item in items if item.task == pool_task), None)
        if fallback is not None:
            chosen = fallback
    payload = chosen.payload or {}
    return {
        "id": str(chosen.id),
        "skill": skill,
        "module": module if skill != "speaking" else user.preferred_module,
        "task": assign_task,
        "slug": chosen.slug,
        "title": chosen.title,
        "prompt": _prompt_for_task(chosen, assign_task),
        "source": chosen.source,
        "generated": generated or chosen.source == "generated",
        "recycled": recycled,
        "remaining": remaining,
        "completed": len(completed),
        "total": len(items),
        "visual": payload.get("visual"),
        "speaking": payload.get("speaking"),
    }


async def next_content_set(
    db: AsyncSession,
    user: User,
    *,
    skill: str,
    module: str | None,
    exclude_id: str | None = None,
) -> dict:
    query = (
        select(ContentSet)
        .options(selectinload(ContentSet.questions))
        .where(ContentSet.skill == skill, ContentSet.review_status == "published")
        .order_by(ContentSet.title)
    )
    if skill == "listening" or module in {None, "shared"}:
        if module and module not in {"shared"}:
            query = query.where(ContentSet.module.in_(["shared", module]))
    elif module:
        query = query.where(ContentSet.module == module)
    sets = list((await db.scalars(query)).all())
    if not sets:
        return {
            "id": None,
            "title": "",
            "remaining": 0,
            "completed": 0,
            "total": 0,
            "recycled": False,
            "completed_ids": [],
        }

    slot = slot_key(skill, module or "shared", "set")
    ordered = exam_first_ids(str(user.id), slot, sets) or shuffle_ids(
        str(user.id), slot, [str(item.id) for item in sets]
    )
    attempts = (
        await db.scalars(
            select(Attempt).where(
                Attempt.user_id == user.id,
                Attempt.skill == skill,
                Attempt.parent_attempt_id.is_(None),
            )
        )
    ).all()
    by_title = {item.title: str(item.id) for item in sets}
    completed: set[str] = set()
    for attempt in attempts:
        if attempt.bank_item_id:
            completed.add(str(attempt.bank_item_id))
        elif attempt.prompt and attempt.prompt in by_title:
            completed.add(by_title[attempt.prompt])
    exclude = {exclude_id} if exclude_id else set()
    unused = first_unused(ordered, completed, exclude)
    recycled = unused is None
    chosen_id = unused or next((item_id for item_id in ordered if item_id not in exclude), ordered[0])
    chosen = next(item for item in sets if str(item.id) == chosen_id)
    remaining = max(0, len(sets) - len(completed)) if unused else 0
    return {
        "id": str(chosen.id),
        "title": chosen.title,
        "remaining": remaining,
        "completed": len(completed),
        "total": len(sets),
        "recycled": recycled,
        "completed_ids": sorted(completed),
    }


async def next_mock_blueprint(db: AsyncSession, user: User, *, module: str) -> MockBlueprint | None:
    rows = list(
        (
            await db.scalars(
                select(MockBlueprint)
                .where(MockBlueprint.module == module, MockBlueprint.review_status == "published")
                .order_by(MockBlueprint.title)
            )
        ).all()
    )
    if not rows:
        return None
    done_sessions = (
        await db.scalars(
            select(MockSession).where(
                MockSession.user_id == user.id,
                MockSession.module == module,
                MockSession.status == "completed",
            )
        )
    ).all()
    completed = {str(row.blueprint_id) for row in done_sessions if row.blueprint_id}
    ordered = shuffle_ids(str(user.id), slot_key("mock", module, "full"), [str(item.id) for item in rows])
    pick = first_unused(ordered, completed) or ordered[0]
    return next(item for item in rows if str(item.id) == pick)
