from app.content.assign import first_unused, shuffle_ids, should_inject_generated
from app.content.prompt_bank import all_curated, format_speaking_prompt
from app.llm.mock_responses import mock_json_for_agent
from app.content.generate import GeneratedSpeaking, GeneratedWriting


def test_curated_bank_covers_slots() -> None:
    items = all_curated()
    writing = [row for row in items if row["skill"] == "writing"]
    speaking = [row for row in items if row["skill"] == "speaking"]
    assert len(writing) >= 24
    assert len(speaking) >= 8
    slugs = [row["slug"] for row in items]
    assert len(slugs) == len(set(slugs))
    assert any(row["module"] == "academic" and row["task"] == "task2" for row in writing)
    assert any(row["module"] == "general" and row["task"] == "task1" for row in writing)


def test_user_shuffle_differs() -> None:
    ids = [f"p{i}" for i in range(12)]
    a = shuffle_ids("user-a", "writing:academic:task2", ids)
    b = shuffle_ids("user-b", "writing:academic:task2", ids)
    assert a != b
    assert sorted(a) == sorted(ids)


def test_first_unused_skips_completed() -> None:
    ordered = ["a", "b", "c"]
    assert first_unused(ordered, set()) == "a"
    assert first_unused(ordered, {"a"}) == "b"
    assert first_unused(ordered, {"a", "b", "c"}) is None
    assert first_unused(ordered, {"a"}, {"b"}) == "c"


def test_inject_generated_is_stable_and_not_first_sit() -> None:
    assert should_inject_generated("user-a", "writing:academic:task2", 0) is False
    first = should_inject_generated("user-a", "writing:academic:task2", 3)
    again = should_inject_generated("user-a", "writing:academic:task2", 3)
    other = should_inject_generated("user-b", "writing:academic:task2", 3)
    assert first == again
    assert first in {True, False}
    assert other in {True, False}


def test_speaking_format_has_parts() -> None:
    pack = next(row for row in all_curated() if row["skill"] == "speaking")["payload"]["speaking"]
    part1 = format_speaking_prompt("part1", pack)
    full = format_speaking_prompt("full", pack)
    assert pack["part1"]["questions"][0] in part1
    assert "Part 2" in full
    assert pack["part2"]["topic"] in full


def test_bank_mock_matches_contracts() -> None:
    GeneratedWriting.model_validate(mock_json_for_agent("bank", "Create one original IELTS Writing academic task2 paper."))
    GeneratedWriting.model_validate(mock_json_for_agent("bank", "Create one original IELTS Writing academic task1 paper."))
    GeneratedSpeaking.model_validate(mock_json_for_agent("bank", "Create one original IELTS Speaking set (Part 1 interview)."))
