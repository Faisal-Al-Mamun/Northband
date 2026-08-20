from app.agents.coach_tools import inspect_item, list_misses, quote_context, run_coach_tool
from app.agents.objective_graph import build_objective_graph
from app.llm.mock_responses import mock_json_for_agent
from app.schemas.agents import CoachStepOutput, FeedbackAgentOutput


def test_objective_graph_compiles():
    graph = build_objective_graph()
    assert graph is not None


def test_quote_context_finds_span():
    source = "Please wait at Door B, not the main hall. The fee is fifteen pounds today."
    snippet = quote_context(source, "door hall")
    assert "Door B" in snippet


def test_list_and_inspect_tools():
    misses = [
        {
            "question_id": "q1",
            "number": 1,
            "qtype": "mcq",
            "stem": "Where should Mina meet the driver?",
            "given": "A",
            "canonical": "B",
            "skill_tags": ["mcq"],
        }
    ]
    listed = list_misses(misses)
    assert "q1" in listed
    inspected = inspect_item("q1", [], misses)
    assert "Door" in inspected or "driver" in inspected.lower()
    quoted = run_coach_tool(
        "quote_context",
        question_id="q1",
        questions=[],
        misses=misses,
        context="Meet the driver at Door B, not the main hall.",
    )
    assert "Door B" in quoted


def test_mock_coach_and_feedback_contracts():
    first = CoachStepOutput.model_validate(
        mock_json_for_agent("coach", "STEP: 0\nLAST_ACTION: none\nMISSES:\nid=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    )
    assert first.action == "list_misses"
    FeedbackAgentOutput.model_validate(mock_json_for_agent("feedback", "objective attempt"))
