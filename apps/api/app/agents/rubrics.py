"""Public-style IELTS band descriptors, compacted for specialist prompts."""

from __future__ import annotations

WRITING_TASK_RESPONSE = """
Task Response / Task Achievement (0.5 steps):
5: Addresses the task only partially; format may be inappropriate; position unclear; ideas limited and repetitive.
6: Addresses all parts though some are more fully covered; relevant position; ideas are generally extended but may be unclear in places.
7: Addresses all parts; clear position throughout; ideas extended, supported, and generally relevant; Academic T1 has a clear overview.
8: All parts fully and appropriately addressed; well-developed, relevant ideas; Academic T1 selects and groups key features with a clear overview; GT T1 covers purpose, tone, and all bullets.
""".strip()

WRITING_COHERENCE = """
Coherence and Cohesion:
5: Inadequate organisation; linking is mechanical or inaccurate; paragraphing may be missing.
6: Information is arranged coherently; linking is used but may be repetitive or faulty; paragraphing is generally logical.
7: Logical organisation; a range of cohesive devices used with some flexibility; each paragraph has a clear central topic.
8: Sequences information and ideas logically; manages cohesion well; paragraphing is sufficient and appropriate.
""".strip()

WRITING_LEXICAL = """
Lexical Resource:
5: Limited vocabulary; noticeable repetition; errors that may cause difficulty for the reader.
6: Adequate range for the task; attempts less common words with some inaccuracy; spelling/word-choice errors do not impede communication.
7: Sufficient range; some less common and idiomatic items; awareness of style and collocation with occasional errors.
8: Wide range used fluently and flexibly; skillful collocation; rare errors, usually slips.
""".strip()

WRITING_GRAMMAR = """
Grammatical Range and Accuracy:
5: Limited range; frequent errors; meaning may be unclear.
6: Mix of simple and complex forms; errors occur but rarely reduce communication.
7: A variety of complex structures; frequent error-free sentences; good control with a few mistakes.
8: Wide range of structures; the majority of sentences are error-free; only very occasional slips.
""".strip()

SPEAKING_FLUENCY = """
Fluency and Coherence:
5: Speech is slow; frequent self-correction; overuse of connectives; can talk but with difficulty.
6: Willing to speak at length; occasional hesitation and self-correction; generally coherent.
7: Speaks at length without noticeable effort; some hesitation for language but ideas flow; a range of connectives.
8: Fluent with only occasional hesitation; develops topics coherently and appropriately.
""".strip()

SPEAKING_LEXICAL = """
Lexical Resource (speaking):
5: Vocabulary talks about familiar topics but is limited; errors and circumlocution.
6: Wide enough for lengthy discussion; some unclear or repetitive wording.
7: Flexible use; some less common and idiomatic vocabulary; paraphrase effective.
8: Wide vocabulary, precise meaning, natural collocation; paraphrase effective as needed.
""".strip()

SPEAKING_GRAMMAR = """
Grammatical Range and Accuracy (speaking):
5: Basic sentences with limited complexity; frequent errors; meaning sometimes unclear.
6: Mix of simple and complex; errors occur but rarely impede communication.
7: A range of structures with some flexibility; frequently error-free.
8: Wide range used with flexibility; most sentences error-free.
""".strip()

SPEAKING_PRONUNCIATION = """
Pronunciation:
5: Mispronunciations are frequent; the listener often has to adjust.
6: Can be understood throughout; mispronunciation of individual words or sounds reduces clarity at times.
7: Easy to understand; some L1 influence; positive features of chunking, stress, and intonation.
8: Easy to understand throughout; flexible use of features; L1 influence minimally affects intelligibility.
If input is text-only, treat this as a proxy from spelling, self-corrections, and phonetic difficulty — say so, and do not claim acoustic evidence.
""".strip()

TASK_NOTES = """
Academic Task 1: describe data/process/map without personal opinion; a clear overview of main trends is required; do not invent numbers not in the visual.
General Training Task 1: letter must show purpose early, appropriate tone (formal/semi/informal), and cover every bullet.
Task 2: clear position, developed arguments with examples, cohesive paragraphs, conclusion that matches the position.
Speaking Part 1: concise familiar answers with extension. Part 2: long turn that covers cue bullets without memorised essays. Part 3: abstract discussion with justification.
Exam ceilings examiners apply in practice: under-length Task 1/2 rarely reaches 7 on TR/TA; missing Academic overview usually caps TA; unanswered bullets cap GT letter TA.
""".strip()


def writing_rubric_block() -> str:
    return "\n\n".join(
        [TASK_NOTES, WRITING_TASK_RESPONSE, WRITING_COHERENCE, WRITING_LEXICAL, WRITING_GRAMMAR]
    )


def speaking_rubric_block() -> str:
    return "\n\n".join(
        [TASK_NOTES, SPEAKING_FLUENCY, SPEAKING_LEXICAL, SPEAKING_GRAMMAR, SPEAKING_PRONUNCIATION]
    )
