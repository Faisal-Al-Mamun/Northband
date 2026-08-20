from app.eval.gold_set import GOLD_SPEAKING, GOLD_WRITING
from app.eval.offline import run_offline_eval
from app.agents.verify import quote_in_source


def test_offline_eval_meets_quality_gates() -> None:
    summary = run_offline_eval()
    assert summary["samples"] == len(GOLD_WRITING) + len(GOLD_SPEAKING)
    assert summary["schema_valid_rate"] == 1.0
    assert summary["mean_quote_hit_rate"] >= 0.95
    assert summary["min_quote_hit_rate"] >= 0.95
    assert summary["invented_quotes_dropped_rate"] == 1.0
    assert summary["must_quotes_present_rate"] == 1.0
    for row in summary["rows"]:
        assert row["schema_valid"] is True
        assert row["all_quotes_in_source"] is True
        assert row["invented_quote_dropped"] is True


def test_speaking_gold_quotes_exist() -> None:
    for sample in GOLD_SPEAKING:
        for quote in sample["must_quotes"]:
            assert quote_in_source(quote, sample["transcript"]), sample["id"]
