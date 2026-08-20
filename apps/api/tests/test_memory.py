from app.agents.memory import empty_profile, update_coach_profile


def test_profile_ewma_and_patterns() -> None:
    profile = update_coach_profile(
        empty_profile(),
        recurring_patterns=["article use"],
        next_focus="lexical",
        criteria=[{"criterion": "Lexical Resource", "band": 6.0}],
    )
    profile = update_coach_profile(
        profile,
        recurring_patterns=["tense consistency", "article use"],
        next_focus="grammar",
        criteria=[{"criterion": "Lexical Resource", "band": 7.0}],
    )
    assert profile["last_next_focus"] == "grammar"
    assert profile["attempt_count"] == 2
    assert "article use" in profile["weak_patterns"]
    assert profile["criterion_ewma"]["Lexical Resource"] == 6.4


def test_skill_ewma_for_objective() -> None:
    profile = update_coach_profile(
        empty_profile(),
        recurring_patterns=["tfng"],
        next_focus="tfng",
        criteria=[{"criterion": "Objective accuracy", "band": 6.0}],
        skill="reading",
        skill_band=6.0,
    )
    profile = update_coach_profile(
        profile,
        recurring_patterns=[],
        next_focus="mcq",
        criteria=[{"criterion": "Objective accuracy", "band": 7.0}],
        skill="reading",
        skill_band=7.0,
    )
    assert profile["skill_ewma"]["reading"] == 6.4
