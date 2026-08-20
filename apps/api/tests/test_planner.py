from app.agents.analysis_cache import clear, get, make_key, put
from app.agents.graph import _after_plan, _after_tools, build_graph
from app.agents.planner import MIN_GRAMMAR_WORDS, MIN_PERFORMANCE_HISTORY, build_plan, skip_reason
from app.llm.router import CHEAP_AGENTS, resolve_provider


def test_plan_skips_performance_without_history() -> None:
    plan = build_plan(skill="writing", tools={"word_count": 260}, history=[], cache_hit=False)
    assert plan["run_specialist"] is True
    assert plan["run_grammar"] is True
    assert plan["run_feedback"] is True
    assert plan["run_performance"] is False
    assert skip_reason(plan, "performance") == "history_too_short"


def test_plan_skips_grammar_on_short_text() -> None:
    plan = build_plan(
        skill="speaking",
        tools={"word_count": MIN_GRAMMAR_WORDS - 1},
        history=[{"overall_band": 6}] * MIN_PERFORMANCE_HISTORY,
        cache_hit=False,
    )
    assert plan["run_grammar"] is False
    assert plan["run_performance"] is True
    assert skip_reason(plan, "grammar") == "response_too_short"


def test_plan_skips_specialists_on_cache_hit() -> None:
    plan = build_plan(
        skill="writing",
        tools={"word_count": 280},
        history=[{"overall_band": 6}, {"overall_band": 6.5}],
        cache_hit=True,
        cache_key="abc",
    )
    assert plan["use_cache"] is True
    assert plan["run_specialist"] is False
    assert plan["run_grammar"] is False
    assert plan["run_performance"] is True
    assert skip_reason(plan, "writing") == "identical_input_cache"
    assert skip_reason(plan, "grammar") == "identical_input_cache"


def test_analysis_cache_roundtrip() -> None:
    clear()
    key = make_key("writing", "academic", "task2", "prompt", "same essay text")
    assert get(key) is None
    put(key, {"writing_analysis": {"task_response": {"proposed_band": 6.0}}})
    hit = get(key)
    assert hit is not None
    assert hit["writing_analysis"]["task_response"]["proposed_band"] == 6.0
    other = make_key("writing", "academic", "task2", "prompt", "different essay")
    assert get(other) is None
    clear()
    assert get(key) is None


def test_graph_routes_tools_to_plan() -> None:
    assert _after_tools({"skill": "writing"}) == "plan"
    assert _after_tools({"error": "nope"}) == "persist"
    assert _after_plan({"skill": "writing"}) == "analyze_writing"
    assert _after_plan({"skill": "speaking"}) == "analyze_speaking"
    graph = build_graph()
    assert graph is not None


def test_cheap_agents_listed() -> None:
    assert {"grammar", "performance", "explain"} <= CHEAP_AGENTS
    resolved = resolve_provider("writing")
    assert resolved.provider
    assert resolved.model


def test_cheap_agent_uses_llm_cheap_model(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "agent_grammar", "")
    monkeypatch.setattr(settings, "agent_writing", "")
    monkeypatch.setattr(settings, "llm_default_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_default_model", "openai/gpt-4o-mini")
    monkeypatch.setattr(settings, "llm_cheap_provider", "gemini")
    monkeypatch.setattr(settings, "llm_cheap_model", "gemini-2.0-flash")
    cheap = resolve_provider("grammar")
    writing = resolve_provider("writing")
    assert cheap.provider == "gemini"
    assert cheap.model == "gemini-2.0-flash"
    assert writing.provider == "openrouter"
    assert writing.model == "openai/gpt-4o-mini"
