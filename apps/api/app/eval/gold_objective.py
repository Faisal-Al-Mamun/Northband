"""Deterministic grader gold cases — 100% mark accuracy required."""

from __future__ import annotations

GOLD_OBJECTIVE: list[dict] = [
    {
        "id": "mcq-exact",
        "qtype": "mcq",
        "canonical": "B",
        "variants": ["b"],
        "answers": {"good": "B", "also": "b", "bad": "A"},
    },
    {
        "id": "tfng-false",
        "qtype": "tfng",
        "canonical": "False",
        "variants": [],
        "answers": {"good": "False", "bad": "True"},
    },
    {
        "id": "completion-article",
        "qtype": "completion",
        "canonical": "waggle dance",
        "variants": ["the waggle dance"],
        "answers": {"good": "The waggle dance", "bad": "queen bee"},
    },
    {
        "id": "short-word-limit",
        "qtype": "short_answer",
        "canonical": "main gate",
        "variants": ["the main gate"],
        "word_limit": 2,
        "answers": {"good": "main gate", "over": "the campus main gate"},
    },
    {
        "id": "multi-blank",
        "qtype": "multi_blank",
        "canonical": "",
        "multi_blank": {
            "blanks": [
                {"id": "1", "canonical": "library", "variants": [], "marks": 1},
                {"id": "2", "canonical": "9 am", "variants": ["9am", "9 a.m."], "marks": 1},
            ]
        },
        "answers": {
            "good": {"1": "library", "2": "9 a.m."},
            "partial": {"1": "library", "2": "noon"},
        },
    },
]
