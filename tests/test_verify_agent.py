import pytest
from unittest.mock import patch
from agents.verify_agent import VerifyAgent


def test_verify_agent_passes_valid_cv(sample_cv, mock_interaction):
    agent = VerifyAgent()
    mock_json = '{"valid": true, "reason": "All clear. Facts align with Master CV."}'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)) as mock_create:
        is_valid, reason = agent.verify(sample_cv, sample_cv)
        assert is_valid is True
        assert "verified successfully" in reason

        _, kwargs = mock_create.call_args
        assert sample_cv in kwargs["input"]
        assert kwargs["generation_config"] == {"thinking_level": "low"}


def test_verify_agent_rejects_hallucination(sample_cv, mock_interaction):
    agent = VerifyAgent()
    hallucinated_cv = sample_cv + "\n- Invented PhD in Quantum Physics from MIT"
    mock_json = '{"valid": false, "reason": "Candidate has no PhD in Quantum Physics in Master CV."}'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)) as mock_create:
        is_valid, reason = agent.verify(sample_cv, hallucinated_cv)
        assert is_valid is False
        assert "Candidate has no PhD" in reason
        mock_create.assert_called_once()


def test_verify_agent_llm_rejects_subtle_data_loss_when_contacts_intact(sample_cv, mock_interaction):
    agent = VerifyAgent()
    # Contacts (email) remain intact so deterministic gate passes and LLM step is reached
    cv_missing_phone = sample_cv.replace("+1234567890", "")
    mock_json = '```json\n{"valid": false, "reason": "Phone number was removed from tailored CV."}\n```'

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)) as mock_create:
        is_valid, reason = agent.verify(sample_cv, cv_missing_phone)
        assert is_valid is False
        assert "Phone number was removed" in reason
        mock_create.assert_called_once()


def test_verify_agent_api_error_failsafe(sample_cv):
    agent = VerifyAgent()

    with patch.object(agent.client.interactions, "create", side_effect=Exception("Network error")):
        is_valid, reason = agent.verify(sample_cv, sample_cv)
        assert is_valid is False
        assert "VerifyAgent parsing error" in reason


def test_verify_agent_deterministic_gate_aborts_without_llm(sample_cv):
    agent = VerifyAgent()
    cv_with_dropped_email = sample_cv.replace("jane.doe@example.com", "")

    with patch.object(agent.client.interactions, "create") as mock_create:
        is_valid, reason = agent.verify(sample_cv, cv_with_dropped_email)
        assert is_valid is False
        assert "DETERMINISTIC GATE" in reason
        assert "jane.doe@example.com" in reason
        mock_create.assert_not_called()


def test_verify_agent_deterministic_gate_rejects_dropped_portfolio_link(sample_cv):
    agent = VerifyAgent()
    cv_with_links = sample_cv + "\nPortfolio: https://github.com/Lightoton | https://www.linkedin.com/in/jane-doe"
    cv_missing_github = sample_cv + "\nPortfolio: https://www.linkedin.com/in/jane-doe"

    with patch.object(agent.client.interactions, "create") as mock_create:
        is_valid, reason = agent.verify(cv_with_links, cv_missing_github)
        assert is_valid is False
        assert "DETERMINISTIC GATE" in reason
        assert "github.com/Lightoton" in reason
        mock_create.assert_not_called()
