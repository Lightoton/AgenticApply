import pytest
from unittest.mock import patch
from agents.verify_agent import VerifyAgent

def test_verify_agent_passes_valid_cv(sample_cv, mock_interaction):
    agent = VerifyAgent()
    mock_json = '{"valid": true, "reason": "All clear. Facts align with Master CV."}'
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)) as mock_create:
        is_valid = agent.verify(sample_cv, sample_cv)
        assert is_valid is True

        _, kwargs = mock_create.call_args
        assert kwargs["generation_config"] == {"thinking_level": "low"}

def test_verify_agent_rejects_hallucination(sample_cv, mock_interaction):
    agent = VerifyAgent()
    hallucinated_cv = sample_cv + "\n- Invented PhD in Quantum Physics from MIT"
    mock_json = '{"valid": false, "reason": "Candidate has no PhD in Quantum Physics in Master CV."}'
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)):
        is_valid = agent.verify(sample_cv, hallucinated_cv)
        assert is_valid is False

def test_verify_agent_rejects_lost_contact(sample_cv, mock_interaction):
    agent = VerifyAgent()
    cv_without_email = sample_cv.replace("jane.doe@example.com", "")
    mock_json = '{"valid": false, "reason": "Candidate contact email was removed."}'
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_json)):
        is_valid = agent.verify(sample_cv, cv_without_email)
        assert is_valid is False

def test_verify_agent_api_error_failsafe(sample_cv):
    agent = VerifyAgent()
    
    with patch.object(agent.client.interactions, "create", side_effect=Exception("Network error")):
        is_valid = agent.verify(sample_cv, sample_cv)
        # Fail-safe: returns False to prevent sending unverified documents
        assert is_valid is False
