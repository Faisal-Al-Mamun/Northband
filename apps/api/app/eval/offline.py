"""Offline eval: schema validity + quote integrity with no live LLM keys.

Runs heuristic mock specialists against the gold set, then the same verifier
the production graph uses. Hiring managers can run this without API keys:

    python -m app.eval.offline
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.verify import quote_in_source, verify_specialist
from app.eval.gold_set import GOLD_SPEAKING, GOLD_WRITING
from app.llm.mock_responses import mock_json_for_agent
from app.schemas.agents import GrammarAgentOutput, SpeakingAgentOutput, WritingAgentOutput

WRITING_KEYS = ("task_response", "coherence", "lexical", "grammar")
SPEAKING_KEYS = ("fluency", "lexical", "grammar", "pronunciation")


def _quotes_from_analysis(analysis: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    quotes: list[str] = []
    for key in keys:
        block = analysis.get(key) or {}
        for item in block.get("evidence") or []:
            quote = str(item.get("quote") or "").strip()
            if quote:
                quotes.append(quote)
    return quotes


def _eval_sample(
    *,
    sample: dict[str, Any],
    agent: str,
    schema: type,
    keys: tuple[str, ...],
    source_field: str,
) -> dict[str, Any]:
    source = sample[source_field]
    raw = mock_json_for_agent(agent, source)
    parsed = schema.model_validate(raw)
    analysis = parsed.model_dump()
    verified = verify_specialist(analysis, source, keys)
    quotes = _quotes_from_analysis(verified, keys)
    invented = verify_specialist(
        {
            **analysis,
            keys[0]: {
                **(analysis.get(keys[0]) or {}),
                "evidence": list((analysis.get(keys[0]) or {}).get("evidence") or [])
                + [{"quote": "this invented span is not in the source xyz", "comment": "fake"}],
            },
        },
        source,
        keys,
    )
    return {
        "id": sample["id"],
        "skill": "speaking" if agent == "speaking" else "writing",
        "schema_valid": True,
        "quote_hit_rate": verified.get("quote_hit_rate"),
        "quotes_kept": verified.get("evidence_quote_kept"),
        "quotes_dropped": verified.get("evidence_quote_dropped"),
        "all_quotes_in_source": all(quote_in_source(q, source) for q in quotes) if quotes else True,
        "must_quotes_present": all(quote_in_source(q, source) for q in sample.get("must_quotes") or []),
        "invented_quote_dropped": int(invented.get("evidence_quote_dropped") or 0) > int(
            verified.get("evidence_quote_dropped") or 0
        ),
        "grammar_schema_valid": True,
    }


def run_offline_eval() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for sample in GOLD_WRITING:
        GrammarAgentOutput.model_validate(mock_json_for_agent("grammar", sample["essay"]))
        rows.append(
            _eval_sample(
                sample=sample,
                agent="writing",
                schema=WritingAgentOutput,
                keys=WRITING_KEYS,
                source_field="essay",
            )
        )
    for sample in GOLD_SPEAKING:
        GrammarAgentOutput.model_validate(mock_json_for_agent("grammar", sample["transcript"]))
        rows.append(
            _eval_sample(
                sample=sample,
                agent="speaking",
                schema=SpeakingAgentOutput,
                keys=SPEAKING_KEYS,
                source_field="transcript",
            )
        )

    hit_rates = [float(row["quote_hit_rate"]) for row in rows if row.get("quote_hit_rate") is not None]
    return {
        "samples": len(rows),
        "schema_valid_rate": 1.0 if rows and all(row["schema_valid"] for row in rows) else 0.0,
        "mean_quote_hit_rate": round(sum(hit_rates) / len(hit_rates), 4) if hit_rates else 0.0,
        "min_quote_hit_rate": min(hit_rates) if hit_rates else 0.0,
        "invented_quotes_dropped_rate": (
            sum(1 for row in rows if row["invented_quote_dropped"]) / len(rows) if rows else 0.0
        ),
        "must_quotes_present_rate": (
            sum(1 for row in rows if row["must_quotes_present"]) / len(rows) if rows else 0.0
        ),
        "rows": rows,
    }


def main() -> None:
    summary = run_offline_eval()
    printable = {key: value for key, value in summary.items() if key != "rows"}
    printable["ids"] = [row["id"] for row in summary["rows"]]
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
