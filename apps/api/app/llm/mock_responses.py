from __future__ import annotations

import re
from typing import Any


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _estimate_band(text: str) -> float:
    words = _word_count(text)
    sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
    avg_len = words / sentences
    band = 5.0
    if words >= 150:
        band += 0.5
    if words >= 250:
        band += 0.5
    if avg_len >= 12:
        band += 0.5
    if re.search(r"\b(however|therefore|although|furthermore)\b", text, re.I):
        band += 0.5
    return min(8.0, max(4.5, round(band * 2) / 2))


def _body(user: str) -> str:
    for marker in ("Candidate response:\n", "Transcript:\n", "Full response:\n", "Text to analyse:\n"):
        if marker in user:
            user = user.split(marker, 1)[-1]
    return user.strip()


def _sample_quote(user: str) -> str:
    body = _body(user)
    compact = " ".join(body.split())
    if len(compact) >= 24:
        return compact[8:48].strip() or compact[:24]
    return compact[:24] or "the"


def mock_json_for_agent(agent: str, user: str) -> dict[str, Any]:
    band = _estimate_band(user)
    quote = _sample_quote(user)
    if agent == "writing":
        return {
            "task_response": {
                "criterion": "Task Response",
                "proposed_band": band,
                "summary": "Addresses the prompt with a clear position, though some ideas need more support.",
                "evidence": [
                    {
                        "quote": quote,
                        "comment": "Introduces the topic but could state the thesis more directly.",
                    }
                ],
            },
            "coherence": {
                "criterion": "Coherence and Cohesion",
                "proposed_band": max(4.5, band - 0.5),
                "summary": "Paragraphing is present; linking can be more varied.",
                "evidence": [],
            },
            "lexical": {
                "criterion": "Lexical Resource",
                "proposed_band": band,
                "summary": "Vocabulary is generally adequate with occasional repetition.",
                "evidence": [],
            },
            "grammar": {
                "criterion": "Grammatical Range and Accuracy",
                "proposed_band": max(4.5, band - 0.5),
                "summary": "Mix of simple and complex sentences with some errors that do not impede meaning.",
                "evidence": [],
            },
            "word_count": _word_count(user),
            "task_fit_notes": "Heuristic fallback used because no live LLM key was configured.",
        }
    if agent == "speaking":
        return {
            "fluency": {
                "criterion": "Fluency and Coherence",
                "proposed_band": band,
                "summary": "Ideas are mostly connected; pacing is estimated from the transcript.",
                "evidence": [],
            },
            "lexical": {
                "criterion": "Lexical Resource",
                "proposed_band": band,
                "summary": "Everyday vocabulary with limited idiomatic range.",
                "evidence": [],
            },
            "grammar": {
                "criterion": "Grammatical Range and Accuracy",
                "proposed_band": max(4.5, band - 0.5),
                "summary": "Mostly controlled simple structures.",
                "evidence": [],
            },
            "pronunciation": {
                "criterion": "Pronunciation",
                "proposed_band": band,
                "summary": "Pronunciation is a proxy estimate from transcript features, not acoustic analysis.",
                "evidence": [],
            },
            "mode": "text",
            "words_per_minute": None,
            "duration_seconds": None,
        }
    if agent == "grammar":
        return {
            "issues": [
                {
                    "span": "there is many",
                    "issue_type": "subject-verb agreement",
                    "correction": "there are many",
                    "explanation": "Plural noun requires a plural verb.",
                    "cefr_tag": "B1",
                }
            ],
            "recurring_patterns": ["article use", "tense consistency"],
            "lexical_range_notes": "Core academic words appear, but collocations could be richer.",
            "vocabulary_upgrades": ["important → significant", "get better → improve"],
        }
    if agent == "scoring":
        return {
            "criteria": [
                {"criterion": "overall", "band": band, "rationale": "Heuristic estimate from length and discourse markers."}
            ],
            "overall_band": band,
            "confidence": 0.45,
            "scoring_notes": "Fallback scorer; replace with a live provider for examiner-style rationale.",
        }
    if agent == "feedback":
        return {
            "strengths": ["Clear attempt to answer the task", "Some useful topic vocabulary"],
            "weaknesses": ["Limited development of ideas", "Repetitive sentence openings"],
            "actions": [
                {
                    "title": "Expand one body paragraph",
                    "detail": "Add a concrete example and a result sentence to each main idea.",
                    "skill_focus": "task_response",
                    "drill_prompt": "Write one body paragraph that states a reason, gives a specific example, and ends with a result. Use this topic: community service in schools.",
                    "drill_task": "task2",
                },
                {
                    "title": "Collect 10 topic collocations",
                    "detail": "Write them in full sentences related to this prompt.",
                    "skill_focus": "lexical",
                    "drill_prompt": "Write 10 sentences using stronger collocations for education policy (e.g. 'compulsory programme', 'civic responsibility').",
                    "drill_task": "task2",
                },
            ],
            "examiner_summary": "A solid mid-band draft. Focus next on development and grammatical accuracy.",
        }
    if agent == "performance":
        return {
            "trends": [{"label": "overall", "direction": "flat", "note": "Not enough history yet to show a trend."}],
            "plateau": False,
            "next_focus": "coherence",
            "comparison_note": "This is an early attempt. Keep submitting work to unlock trend analysis.",
        }
    if agent == "revision":
        span = _sample_quote(user)
        return {
            "original_span": span,
            "rewritten": f"{span.rstrip('.')} with a clearer position and a concrete example.",
            "changes": ["Clearer topic sentence", "Added a specific example"],
            "target_band": min(9.0, band + 0.5),
            "notes": "Heuristic rewrite used because no live LLM key was configured.",
        }
    if agent == "coach":
        last = ""
        if "LAST_ACTION:" in user:
            last = user.split("LAST_ACTION:", 1)[1].splitlines()[0].strip()
        qid = ""
        match = re.search(r"id=([0-9a-f-]{8,})", user, re.I)
        if match:
            qid = match.group(1)
        if last in {"", "none"}:
            return {
                "thought": "List the misses first.",
                "action": "list_misses",
            }
        if last == "list_misses":
            return {
                "thought": "Inspect the first miss.",
                "action": "inspect_item",
                "question_id": qid,
            }
        if last == "inspect_item":
            return {
                "thought": "Ground the explanation in the source.",
                "action": "quote_context",
                "question_id": qid,
                "query": "key phrase from the item",
            }
        if last == "quote_context":
            return {
                "thought": "Write a trap-aware note.",
                "action": "note_explanation",
                "question_id": qid,
                "trap_type": "paraphrase_miss",
                "explanation": "The recording/passage states the key directly; a nearby distractor is easy to copy.",
                "tip": "Underline numbers, names, and negatives while you listen or read.",
                "skill_tag": "accuracy",
            }
        return {
            "thought": "Notes are sufficient.",
            "action": "finish",
        }
    if agent == "explain":
        qids = re.findall(r'"question_id":\s*"([^"]+)"', user)
        items = []
        for qid in qids[:8]:
            items.append(
                {
                    "question_id": qid,
                    "explanation": "The correct answer is in the wording of the text or recording; a nearby phrase is a distractor.",
                    "tip": "Check spelling, numbers, and absolute words before you lock the answer.",
                    "skill_tag": "accuracy",
                    "trap_type": "paraphrase_miss",
                }
            )
        if not items:
            items = [
                {
                    "question_id": "unknown",
                    "explanation": "Compare your answer with the exact wording in the source.",
                    "tip": "Underline the key phrase first.",
                    "skill_tag": "accuracy",
                    "trap_type": "paraphrase_miss",
                }
            ]
        return {"items": items}
    if agent == "bank":
        if "task1" in user.lower() and "general" not in user.lower():
            return {
                "title": "Bicycle share schemes",
                "topic": "The chart below shows bicycle-share trips in three cities between 2016 and 2022.",
                "instruction": "Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
                "bullets": [],
                "bullet_lead": "",
                "visual": {
                    "kind": "line",
                    "title": "Bicycle-share trips (millions)",
                    "xKey": "year",
                    "yLabel": "Trips (millions)",
                    "series": [
                        {"key": "A", "label": "City A", "color": "#1b4d4a"},
                        {"key": "B", "label": "City B", "color": "#8a6328"},
                    ],
                    "rows": [
                        {"year": "2016", "A": 4, "B": 2},
                        {"year": "2019", "A": 9, "B": 6},
                        {"year": "2022", "A": 11, "B": 10},
                    ],
                },
            }
        if "task1" in user.lower():
            return {
                "title": "Request a reference",
                "topic": "You are applying for a new job and would like a former manager to provide a reference.",
                "instruction": "",
                "bullets": ["remind them who you are", "say why you need the reference", "explain how they can send it"],
                "bullet_lead": "In your letter:",
                "visual": None,
            }
        if "speaking" in user.lower() or "part 1" in user.lower():
            return {
                "title": "Clothes / a useful object",
                "part1_topic": "Let's talk about clothes.",
                "part1_questions": [
                    "What do you usually wear during the week?",
                    "Do you enjoy shopping for clothes?",
                    "Did you wear a uniform at school?",
                ],
                "part2_topic": "Describe an object you use every day.",
                "part2_bullets": ["what it is", "how you got it", "how you use it"],
                "part2_explain": "why this object is useful to you",
                "part3_questions": [
                    "Do people value objects more than they used to?",
                    "Should products be designed to last longer?",
                    "How might everyday technology change in the next ten years?",
                ],
            }
        return {
            "title": "Public libraries",
            "topic": "Some people think public libraries are no longer needed because of the internet. To what extent do you agree or disagree?",
            "instruction": "Give reasons for your answer and include any relevant examples from your own knowledge or experience.",
            "bullets": [],
            "bullet_lead": "",
            "visual": None,
        }
    return {"note": "unknown agent"}
