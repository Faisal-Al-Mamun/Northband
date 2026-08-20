from app.agents.exam_rules import apply_exam_ceilings, examiner_first_impression


def test_under_length_caps_task_response():
    criteria = [
        {"criterion": "Task Response", "band": 7.5, "rationale": "ok"},
        {"criterion": "Coherence and Cohesion", "band": 7.0, "rationale": "ok"},
    ]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="writing",
        module="academic",
        task="task2",
        tools={"under_length": True, "word_count": 180, "expected_min_words": 250},
    )
    assert updated[0]["band"] == 6.0
    assert warnings
    assert "under minimum length" in warnings[0]


def test_missing_overview_caps_academic_task1():
    criteria = [{"criterion": "Task Achievement", "band": 7.0, "rationale": "clear"}]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="writing",
        module="academic",
        task="task1",
        tools={"overview_present": False, "word_count": 160, "expected_min_words": 150},
    )
    assert updated[0]["band"] == 6.0
    assert any("overview" in w for w in warnings)


def test_first_impression_mentions_length():
    note = examiner_first_impression(
        {"word_count": 120, "expected_min_words": 250, "under_length": True},
        "writing",
        "task2",
    )
    assert "Length" in note


def test_short_part2_caps_fluency():
    criteria = [
        {"criterion": "Fluency and Coherence", "band": 7.0, "rationale": "ok"},
        {"criterion": "Lexical Resource", "band": 7.0, "rationale": "ok"},
    ]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="speaking",
        module="academic",
        task="part2",
        tools={"duration_seconds": 18, "words_per_minute": 110},
    )
    assert updated[0]["band"] == 4.0
    assert any("too short" in item for item in warnings)
    assert updated[1]["band"] == 7.0


def test_part2_missed_cue_caps_fluency():
    criteria = [{"criterion": "Fluency and Coherence", "band": 7.5, "rationale": "ok"}]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="speaking",
        module="academic",
        task="part2",
        tools={
            "duration_seconds": 90,
            "task_coverage": {"coverage_ratio": 0.25, "missing": ["why you want to learn it"]},
        },
    )
    assert updated[0]["band"] == 6.0
    assert any("cue-card" in item for item in warnings)


def test_speaking_first_impression_flags_short_turn():
    note = examiner_first_impression(
        {"duration_seconds": 30, "task_coverage": {"missing": ["how you would learn it"]}},
        "speaking",
        "part2",
    )
    assert "Part 2" in note
    assert "how you would learn it" in note


def test_full_interview_caps_fluency():
    criteria = [{"criterion": "Fluency and Coherence", "band": 7.5, "rationale": "ok"}]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="speaking",
        module="academic",
        task="full",
        tools={"duration_seconds": 120, "words_per_minute": 120},
    )
    assert updated[0]["band"] == 4.0
    assert any("full interview too short" in item for item in warnings)


def test_full_interview_cue_coverage_cap():
    criteria = [{"criterion": "Fluency and Coherence", "band": 7.5, "rationale": "ok"}]
    updated, warnings = apply_exam_ceilings(
        criteria,
        skill="speaking",
        module="academic",
        task="full",
        tools={
            "duration_seconds": 700,
            "task_coverage": {"coverage_ratio": 0.2, "missing": ["why you want to learn it"]},
        },
    )
    assert updated[0]["band"] == 6.0
    assert any("cue-card" in item for item in warnings)
