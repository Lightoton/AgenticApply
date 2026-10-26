import pytest
from unittest.mock import patch
from agents.evaluator_agent import EvaluatorAgent, EvaluationResult
from core.config import config


def test_evaluator_proceed_threshold(sample_cv, sample_jd_good, mock_interaction):
    agent = EvaluatorAgent()
    mock_json = '{"score": 82, "reasoning": "Strong match on Python and Docker.", "decision": "PROCEED", "company_name": "TechCorp", "role_title": "Python Developer"}'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)) as mock_create:
        result = agent.evaluate(sample_cv, sample_jd_good)

        assert isinstance(result, EvaluationResult)
        assert result.score == 82
        assert result.decision == "PROCEED"
        assert result.company_name == "TechCorp"
        assert result.role_title == "Python Developer"
        assert "Strong match" in result.reasoning

        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        prompt_sent = kwargs["input"]
        assert sample_cv in prompt_sent
        assert sample_jd_good in prompt_sent
        assert config.TARGET_LOCATION in prompt_sent
        assert config.CANDIDATE_LANGUAGES in prompt_sent
        assert "Kollektivvertrag" in prompt_sent
        assert kwargs["generation_config"] == {"thinking_level": "high"}


def test_evaluator_reject_threshold(sample_cv, sample_jd_bad, mock_interaction):
    agent = EvaluatorAgent()
    mock_json = '{"score": 25, "reasoning": "Severe seniority and location mismatch.", "decision": "REJECT", "company_name": "NY Firm"}'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)):
        result = agent.evaluate(sample_cv, sample_jd_bad)

        assert result.score == 25
        assert result.decision == "REJECT"


def test_evaluator_markdown_json_wrapper(sample_cv, sample_jd_good, mock_interaction):
    agent = EvaluatorAgent()
    wrapped_json = '```json\n{"score": 77, "reasoning": "Good fit.", "decision": "PROCEED", "company_name": "CloudCo"}\n```'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(wrapped_json)):
        result = agent.evaluate(sample_cv, sample_jd_good)
        assert result.score == 77
        assert result.decision == "PROCEED"


def test_evaluator_api_error_fallback(sample_cv, sample_jd_good):
    agent = EvaluatorAgent()

    with patch.object(agent.client.interactions, "create", side_effect=Exception("API connection timeout")):
        result = agent.evaluate(sample_cv, sample_jd_good)

        assert result.score == 0
        assert result.decision == "REJECT"
        assert result.company_name == "Unknown"
        assert "API Error" in result.reasoning
