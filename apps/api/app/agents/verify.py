from __future__ import annotations

import re
from typing import Any

from app.scoring.bands import round_half_band

_WS = re.compile(r"\s+")


def _norm(value: str) -> str:
    return _WS.sub(" ", (value or "").lower()).strip()


def quote_in_source(quote: str, source: str) -> bool:
    q = _norm(quote)
    if len(q) < 4:
        return False
    body = _norm(source)
    if q in body:
        return True
    # allow a slightly shortened span
    if len(q) > 24 and q[:24] in body:
        return True
    return False


def filter_evidence(evidence: list[dict[str, Any]] | None, source: str) -> tuple[list[dict[str, Any]], int, int]:
    kept: list[dict[str, Any]] = []
    dropped = 0
    total = 0
    for item in evidence or []:
        quote = str(item.get("quote") or "")
        if not quote.strip():
            continue
        total += 1
        if quote_in_source(quote, source):
            kept.append(item)
        else:
            dropped += 1
    return kept, total, dropped


def verify_criterion_block(block: dict[str, Any] | None, source: str) -> dict[str, Any]:
    payload = dict(block or {})
    evidence, total, dropped = filter_evidence(payload.get("evidence") or [], source)
    payload["evidence"] = evidence
    payload["evidence_dropped"] = dropped
    payload["evidence_total"] = total
    return payload


def verify_specialist(analysis: dict[str, Any] | None, source: str, keys: tuple[str, ...]) -> dict[str, Any]:
    payload = dict(analysis or {})
    dropped_all = 0
    total_all = 0
    for key in keys:
        item = verify_criterion_block(payload.get(key) if isinstance(payload.get(key), dict) else {}, source)
        payload[key] = item
        dropped_all += int(item.get("evidence_dropped") or 0)
        total_all += int(item.get("evidence_total") or 0)
    payload["evidence_quote_total"] = total_all
    payload["evidence_quote_dropped"] = dropped_all
    payload["evidence_quote_kept"] = total_all - dropped_all
    payload["quote_hit_rate"] = (1.0 if total_all == 0 else (total_all - dropped_all) / total_all)
    return payload


def reconcile_grammar_band(proposed: float, issue_count: int) -> float:
    if issue_count >= 12:
        cap = 5.0
    elif issue_count >= 8:
        cap = 5.5
    elif issue_count >= 5:
        cap = 6.0
    elif issue_count >= 3:
        cap = 6.5
    else:
        cap = 9.0
    return round_half_band(min(float(proposed or 0), cap))


def apply_grammar_reconciliation(
    analysis: dict[str, Any] | None,
    issues: list[dict[str, Any]] | None,
    *,
    grammar_key: str = "grammar",
) -> dict[str, Any]:
    payload = dict(analysis or {})
    block = dict(payload.get(grammar_key) or {})
    proposed = float(block.get("proposed_band") or 0)
    count = len(issues or [])
    reconciled = reconcile_grammar_band(proposed, count)
    if reconciled < proposed:
        note = (
            f" Band reduced from {proposed} to {reconciled} after {count} language issues "
            "found by the grammar agent."
        )
        block["summary"] = ((block.get("summary") or "") + note).strip()
        block["proposed_band"] = reconciled
        block["reconciled_from"] = proposed
    payload[grammar_key] = block
    return payload


def quote_hit_rate(analysis: dict[str, Any] | None) -> float:
    if not analysis:
        return 1.0
    total = int(analysis.get("evidence_quote_total") or 0)
    kept = int(analysis.get("evidence_quote_kept") or 0)
    if total == 0:
        return 1.0
    return kept / total
