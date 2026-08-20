from app.content.listening_bank import CAMPUS_S1, CAMPUS_QUESTIONS
from app.services.tts import parse_script, pocket_voice_for, script_fingerprint


def test_parse_script_splits_speakers():
    turns = parse_script(CAMPUS_S1)
    roles = {role for role, _text in turns}
    assert "Narrator" in roles
    assert "Advisor" in roles
    assert "Student" in roles
    assert all(text.strip() for _role, text in turns)
    spoken = " ".join(text for _role, text in turns)
    assert "M724" in spoken or "seven two four" in spoken.lower()
    assert "Door B" in spoken or "door B" in spoken.lower()


def test_plain_text_becomes_narrator():
    turns = parse_script("Please wait at door B.")
    assert turns == [("Narrator", "Please wait at door B.")]


def test_voice_map_and_fingerprint_are_stable():
    assert pocket_voice_for("Advisor") == "alba"
    assert pocket_voice_for("Student") == "jean"
    first = script_fingerprint("hello", "en-GB")
    second = script_fingerprint("hello", "en-GB")
    assert first == second
    assert first != script_fingerprint("hello", "en-AU")


def test_campus_paper_has_forty_questions():
    assert len(CAMPUS_QUESTIONS) == 40
    numbers = [item["number"] for item in CAMPUS_QUESTIONS]
    assert numbers == list(range(1, 41))
