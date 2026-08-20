from app.llm.mock_responses import mock_json_for_agent
from app.schemas.agents import (
    CoachStepOutput,
    FeedbackAgentOutput,
    GrammarAgentOutput,
    PerformanceAgentOutput,
    SpeakingAgentOutput,
    WritingAgentOutput,
)


def test_mock_payloads_match_contracts() -> None:
    sample = "However, education is important. Therefore schools should improve."
    WritingAgentOutput.model_validate(mock_json_for_agent("writing", sample))
    SpeakingAgentOutput.model_validate(mock_json_for_agent("speaking", sample))
    GrammarAgentOutput.model_validate(mock_json_for_agent("grammar", sample))
    FeedbackAgentOutput.model_validate(mock_json_for_agent("feedback", sample))
    PerformanceAgentOutput.model_validate(mock_json_for_agent("performance", sample))
    CoachStepOutput.model_validate(mock_json_for_agent("coach", "LAST_ACTION: none"))
