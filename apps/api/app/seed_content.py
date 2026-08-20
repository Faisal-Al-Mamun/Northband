"""Seed curated Reading/Listening practice sets. Run: python -m app.seed_content

Versioned: bump SEED_BANK_VERSION to refresh published seed packs in place.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.content.listening_bank import (
    CAMPUS_AUDIO,
    CAMPUS_QUESTIONS,
    HOUSING_AUDIO,
    HOUSING_QUESTIONS,
    NUMBERS_AUDIO,
    NUMBERS_QUESTIONS,
)
from app.content.prompt_bank import PROMPT_BANK_VERSION, all_curated
from app.content.reading_bank import AC_P1, AC_P2, AC_P3, AC_P4, AC_P5, AC_P6, GT_S1, GT_S2, GT_S3, GT_S4, GT_S5, GT_S6
from app.db.models import (
    AnswerKey,
    AudioAsset,
    ContentSet,
    MockBlueprint,
    Passage,
    PromptItem,
    Question,
)
from app.db.session import SessionLocal
from app.services.stt import audio_duration_seconds
from app.services.tts import audio_path_for, wav_is_playable

# Bump to force refresh of seeded packs (questions/passages/audio).
SEED_BANK_VERSION = 8


def _audio_seed_items(rows: list[dict]) -> list[dict]:
    items = []
    for row in rows:
        path = audio_path_for(row["stem"], row["transcript"], row["accent"])
        duration = audio_duration_seconds(path) if wav_is_playable(path) else 0.0
        items.append(
            {
                "order": row["order"],
                "section_label": row["section_label"],
                "uri": f"content/audio/{path.name}",
                "duration_sec": duration or 0,
                "accent": row["accent"],
                "transcript": row["transcript"],
            }
        )
    return items


async def _clear_set_children(db, content: ContentSet) -> None:
    qids = (
        await db.scalars(select(Question.id).where(Question.content_set_id == content.id))
    ).all()
    if qids:
        await db.execute(delete(AnswerKey).where(AnswerKey.question_id.in_(qids)))
        await db.execute(delete(Question).where(Question.content_set_id == content.id))
    await db.execute(delete(Passage).where(Passage.content_set_id == content.id))
    await db.execute(delete(AudioAsset).where(AudioAsset.content_set_id == content.id))


async def _ensure_set(
    db,
    *,
    skill: str,
    module: str,
    slug: str,
    title: str,
    time_limit_sec: int,
    passages: list[dict],
    questions: list[dict],
    audio: list[dict] | None = None,
    difficulty: str = "medium",
    kind: str = "exam",
) -> ContentSet:
    existing = await db.scalar(
        select(ContentSet)
        .options(selectinload(ContentSet.questions))
        .where(ContentSet.slug == slug)
    )
    if existing and int(existing.version or 0) >= SEED_BANK_VERSION:
        return existing
    if existing:
        await _clear_set_children(db, existing)
        content = existing
        content.title = title
        content.time_limit_sec = time_limit_sec
        content.difficulty = difficulty
        content.version = SEED_BANK_VERSION
        content.review_status = "published"
        content.meta = {"seed": True, "bank_version": SEED_BANK_VERSION, "kind": kind}
    else:
        content = ContentSet(
            skill=skill,
            module=module,
            slug=slug,
            title=title,
            time_limit_sec=time_limit_sec,
            review_status="published",
            difficulty=difficulty,
            version=SEED_BANK_VERSION,
            meta={"seed": True, "bank_version": SEED_BANK_VERSION, "kind": kind},
        )
        db.add(content)
        await db.flush()

    passage_ids: dict[int, object] = {}
    for item in passages:
        row = Passage(
            content_set_id=content.id,
            order_index=item["order"],
            title=item.get("title", ""),
            body=item["body"],
        )
        db.add(row)
        await db.flush()
        passage_ids[item["order"]] = row.id
    audio_ids: dict[int, object] = {}
    for item in audio or []:
        row = AudioAsset(
            content_set_id=content.id,
            order_index=item["order"],
            section_label=item.get("section_label", f"section{item['order']}"),
            uri=item["uri"],
            duration_sec=item.get("duration_sec", 3),
            accent=item.get("accent", "en-GB"),
            transcript=item.get("transcript", ""),
        )
        db.add(row)
        await db.flush()
        audio_ids[item["order"]] = row.id
    for item in questions:
        q = Question(
            content_set_id=content.id,
            passage_id=passage_ids.get(item.get("passage_order")),
            audio_asset_id=audio_ids.get(item.get("audio_order")),
            order_index=item["number"],
            number=item["number"],
            qtype=item["qtype"],
            stem=item["stem"],
            options=item.get("options") or {},
            skill_tags=item.get("skill_tags") or [],
            marks=item.get("marks", 1),
            word_limit=item.get("word_limit"),
        )
        db.add(q)
        await db.flush()
        db.add(
            AnswerKey(
                question_id=q.id,
                canonical=str(item["canonical"]),
                acceptable_variants=item.get("variants") or [],
                normalization=item.get("normalization") or {"strip_articles": True},
                multi_blank=item.get("multi_blank") or {},
                key_version=1,
            )
        )
    return content



def _matching_info(stem: str, answer: str, choices: list[str], tags: list[str] | None = None) -> dict:
    return {
        "qtype": "matching_information",
        "stem": stem,
        "options": {"choices": choices},
        "canonical": answer,
        "variants": [answer.lower(), answer.upper()],
        "skill_tags": tags or ["matching_information"],
    }


def _summary(stem: str, answer: str, variants: list[str], tags: list[str] | None = None) -> dict:
    return {
        "qtype": "summary_completion",
        "stem": stem,
        "canonical": answer,
        "variants": variants,
        "skill_tags": tags or ["summary_completion"],
        "word_limit": 2,
    }


def _tfng(stem: str, answer: str, tags: list[str] | None = None) -> dict:
    return {
        "qtype": "tfng",
        "stem": stem,
        "options": {"choices": ["True", "False", "Not Given"]},
        "canonical": answer,
        "skill_tags": tags or ["tfng"],
    }


def _ynng(stem: str, answer: str, tags: list[str] | None = None) -> dict:
    return {
        "qtype": "ynng",
        "stem": stem,
        "options": {"choices": ["Yes", "No", "Not Given"]},
        "canonical": answer,
        "skill_tags": tags or ["ynng"],
    }


def _mcq(stem: str, choices: list[str], answer: str, tags: list[str] | None = None) -> dict:
    return {
        "qtype": "mcq",
        "stem": stem,
        "options": {"choices": choices},
        "canonical": answer,
        "variants": [answer.lower()],
        "skill_tags": tags or ["mcq"],
    }


def _short(stem: str, answer: str, variants: list[str], limit: int, tags: list[str] | None = None) -> dict:
    return {
        "qtype": "short_answer",
        "stem": stem,
        "canonical": answer,
        "variants": variants,
        "word_limit": limit,
        "skill_tags": tags or ["short_answer"],
    }


def _comp(stem: str, answer: str, variants: list[str], tags: list[str] | None = None) -> dict:
    return {
        "qtype": "completion",
        "stem": stem,
        "canonical": answer,
        "variants": variants,
        "skill_tags": tags or ["completion"],
    }


def _headings(stem: str, answer: str, choices: list[str], tags: list[str] | None = None) -> dict:
    return {
        "qtype": "matching_headings",
        "stem": stem,
        "options": {"choices": choices},
        "canonical": answer,
        "variants": [answer.lower(), answer.upper()],
        "skill_tags": tags or ["matching_headings"],
    }


def _speak(
    title: str,
    part1_topic: str,
    part1_qs: list[str],
    part2_topic: str,
    part2_bullets: list[str],
    part2_explain: str,
    part3_qs: list[str],
) -> dict:
    return {
        "id": title.lower().replace(" ", "-")[:40],
        "title": title,
        "part1": {
            "topic": part1_topic,
            "examiner": "Now, in this first part, I'd like to ask you some questions about yourself.",
            "questions": part1_qs,
        },
        "part2": {
            "topic": part2_topic,
            "examiner": (
                "Now, I'm going to give you a topic and I'd like you to talk about it for one to two minutes. "
                "Before you talk, you will have one minute to think about what you are going to say. "
                "You can make some notes if you wish. Do you understand?"
            ),
            "bullets": part2_bullets,
            "explain": part2_explain,
        },
        "part3": {
            "examiner": "We've been talking about this topic, and I'd like to discuss one or two more general questions related to this.",
            "questions": part3_qs,
        },
    }


async def seed_content() -> None:
    async with SessionLocal() as db:
        heat_headings = [
            "i Measuring two kinds of urban heat and why they matter for health",
            "ii Why a fashionable single intervention is rarely enough",
            "iii Uneven exposure and who captures the subsidies",
            "iv What early block-level evaluations found",
            "v Co-benefits with energy, flood control and air quality",
            "vi A history of asphalt paving in European capitals",
        ]
        heat_info = ["A", "B", "C", "D", "E"]
        ac_questions = []
        # Passage 1 — Urban heat (Q1–13)
        for i, q in enumerate(
            [
                _headings("Paragraph A", "i", heat_headings),
                _headings("Paragraph B", "ii", heat_headings),
                _headings("Paragraph C", "iii", heat_headings),
                _matching_info("a measured range for night-time cooling on treated blocks", "D", heat_info),
                _matching_info("the risk that cool roofs worsen heat for pedestrians", "B", heat_info),
                _mcq(
                    "According to the writer, successful heat mitigation mainly depends on:",
                    [
                        "A importing the most popular international design",
                        "B matching interventions to local constraints",
                        "C replacing all asphalt within five years",
                        "D measuring only surface temperatures",
                    ],
                    "B",
                    ["mcq", "writer_view"],
                ),
                _comp(
                    "Without targeting, cool-roof subsidies may favour owners of large ______ properties.",
                    "commercial",
                    ["commercial properties"],
                    ["completion"],
                ),
                _short(
                    "What night-time cooling range (in °C) did early evaluations report on treated blocks? (e.g. 0.5-1.5)",
                    "0.5-1.5",
                    ["0.5–1.5", "0.5 to 1.5", "0.5 - 1.5"],
                    3,
                    ["short_answer", "numbers"],
                ),
                _tfng(
                    "Heatwaves increase hospital admissions for respiratory and cardiovascular conditions.",
                    "True",
                    ["tfng"],
                ),
                _tfng(
                    "Street trees can be planted in any street regardless of underground utilities.",
                    "False",
                    ["tfng", "absolute_trap"],
                ),
                _comp(
                    "Heat risk maps frequently show higher exposure in ______ neighbourhoods.",
                    "lower-income",
                    ["lower income", "low-income"],
                    ["completion"],
                ),
                _mcq(
                    "Mandatory cool-roof codes mentioned in the passage apply to:",
                    [
                        "A all residential streets",
                        "B new warehouses",
                        "C historic city centres only",
                        "D rural barns",
                    ],
                    "B",
                    ["mcq"],
                ),
                _short(
                    "Besides older residents, which group is especially affected by heatwaves?",
                    "outdoor workers",
                    ["outdoor worker", "outside workers"],
                    3,
                    ["short_answer"],
                ),
            ],
            start=1,
        ):
            ac_questions.append({**q, "number": i, "passage_order": 1})

        # Passage 2 — Bees (Q9–14)
        for i, q in enumerate(
            [
                _summary("A honey-bee colony normally contains a single ______.", "queen", ["the queen"]),
                _summary("The ______ dance encodes distance and direction relative to the sun.", "waggle", ["waggle dance"]),
                _summary("Young workers typically ______ cells.", "clean", ["clean cells"]),
                _mcq(
                    "Conservation programmes emphasise:",
                    [
                        "A increasing hive counts only",
                        "B habitat corridors and lower chemical load",
                        "C replacing queens annually",
                        "D banning all foraging",
                    ],
                    "B",
                    ["mcq"],
                ),
                _short(
                    "What dance encodes distance and direction of food? (max 3 words)",
                    "waggle dance",
                    ["the waggle dance", "waggle-dance"],
                    3,
                    ["short_answer"],
                ),
                _comp(
                    "Pesticide exposure can impair ______ even when acute mortality is low.",
                    "navigation",
                    ["bee navigation"],
                    ["completion"],
                ),
                _tfng("Middle-aged bees typically nurse larvae.", "True", ["tfng"]),
                _tfng("The waggle dance encodes the colour of flowers.", "False", ["tfng"]),
                _comp("Older bees typically ______.", "forage", ["foraging"], ["completion"]),
                _short(
                    "What is the scientific name of the honey bee?",
                    "Apis mellifera",
                    ["apis mellifera"],
                    3,
                    ["short_answer"],
                ),
                _tfng(
                    "Commercial pollination contracts have grown with monoculture agriculture.",
                    "True",
                    ["tfng"],
                ),
                _mcq(
                    "Critics argue that treating bees mainly as livestock overlooks:",
                    [
                        "A hive numbers",
                        "B wild pollinators",
                        "C the waggle dance",
                        "D seasonal drones",
                    ],
                    "B",
                    ["mcq"],
                ),
                _comp(
                    "Conservation programmes should not focus on ______ alone.",
                    "hive numbers",
                    ["hive counts"],
                    ["completion"],
                ),
            ],
            start=14,
        ):
            ac_questions.append({**q, "number": i, "passage_order": 2})

        # Passage 3 — Open science (Q15–20) Yes/No/NG + matching style
        for i, q in enumerate(
            [
                _ynng(
                    "The writer believes subscription journals can block access for under-resourced scholars.",
                    "Yes",
                    ["ynng", "writer_view"],
                ),
                _ynng(
                    "APCs always make publishing cheaper for early-career researchers.",
                    "No",
                    ["ynng", "absolute_trap"],
                ),
                _ynng(
                    "Every scientific field now uses preprint servers as the main publication route.",
                    "No",
                    ["ynng"],
                ),
                _ynng(
                    "Citation advantages from open mandates are identical in every discipline.",
                    "No",
                    ["ynng"],
                ),
                _ynng(
                    "The writer recommends closing all subscription journals next year.",
                    "Not Given",
                    ["ynng", "ng_trap"],
                ),
                _mcq(
                    "Hybrid journals have been criticised for:",
                    [
                        "A refusing APCs",
                        "B double dipping (subscriptions plus APCs)",
                        "C banning preprints",
                        "D ignoring peer review entirely",
                    ],
                    "B",
                    ["mcq"],
                ),
                _ynng(
                    "The writer claims APCs can exclude early-career researchers without grants.",
                    "Yes",
                    ["ynng"],
                ),
                _comp(
                    "Funders in several countries require deposit of accepted manuscripts in ______.",
                    "repositories",
                    ["a repository", "repositories"],
                    ["completion"],
                ),
                _ynng(
                    "Early evidence shows increased downloads after open-access mandates.",
                    "Yes",
                    ["ynng"],
                ),
                _ynng(
                    "Citation advantages from mandates are the same in every language.",
                    "No",
                    ["ynng"],
                ),
                _comp(
                    "Hybrid journals offer both subscription access and optional ______.",
                    "open access",
                    ["OA", "open-access"],
                    ["completion"],
                ),
                _mcq(
                    "Some disciplines remain cautious about preprint servers because of:",
                    [
                        "A library subscription fees only",
                        "B priority disputes and the absence of peer review prior to posting",
                        "C a ban on APCs",
                        "D satellite heat maps",
                    ],
                    "B",
                    ["mcq"],
                ),
                _short(
                    "What charge shifts publication costs to authors or their funders? (abbreviation accepted)",
                    "APCs",
                    ["APC", "article processing charges", "article processing charge"],
                    4,
                    ["short_answer"],
                ),
                _ynng(
                    "The writer says every funder worldwide now requires repository deposit.",
                    "Not Given",
                    ["ynng", "ng_trap"],
                ),
            ],
            start=27,
        ):
            ac_questions.append({**q, "number": i, "passage_order": 3})

        ar1 = await _ensure_set(
            db,
            skill="reading",
            module="academic",
            slug="reading-ac-exam-pack-v2",
            title="Academic Reading — Heat, bees & open science",
            time_limit_sec=3600,
            difficulty="medium",
            passages=[
                {"order": 1, "title": "Passage 1 — Urban heat islands", "body": AC_P1},
                {"order": 2, "title": "Passage 2 — Honey bees", "body": AC_P2},
                {"order": 3, "title": "Passage 3 — Open science", "body": AC_P3},
            ],
            questions=ac_questions,
        )

        ar2_questions = []
        plastic_headings = [
            "i Why optical sorters reject some packaging",
            "ii Limits of current recycling methods",
            "iii How law is forcing recycled content",
            "iv The invention of Bakelite",
            "v Design choices that affect real recovery",
            "vi Exporting plastic waste overseas",
        ]
        for i, q in enumerate(
            [
                _headings("Paragraph A", "ii", plastic_headings),
                _headings("Paragraph B", "iii", plastic_headings),
                _headings("Paragraph C", "v", plastic_headings),
                _tfng("Chemical recycling plants are cheap to run.", "False", ["tfng", "absolute_trap"]),
                _comp("Some audits found that facilities still send a large share of input to ______.", "incineration", ["incineration"]),
                _mcq(
                    "Recycled-content mandates for bottles are described as a shift:",
                    [
                        "A from incineration to landfill",
                        "B from voluntary pledges to legal minimums",
                        "C from food-grade to mixed plastic",
                        "D from design rules to chemical plants only",
                    ],
                    "B",
                    ["mcq"],
                ),
                _short("By which year must some beverage bottles contain a minimum of recycled plastic?", "2030", ["2030"], 1, ["short_answer"]),
                _tfng("Brands say collection systems already supply enough food-grade material.", "False"),
                _ynng("The writer states that design-for-recycling rules may raise actual recovery rates more than new plants.", "Yes", ["ynng"]),
                _tfng("Black plastic trays are always accepted by optical sorters.", "False", ["tfng", "absolute_trap"]),
                _mcq(
                    "What do critics say the design-for-recycling view underestimates?",
                    [
                        "A The cost of chemical plants",
                        "B The volume of existing stock already in circulation",
                        "C Household bin contamination",
                        "D Beverage-bottle colour",
                    ],
                    "B",
                    ["mcq"],
                ),
                _tfng("The writer says tomorrow’s packaging can be simpler while old waste still needs an honest end-of-life route.", "True"),
            ],
            start=1,
        ):
            ar2_questions.append({**q, "number": i, "passage_order": 1})
        remote_info = ["A", "B", "C", "D", "E"]
        for i, q in enumerate(
            [
                _matching_info("junior staff receiving less informal mentoring", "B", remote_info),
                _matching_info("a typical split of two or three office days", "C", remote_info),
                _matching_info("uneven access to a spare room and broadband", "D", remote_info),
                _comp("Some people on a hybrid pattern reported higher job ______.", "satisfaction", ["satisfaction"]),
                _tfng("All productivity studies agree that remote work raises output.", "False", ["tfng", "absolute_trap"]),
                _mcq(
                    "A call-centre experiment found that fully remote staff had:",
                    ["A Faster handling times", "B Slower handling times", "C No change", "D Fewer meetings"],
                    "B",
                    ["mcq"],
                ),
                _ynng("The writer says junior staff in some industries received less informal mentoring.", "Yes", ["ynng"]),
                _tfng("Every city saw the same drop in office-lunch footfall.", "Not Given", ["tfng", "ng_trap"]),
                _short("Typical hybrid pattern: how many office days?", "2 or 3", ["two or three", "2-3", "two to three"], 4, ["short_answer"]),
                _mcq(
                    "Employees often keep deep work for:",
                    ["A The office", "B Home", "C Commuter trains", "D Friday only"],
                    "B",
                    ["mcq"],
                ),
                _tfng("Research that treats remote work as a single condition is described as misleading.", "True"),
                _comp("The relevant question is which activities need ______.", "co-location", ["colocation", "co location"]),
            ],
            start=13,
        ):
            ar2_questions.append({**q, "number": i, "passage_order": 2})
        coral_headings = [
            "i Why bleaching has become more frequent",
            "ii What coral gardening can and cannot do",
            "iii Breeding heat-tolerant corals, and the trade-offs",
            "iv How tourism both funds and damages reefs",
            "v Restoration as delay, not a substitute for cooler water",
            "vi The chemistry of coral skeletons",
        ]
        for i, q in enumerate(
            [
                _headings("Paragraph A", "i", coral_headings),
                _headings("Paragraph B", "ii", coral_headings),
                _headings("Paragraph C", "iii", coral_headings),
                _tfng("A bleached coral is always dead immediately.", "False"),
                _tfng("Gardening can keep pace with a basin-scale heatwave.", "False"),
                _comp("Coral gardening grows fragments in ______ before transplanting them.", "nurseries", ["a nursery"]),
                _mcq(
                    "Critics of gardening call it:",
                    ["A A sewage solution", "B A photogenic distraction", "C A replacement for fish", "D An emissions cut"],
                    "B",
                    ["mcq"],
                ),
                _ynng("The writer says introducing a heat-tolerant strain may still reduce genetic diversity.", "Yes", ["ynng"]),
                _tfng("Sewage and sediment can be ignored if breeding programmes succeed.", "False"),
                _short("What do some diver fees fund?", "rangers", ["ranger", "rangers"], 2, ["short_answer"]),
                _mcq(
                    "A resort that advertises a restored reef beside an untreated outfall is described as selling:",
                    ["A A habitat", "B A photograph", "C A fishery", "D An audit"],
                    "B",
                    ["mcq"],
                ),
                _comp("The writer refuses a swap in which a nursery frame excuses postponing sewage, sediment and ______.", "emissions", ["emission cuts"]),
                _tfng("The passage claims gardening is completely useless.", "False"),
                _ynng("The writer believes delay tactics can still have human value if they keep a fishery alive.", "Yes", ["ynng"]),
                _matching_info("certification schemes that travellers rarely read", "D", ["A", "B", "C", "D", "E"]),
                _short("What event is named when corals expel algae and turn white?", "bleaching", ["coral bleaching"], 2, ["short_answer"]),
            ],
            start=25,
        ):
            ar2_questions.append({**q, "number": i, "passage_order": 3})

        ar2 = await _ensure_set(
            db,
            skill="reading",
            module="academic",
            slug="reading-ac-exam-pack-v3",
            title="Academic Reading — Plastics, remote work & reefs",
            time_limit_sec=3600,
            difficulty="medium",
            passages=[
                {"order": 1, "title": "Passage 1 — Plastic recycling", "body": AC_P4},
                {"order": 2, "title": "Passage 2 — Remote work", "body": AC_P5},
                {"order": 3, "title": "Passage 3 — Coral restoration", "body": AC_P6},
            ],
            questions=ar2_questions,
        )

        await _ensure_set(
            db,
            skill="reading",
            module="academic",
            slug="reading-ac-tfng-drill-v2",
            title="Academic drill — TFNG traps",
            time_limit_sec=900,
            difficulty="medium",
            kind="drill",
            passages=[{"order": 1, "title": "Urban heat islands", "body": AC_P1}],
            questions=[
                {**_tfng("Cities can stay warmer at night than nearby rural areas.", "True"), "number": 1, "passage_order": 1},
                {**_tfng("Cool roofs never create problems for pedestrians.", "False", ["tfng", "absolute_trap"]), "number": 2, "passage_order": 1},
                {**_tfng("Heat risk is often higher in lower-income neighbourhoods.", "True"), "number": 3, "passage_order": 1},
                {**_tfng("Every city has banned asphalt roofs.", "Not Given", ["tfng", "ng_trap"]), "number": 4, "passage_order": 1},
                {**_tfng("Green roofs need maintenance budgets.", "True"), "number": 5, "passage_order": 1},
                {**_tfng("Street trees are impossible wherever utilities exist.", "False", ["tfng", "absolute_trap"]), "number": 6, "passage_order": 1},
            ],
        )

        plastic_headings = [
            "i Why optical sorters reject some packaging",
            "ii Limits of current recycling methods",
            "iii How law is forcing recycled content",
            "iv The invention of Bakelite",
            "v Design choices that affect real recovery",
            "vi Exporting plastic waste overseas",
        ]
        await _ensure_set(
            db,
            skill="reading",
            module="academic",
            slug="reading-ac-headings-drill-v1",
            title="Academic drill — Matching headings",
            time_limit_sec=720,
            difficulty="medium",
            kind="drill",
            passages=[{"order": 1, "title": "Plastic recycling", "body": AC_P4}],
            questions=[
                {**_headings("Paragraph A", "ii", plastic_headings), "number": 1, "passage_order": 1},
                {**_headings("Paragraph B", "iii", plastic_headings), "number": 2, "passage_order": 1},
                {**_headings("Paragraph C", "v", plastic_headings), "number": 3, "passage_order": 1},
            ],
        )

        gt_questions = []
        for i, q in enumerate(
            [
                _mcq(
                    "What does a standard membership include?",
                    [
                        "A Gym only",
                        "B Gym, pool and group fitness classes",
                        "C Pool and café discounts only",
                        "D Personal training sessions",
                    ],
                    "B",
                    ["mcq", "section1"],
                ),
                _short("Monthly fee for standard membership (number only)?", "32", ["£32", "32 pounds"], 2, ["short_answer", "section1"]),
                _comp("Lost membership cards cost £______ to replace.", "5", ["five", "£5"], ["completion", "section1"]),
                _tfng("Towels are provided free at the leisure centre.", "False", ["tfng", "section1"]),
                _short("How many days’ notice is required to cancel?", "30", ["thirty", "30 days"], 2, ["short_answer", "section1"]),
                _mcq(
                    "Induction sessions are held on:",
                    ["A Mondays and Wednesdays", "B Tuesdays and Thursdays", "C Weekends only", "D Fridays at 09:00"],
                    "B",
                    ["mcq", "section1"],
                ),
                _tfng("Standard membership includes the gym, pool and group fitness classes.", "True", ["tfng", "section1"]),
                _short("What form number is used to join?", "LC-12", ["LC12", "form LC-12"], 2, ["short_answer", "section1"]),
                _comp("Peak hours in the evening start at ______.", "17:00", ["5 p.m.", "5pm", "17:00", "5:00"], ["completion", "section1"]),
                _tfng("Pool lanes 3–4 are reserved for members during peak hours.", "False", ["tfng", "section1"]),
                _short("Yearly membership price (number only)?", "340", ["£340", "340 pounds"], 2, ["short_answer", "section1"]),
                _comp("Lockers require a £______ coin deposit.", "1", ["£1", "one"], ["completion", "section1"]),
                _tfng("Under-16s can join without any adult signature.", "False", ["tfng", "section1"]),
            ],
            start=1,
        ):
            gt_questions.append({**q, "number": i, "passage_order": 1})
        for i, q in enumerate(
            [
                _tfng("The chilled bay temperature must stay between 2°C and 5°C.", "True", ["tfng", "section2"]),
                _short("Engineer extension to call if temperature is out of range?", "440", ["ext. 440", "ext 440"], 2, ["short_answer", "section2"]),
                _comp("Near-misses must be reported within ______ hours.", "24", ["twenty-four", "24 hours"], ["completion", "section2"]),
                _tfng("Personal phones are allowed in the picking zone on night shifts.", "False", ["tfng", "section2"]),
                _mcq(
                    "Visitors beyond the yellow line must wear:",
                    ["A Suits", "B High-visibility vests", "C Ear plugs only", "D White coats"],
                    "B",
                    ["mcq", "section2"],
                ),
                _tfng("Outgoing supervisors must complete the digital handover form before leaving.", "True", ["tfng", "section2"]),
                _comp("If the chilled bay is out of range for more than ______ minutes, call the engineer.", "15", ["fifteen", "15 minutes"], ["completion", "section2"]),
                _tfng("Stock may be moved to bay D without any authorisation.", "False", ["tfng", "section2"]),
                _short("Who must authorise a transfer to bay D?", "night manager", ["the night manager"], 3, ["short_answer", "section2"]),
                _mcq(
                    "Visitors must wait:",
                    ["A On the dock", "B In reception", "C In bay C", "D At the yellow line"],
                    "B",
                    ["mcq", "section2"],
                ),
                _comp("Near-miss reports use portal ______.", "RL-SAFE", ["RL SAFE", "rl-safe"], ["completion", "section2"]),
                _tfng("The memo takes effect on Monday.", "True", ["tfng", "section2"]),
                _tfng("High-visibility vests are mandatory past the yellow line.", "True", ["tfng", "section2"]),
            ],
            start=14,
        ):
            gt_questions.append({**q, "number": i, "passage_order": 2})
        for i, q in enumerate(
            [
                _ynng(
                    "The writer suggests libraries increasingly support digital public services.",
                    "Yes",
                    ["ynng", "section3"],
                ),
                _ynng(
                    "Rising wifi session counts prove print borrowing no longer matters for young children.",
                    "No",
                    ["ynng", "section3"],
                ),
                _ynng(
                    "All rural libraries now open seven days a week.",
                    "Not Given",
                    ["ynng", "ng_trap", "section3"],
                ),
                _mcq(
                    "Campaigners want funders to measure outcomes such as:",
                    [
                        "A wifi hours only",
                        "B successful benefit applications assisted",
                        "C café revenue",
                        "D number of closed banks nearby",
                    ],
                    "B",
                    ["mcq", "section3"],
                ),
                _comp(
                    "Supporters say refusing help with a housing form pushes people toward paid ______.",
                    "intermediaries",
                    ["paid intermediaries"],
                    ["completion", "section3"],
                ),
                _ynng(
                    "The writer presents libraries as sometimes the last free indoor place with wifi in towns that lost banks.",
                    "Yes",
                    ["ynng", "section3"],
                ),
                _ynng(
                    "Rural branches always open seven days a week with full-time staff.",
                    "No",
                    ["ynng", "section3"],
                ),
                _comp(
                    "Well-funded city systems run coding clubs and ______ spaces.",
                    "maker",
                    ["maker spaces", "makerspaces"],
                    ["completion", "section3"],
                ),
                _ynng(
                    "Print borrowing still matters most for children under eight.",
                    "Yes",
                    ["ynng", "section3"],
                ),
                _mcq(
                    "Critics worry that mission creep turns libraries into:",
                    [
                        "A unofficial social-work offices",
                        "B bank branches",
                        "C wifi shops",
                        "D council voting halls",
                    ],
                    "A",
                    ["mcq", "section3"],
                ),
                _short(
                    "How many minutes might staff sit with a confused user?",
                    "20",
                    ["twenty", "20 minutes"],
                    2,
                    ["short_answer", "section3"],
                ),
                _ynng(
                    "The emerging middle path is partnership between librarians and specialist charities.",
                    "Yes",
                    ["ynng", "section3"],
                ),
                _comp(
                    "Rural branches may open only three ______ a week.",
                    "afternoons",
                    ["afternoon"],
                    ["completion", "section3"],
                ),
                _ynng(
                    "Librarians in the partnership model handle navigation and appointments.",
                    "Yes",
                    ["ynng", "section3"],
                ),
            ],
            start=27,
        ):
            gt_questions.append({**q, "number": i, "passage_order": 3})

        gt1 = await _ensure_set(
            db,
            skill="reading",
            module="general",
            slug="reading-gt-exam-pack-v2",
            title="GT Reading — Leisure, workplace & libraries",
            time_limit_sec=3600,
            difficulty="medium",
            passages=[
                {"order": 1, "title": "Section 1 — Leisure centre", "body": GT_S1},
                {"order": 2, "title": "Section 2 — Warehouse memo", "body": GT_S2},
                {"order": 3, "title": "Section 3 — Modern libraries", "body": GT_S3},
            ],
            questions=gt_questions,
        )

        gt2_questions = []
        for i, q in enumerate(
            [
                _mcq("The clinic job is:", ["A Full time nights", "B 20 hours, weekday mornings", "C Saturday only", "D Unpaid"], "B", ["mcq", "section1"]),
                _short("Form number for the clinic job", "WB-04", ["WB04", "form WB-04"], 2, ["short_answer", "section1"]),
                _comp("Warehouse applicants should text NIGHT plus their name to ______.", "07700900882", ["07700 900882"], ["completion", "section1"]),
                _tfng("The warehouse role is open to 16-year-olds.", "False", ["tfng", "section1"]),
                _short("Café interviews are on which date?", "3 March", ["3rd March", "March 3"], 3, ["short_answer", "section1"]),
                _mcq("Café interviews are held:", ["A At the café", "B In the museum education room", "C At Job Club", "D Online only"], "B", ["mcq", "section1"]),
                _tfng("A food-hygiene certificate is required before the café start date.", "True", ["tfng", "section1"]),
                _comp("From 12 May the 14A will not stop at ______.", "Job Club", ["the Job Club"], ["completion", "section1"]),
                _short("Use which stop on Market Square?", "stop C", ["C", "stop C"], 2, ["short_answer", "section1"]),
                _tfng("The shuttle from the square runs at weekends.", "False", ["tfng", "section1"]),
                _comp("A black rucksack was handed in on ______.", "Tuesday", ["tues"], ["completion", "section1"]),
                _short("Uncollected lost property goes to the charity shop after how many days?", "14", ["fourteen", "14 days"], 2, ["short_answer", "section1"]),
                _mcq("Steel-toe boots for the warehouse job are:", ["A Not needed", "B Supplied", "C Bought by staff", "D Optional after month one"], "B", ["mcq", "section1"]),
            ],
            start=1,
        ):
            gt2_questions.append({**q, "number": i, "passage_order": 1})
        for i, q in enumerate(
            [
                _tfng("Front-of-house staff may take uniforms home to wash.", "False", ["tfng", "section2"]),
                _comp("Kitchen whites are changed at the start of each ______.", "shift", ["shifts"], ["completion", "section2"]),
                _short("Where do name badges stay overnight?", "staff desk", ["the staff desk"], 3, ["short_answer", "section2"]),
                _mcq("A shift over six hours includes:", ["A A paid hour", "B A 30-minute unpaid break", "C No break", "D Two paid breaks"], "B", ["mcq", "section2"]),
                _tfng("Phones may be used in guest corridors.", "False", ["tfng", "section2"]),
                _comp("After 23:00, locked-out guests: call night security on extension ______.", "201", ["ext. 201"], ["completion", "section2"]),
                _tfng("A master key may be left in a door during a short errand.", "False", ["tfng", "section2"]),
                _short("Fire assembly point", "Car Park B", ["far end of Car Park B", "car park B"], 4, ["short_answer", "section2"]),
                _comp("Weekly alarm tests are on Tuesdays at ______.", "10:00", ["10 am", "10 a.m.", "ten"], ["completion", "section2"]),
                _mcq("Guest noise complaints go on:", ["A HV-12", "B LC-12", "C WB-04", "D RL-SAFE"], "A", ["mcq", "section2"]),
                _tfng("Maintenance faults should be posted in WhatsApp groups.", "False", ["tfng", "section2"]),
                _comp("Cash tips are recorded in the ______.", "till", ["the till"], ["completion", "section2"]),
                _tfng("Breaks should be taken in the staff room.", "True", ["tfng", "section2"]),
            ],
            start=14,
        ):
            gt2_questions.append({**q, "number": i, "passage_order": 2})
        for i, q in enumerate(
            [
                _ynng("The writer thinks night markets are first a labour market, not only a tourist spectacle.", "Yes", ["ynng"]),
                _ynng("Raising pitch fees always helps the poorest vendors.", "No", ["ynng"]),
                _comp("Hygiene rules are often written for kitchens with sinks and staff ______.", "rotas", ["rota"], ["completion"]),
                _mcq(
                    "Cities that want both safety and survival invent:",
                    ["A Festival rents", "B Intermediate licences", "C A ban on carts", "D Matching awnings only"],
                    "B",
                    ["mcq"],
                ),
                _tfng("A raid that empties a market for a week is presented as the best long-term tool.", "False"),
                _ynng("Resident complaints are sometimes a proxy for who belongs on the pavement after dark.", "Yes", ["ynng"]),
                _short("Until what time might a market stay open on a street of new apartments?", "02:00", ["2 a.m.", "2am", "02:00"], 2, ["short_answer"]),
                _mcq(
                    "Some cities now publish a one-page compact covering hours, waste collection and:",
                    ["A A named officer", "B Ticket prices", "C Hotel ratings", "D Cycle hire"],
                    "A",
                    ["mcq"],
                ),
                _ynng("The writer romanticises every stall, including those with child labour.", "No", ["ynng"]),
                _comp("Night markets are compared to infrastructure like a ______ route.", "bus", ["bus route"], ["completion"]),
                _tfng("Pricing markets as a festival can push out vendors who cannot pay festival rents.", "True"),
                _ynng("The writer says inspections that are only for show can hide overcrowding and counterfeit goods.", "Yes", ["ynng"]),
                _comp("Stallholders rent a few square ______.", "metres", ["meters"], ["completion"]),
                _mcq(
                    "The practical paperwork that 'keeps the lights on' is described as:",
                    ["A Dull", "B Optional", "C A tourist brochure", "D A raid"],
                    "A",
                    ["mcq"],
                ),
            ],
            start=27,
        ):
            gt2_questions.append({**q, "number": i, "passage_order": 3})

        gt2 = await _ensure_set(
            db,
            skill="reading",
            module="general",
            slug="reading-gt-exam-pack-v3",
            title="GT Reading — Jobs, hotel handbook & night markets",
            time_limit_sec=3600,
            difficulty="medium",
            passages=[
                {"order": 1, "title": "Section 1 — Job Club notices", "body": GT_S4},
                {"order": 2, "title": "Section 2 — Hotel handbook", "body": GT_S5},
                {"order": 3, "title": "Section 3 — Night markets", "body": GT_S6},
            ],
            questions=gt2_questions,
        )

        await _ensure_set(
            db,
            skill="reading",
            module="general",
            slug="reading-gt-short-drill-v2",
            title="GT drill — forms & facts",
            time_limit_sec=600,
            kind="drill",
            passages=[{"order": 1, "title": "Leisure centre", "body": GT_S1}],
            questions=[
                {**_short("Yearly membership price?", "340", ["£340", "340 pounds"], 2), "number": 1, "passage_order": 1},
                {**_short("Coin deposit for lockers?", "1", ["£1", "1 pound"], 2), "number": 2, "passage_order": 1},
                {**_comp("Book induction at least ______ hours ahead.", "24", ["twenty-four"], ["completion"]), "number": 3, "passage_order": 1},
                {**_tfng("Under-16s can join without any adult signature.", "False"), "number": 4, "passage_order": 1},
            ],
        )

        listen = await _ensure_set(
            db,
            skill="listening",
            module="shared",
            slug="listening-shared-campus-v2",
            title="Listening — Campus & city (Sections 1–4)",
            time_limit_sec=1800,
            difficulty="medium",
            passages=[],
            audio=_audio_seed_items(CAMPUS_AUDIO),
            questions=CAMPUS_QUESTIONS,
        )

        listen2 = await _ensure_set(
            db,
            skill="listening",
            module="shared",
            slug="listening-shared-housing-v1",
            title="Listening — Housing & the compact city (Sections 1–4)",
            time_limit_sec=1800,
            difficulty="medium",
            passages=[],
            audio=_audio_seed_items(HOUSING_AUDIO),
            questions=HOUSING_QUESTIONS,
        )

        await _ensure_set(
            db,
            skill="listening",
            module="shared",
            slug="listening-shared-numbers-v2",
            title="Listening drill — Numbers & spelling",
            time_limit_sec=600,
            kind="drill",
            passages=[],
            audio=_audio_seed_items(NUMBERS_AUDIO),
            questions=NUMBERS_QUESTIONS,
        )

        # Refresh mock blueprints to point at v2 packs
        for title, module, reading, writing1, writing2, cues in [
            (
                "Academic full mock v1",
                "academic",
                ar1,
                "The charts below show the proportion of energy produced from coal, gas, nuclear and renewables "
                "in a European country in 2000 and 2020.\n\nSummarise the information by selecting and reporting "
                "the main features, and make comparisons where relevant.\n\nWrite at least 150 words.",
                "Some people believe that unpaid community service should be a compulsory part of high school "
                "programmes. To what extent do you agree or disagree?\n\nGive reasons for your answer and include "
                "any relevant examples from your own knowledge or experience.\n\nWrite at least 250 words.",
                {
                    "part1": "Let's talk about your hometown. What do you like most about living there?",
                    "part2": "Describe a skill you would like to learn. You should say: what the skill is, "
                    "how you would learn it, how long it might take, and explain why you want to learn it.",
                    "part3": "Should schools teach more practical skills? How might that affect academic subjects?",
                },
            ),
            (
                "General Training full mock v1",
                "general",
                gt1,
                "You recently stayed in a hotel and had several problems with the room and the service.\n\n"
                "Write a letter to the hotel manager. In your letter:\n"
                "- describe the problems\n- explain how they affected your stay\n"
                "- say what you would like the manager to do\n\nWrite at least 150 words.",
                "In many countries, people are living longer. What problems does this cause for individuals "
                "and society? What measures could be taken to address these problems?\n\nWrite at least 250 words.",
                {
                    "part1": "Do you enjoy reading? What kinds of things do you read?",
                    "part2": "Describe a place you like to visit. You should say: where it is, how you get there, "
                    "what you do there, and explain why you like it.",
                    "part3": "How is tourism changing in your country? Does it create more benefits or problems?",
                },
            ),
            (
                "Academic full mock v2",
                "academic",
                ar2,
                "The graph below shows how people in a city travelled to work in 1990, 2005 and 2020.\n\n"
                "Summarise the information by selecting and reporting the main features, and make comparisons "
                "where relevant.\n\nWrite at least 150 words.",
                "More people are choosing to work from home rather than in an office. Is this a positive or "
                "negative development?\n\nGive reasons for your answer and include any relevant examples from "
                "your own knowledge or experience.\n\nWrite at least 250 words.",
                {
                    "part1": "Let's talk about food and cooking. What kinds of food do you like to eat?",
                    "part2": "Describe a memorable meal you have had. You should say: where you had it, who you "
                    "were with, what you ate, and explain why this meal was memorable.",
                    "part3": "Why do people enjoy eating together? Has the way people eat changed in your country?",
                },
            ),
            (
                "General Training full mock v2",
                "general",
                gt2,
                "You bought an item online and it arrived damaged. Write a letter to the company. In your letter:\n"
                "- describe the item and the problem\n- explain what you have already done\n"
                "- say what you want the company to do\n\nWrite at least 150 words.",
                "More people now shop online instead of going to local shops. Do the advantages of this outweigh "
                "the disadvantages?\n\nGive reasons for your answer and include any relevant examples from your "
                "own knowledge or experience.\n\nWrite at least 250 words.",
                {
                    "part1": "Let's talk about the weather. What is the weather like where you live?",
                    "part2": "Describe a season you enjoy. You should say: which season it is, what the weather "
                    "is like, what you usually do then, and explain why you enjoy this season.",
                    "part3": "How does weather affect daily life in your country? Should individuals or governments "
                    "do more to protect the environment?",
                },
            ),
        ]:
            bp = await db.scalar(select(MockBlueprint).where(MockBlueprint.title == title))
            if bp is None:
                bp = MockBlueprint(module=module, title=title, review_status="published")
                db.add(bp)
            bp.module = module
            bp.listening_set_id = listen2.id if "v2" in title else listen.id
            bp.reading_set_id = reading.id
            bp.writing_task1_prompt = writing1
            bp.writing_task2_prompt = writing2
            bp.speaking_cues = cues
            bp.review_status = "published"

        await db.commit()
        # Retire short demo packs from bank v1 so hubs show exam-quality sets.
        for slug in (
            "reading-ac-bees-v1",
            "reading-ac-bees-short-v1",
            "reading-gt-library-v1",
            "reading-gt-library-drill-v1",
            "listening-shared-demo-v1",
            "listening-shared-numbers-v1",
        ):
            old = await db.scalar(select(ContentSet).where(ContentSet.slug == slug))
            if old:
                old.review_status = "retired"
        await db.commit()
        await _seed_prompt_bank(db)
        print(f"Seeded/refreshed content bank v{SEED_BANK_VERSION}.")


async def _seed_prompt_bank(db) -> None:
    for row in all_curated():
        existing = await db.scalar(select(PromptItem).where(PromptItem.slug == row["slug"]))
        version = int((existing.meta or {}).get("bank_version") or 0) if existing else 0
        if existing and version >= PROMPT_BANK_VERSION and existing.source == "curated":
            continue
        if existing is None:
            existing = PromptItem(slug=row["slug"])
            db.add(existing)
        existing.skill = row["skill"]
        existing.module = row["module"]
        existing.task = row["task"]
        existing.title = row["title"]
        existing.prompt = row["prompt"]
        existing.payload = row.get("payload") or {}
        existing.source = "curated"
        existing.review_status = "published"
        existing.owner_user_id = None
        existing.meta = {"seed": True, "bank_version": PROMPT_BANK_VERSION}
    await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_content())
