from app.agents.tools import analyze_text, filler_count, word_count
from app.agents.verify import apply_grammar_reconciliation, quote_in_source, verify_specialist
from app.eval.gold_set import GOLD_WRITING
from app.llm.mock_responses import mock_json_for_agent
from app.schemas.agents import (
    FeedbackAgentOutput,
    GrammarAgentOutput,
    PerformanceAgentOutput,
    RevisionAgentOutput,
    SpeakingAgentOutput,
    WritingAgentOutput,
)


def test_gold_quotes_exist_in_essays() -> None:
    for sample in GOLD_WRITING:
        essay = sample["essay"]
        for quote in sample["must_quotes"]:
            assert quote_in_source(quote, essay), sample["id"]


def test_gold_bands_are_half_steps() -> None:
    for sample in GOLD_WRITING:
        assert sample["human_overall"] * 2 == int(sample["human_overall"] * 2)
        for band in sample["human_criteria"].values():
            assert band * 2 == int(band * 2)


def test_verifier_drops_invented_quotes() -> None:
    sample = GOLD_WRITING[0]
    analysis = {
        "task_response": {
            "criterion": "Task Response",
            "proposed_band": 6.0,
            "summary": "ok",
            "evidence": [
                {"quote": sample["must_quotes"][0], "comment": "real"},
                {"quote": "this sentence is not in the essay at all", "comment": "fake"},
            ],
        },
        "coherence": {"criterion": "CC", "proposed_band": 6.0, "summary": "ok", "evidence": []},
        "lexical": {"criterion": "LR", "proposed_band": 6.0, "summary": "ok", "evidence": []},
        "grammar": {"criterion": "GRA", "proposed_band": 6.0, "summary": "ok", "evidence": []},
    }
    verified = verify_specialist(
        analysis, sample["essay"], ("task_response", "coherence", "lexical", "grammar")
    )
    assert verified["evidence_quote_total"] == 2
    assert verified["evidence_quote_dropped"] == 1
    assert verified["quote_hit_rate"] == 0.5
    kept = verified["task_response"]["evidence"]
    assert len(kept) == 1
    assert quote_in_source(kept[0]["quote"], sample["essay"])


def test_quote_hit_rate_meets_threshold_on_mostly_grounded_output() -> None:
    sample = GOLD_WRITING[2]
    real_quote = sample["must_quotes"][0]
    real = [{"quote": real_quote, "comment": "ok"}] * 19
    fake = [{"quote": "invented evidence span xyz", "comment": "nope"}]
    analysis = {
        "task_response": {
            "criterion": "TR",
            "proposed_band": 7.0,
            "summary": "ok",
            "evidence": real + fake,
        },
        "coherence": {"criterion": "CC", "proposed_band": 7.0, "summary": "ok", "evidence": []},
        "lexical": {"criterion": "LR", "proposed_band": 7.0, "summary": "ok", "evidence": []},
        "grammar": {"criterion": "GRA", "proposed_band": 7.0, "summary": "ok", "evidence": []},
    }
    verified = verify_specialist(
        analysis, sample["essay"], ("task_response", "coherence", "lexical", "grammar")
    )
    assert verified["quote_hit_rate"] >= 0.95
    for item in verified["task_response"]["evidence"]:
        assert quote_in_source(item["quote"], sample["essay"])


def test_grammar_reconciliation_caps_inflated_band() -> None:
    analysis = {
        "grammar": {
            "criterion": "Grammatical Range and Accuracy",
            "proposed_band": 8.0,
            "summary": "Mostly accurate.",
        }
    }
    issues = [{"span": "x"}] * 9
    updated = apply_grammar_reconciliation(analysis, issues)
    assert updated["grammar"]["proposed_band"] == 5.5
    assert updated["grammar"]["reconciled_from"] == 8.0


def test_tools_word_count_and_under_length() -> None:
    sample = GOLD_WRITING[4]
    tools = analyze_text(
        text=sample["essay"],
        skill="writing",
        module=sample["module"],
        task=sample["task"],
        prompt=sample["prompt"],
    )
    assert tools["word_count"] == word_count(sample["essay"])
    assert tools["under_length"] is True
    assert tools["expected_min_words"] == 150
    # "The chart shows …" is an overview marker; this sample is weak on development, not missing the phrase.


def test_letter_coverage_finds_bullets() -> None:
    sample = GOLD_WRITING[3]
    tools = analyze_text(
        text=sample["essay"],
        skill="writing",
        module="general",
        task="task1",
        prompt=sample["prompt"],
    )
    coverage = tools["task_coverage"]
    assert coverage["bullet_count"] >= 1
    assert coverage["coverage_ratio"] is not None
    assert coverage["coverage_ratio"] > 0


def test_filler_count() -> None:
    assert filler_count("I um think that uh it is like important") >= 2


def test_speaking_part2_coverage() -> None:
    prompt = (
        "Describe a skill you would like to learn.\n"
        "You should say:\n"
        "- what the skill is\n"
        "- why you want to learn it\n"
        "- how you would learn it\n"
        "- and explain how this skill would help you"
    )
    tools = analyze_text(
        text="I want to learn pottery because it is relaxing. I would take a class.",
        skill="speaking",
        module="academic",
        task="part2",
        prompt=prompt,
    )
    coverage = tools["task_coverage"]
    assert coverage is not None
    assert coverage["bullet_count"] >= 3
    assert coverage["coverage_ratio"] is not None
    assert coverage["coverage_ratio"] < 1


def test_mock_payloads_match_contracts() -> None:
    sample = "However, education is important. Therefore schools should improve."
    WritingAgentOutput.model_validate(mock_json_for_agent("writing", sample))
    SpeakingAgentOutput.model_validate(mock_json_for_agent("speaking", sample))
    GrammarAgentOutput.model_validate(mock_json_for_agent("grammar", sample))
    FeedbackAgentOutput.model_validate(mock_json_for_agent("feedback", sample))
    PerformanceAgentOutput.model_validate(mock_json_for_agent("performance", sample))
    RevisionAgentOutput.model_validate(mock_json_for_agent("revision", sample))
