from app.content.validators import ready_to_publish, validate_content_set, validate_question
from app.eval.gold_objective import GOLD_OBJECTIVE
from app.scoring.objective import grade_attempt, grade_item, normalize_answer
from app.scoring.raw_to_band import overall_ielts_band, raw_to_band, table_for_skill


def test_tfng_letter_aliases_match_keys():
    assert grade_item(qtype="tfng", student_answer="A", canonical="True")["correct"] is True
    assert grade_item(qtype="tfng", student_answer="B", canonical="False")["correct"] is True
    assert grade_item(qtype="tfng", student_answer="C", canonical="Not Given")["correct"] is True
    assert grade_item(qtype="tfng", student_answer="A", canonical="False")["correct"] is False
    assert grade_item(qtype="ynng", student_answer="A", canonical="Yes")["correct"] is True
    assert grade_item(qtype="ynng", student_answer="B", canonical="No")["correct"] is True
    assert grade_item(qtype="ynng", student_answer="True", canonical="Yes")["correct"] is False


def test_normalize_strips_articles_and_punct():
    assert normalize_answer("The Waggle-Dance!") == "waggle dance"
    assert normalize_answer("9 a.m.") == "9 am"
    assert normalize_answer("9am") == "9 am"


def test_gold_objective_marking():
    for case in GOLD_OBJECTIVE:
        if case["id"] == "multi-blank":
            good = grade_item(
                qtype="multi_blank",
                student_answer=case["answers"]["good"],
                canonical="",
                multi_blank=case["multi_blank"],
            )
            assert good["correct"] is True
            assert good["earned_marks"] == 2
            partial = grade_item(
                qtype="multi_blank",
                student_answer=case["answers"]["partial"],
                canonical="",
                multi_blank=case["multi_blank"],
            )
            assert partial["earned_marks"] == 1
            continue
        if case["id"] == "short-word-limit":
            over = grade_item(
                qtype="short_answer",
                student_answer=case["answers"]["over"],
                canonical=case["canonical"],
                variants=case["variants"],
                word_limit=case["word_limit"],
            )
            assert over["correct"] is False
            assert over["details"]["reason"] == "word_limit"
            good = grade_item(
                qtype=case["qtype"],
                student_answer=case["answers"]["good"],
                canonical=case["canonical"],
                variants=case.get("variants") or [],
                word_limit=case.get("word_limit"),
            )
            assert good["correct"] is True
            continue
        good = grade_item(
            qtype=case["qtype"],
            student_answer=case["answers"]["good"],
            canonical=case["canonical"],
            variants=case.get("variants") or [],
            word_limit=case.get("word_limit"),
        )
        assert good["correct"] is True, case["id"]
        if "also" in case["answers"]:
            also = grade_item(
                qtype=case["qtype"],
                student_answer=case["answers"]["also"],
                canonical=case["canonical"],
                variants=case.get("variants") or [],
            )
            assert also["correct"] is True
        bad = grade_item(
            qtype=case["qtype"],
            student_answer=case["answers"]["bad"],
            canonical=case["canonical"],
            variants=case.get("variants") or [],
            word_limit=case.get("word_limit"),
        )
        assert bad["correct"] is False, case["id"]


def test_matching_headings_roman_keys():
    assert grade_item(qtype="matching_headings", student_answer="ii", canonical="ii")["correct"] is True
    assert grade_item(qtype="matching_headings", student_answer="ii", canonical="iii")["correct"] is False


def test_grade_attempt_aggregates():
    questions = [
        {
            "id": "q1",
            "number": 1,
            "qtype": "mcq",
            "marks": 1,
            "answer_key": {"canonical": "B", "acceptable_variants": []},
        },
        {
            "id": "q2",
            "number": 2,
            "qtype": "tfng",
            "marks": 1,
            "answer_key": {"canonical": "True", "acceptable_variants": []},
        },
    ]
    result = grade_attempt(questions, {"q1": "B", "q2": "False"})
    assert result["earned_marks"] == 1
    assert result["max_marks"] == 2
    assert len(result["misses"]) == 1
    assert result["by_type"]["mcq"]["correct"] == 1


def test_raw_to_band_tables():
    assert raw_to_band(39, table_id="listening_v1") == 9.0
    assert raw_to_band(30, table_id="reading_academic_v1") == 7.0
    assert table_for_skill("listening", "academic") == "listening_v1"
    assert table_for_skill("reading", "general") == "reading_general_v1"


def test_raw_to_band_skips_drills():
    from app.scoring.raw_to_band import is_full_paper

    assert raw_to_band(6, table_id="reading_academic_v1", max_marks=6) is None
    assert raw_to_band(6, table_id="listening_v1", max_marks=4) is None
    assert is_full_paper(6) is False
    assert is_full_paper(40) is True
    assert raw_to_band(30, table_id="reading_academic_v1", max_marks=40) == 7.0


def test_overall_ielts_band_confidence():
    full = overall_ielts_band({"listening": 6.5, "reading": 7.0, "writing": 6.0, "speaking": 6.5})
    assert full["overall_band"] == 6.5
    assert full["confidence"] == 1.0
    assert full["missing_skills"] == []
    partial = overall_ielts_band({"listening": 6.5, "reading": 7.0})
    assert partial["estimated"] is True
    assert partial["confidence"] == 0.5
    assert "writing" in partial["missing_skills"]
    single = overall_ielts_band({"listening": 6.5})
    assert single["overall_band"] is None


def test_content_validators():
    bad = validate_question({"qtype": "mcq", "stem": "x", "canonical": ""})
    assert bad
    good_set = {
        "skill": "reading",
        "module": "academic",
        "title": "Bees",
        "passages": [{"body": "text"}],
        "questions": [
            {
                "qtype": "tfng",
                "stem": "A colony always contains many queens.",
                "canonical": "False",
                "options": {"choices": ["True", "False", "Not Given"]},
            }
        ],
    }
    assert validate_content_set(good_set) == []
    assert ready_to_publish(good_set) is True
    heading = validate_question(
        {
            "qtype": "matching_headings",
            "stem": "Paragraph A",
            "canonical": "ii",
            "options": {"choices": ["i One", "ii Two", "iii Three"]},
        }
    )
    assert heading == []
