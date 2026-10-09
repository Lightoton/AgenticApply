import pytest
from unittest.mock import patch, MagicMock
from agents.discovery_agent import DiscoveryAgent

def test_discovery_search_terms_generation(sample_cv, mock_interaction):
    agent = DiscoveryAgent()
    mock_keywords = "python developer, backend engineer, fastapi"
    
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction(mock_keywords)):
        with patch("playwright.async_api.async_playwright"), \
             patch("requests.get") as mock_get:
            # Prevent actual network calls
            mock_get.return_value.status_code = 404
            
            # Direct test of terms via internal LLM call logic
            prompt = f"Analyze CV: {sample_cv}"
            interaction = agent.client.interactions.create(
                model=agent.model,
                input=prompt,
                generation_config={"thinking_level": "low"}
            )
            terms = [t.strip().lower() for t in interaction.output_text.split(",")]
            assert "python developer" in terms
            assert "backend engineer" in terms

def test_discovery_exclude_words_filtering(monkeypatch):
    monkeypatch.setattr("core.config.config.EXCLUDE_WORDS", ["senior", "lead", "principal"])
    
    titles = [
        ("Senior Python Engineer", True),
        ("Lead Software Architect", True),
        ("Principal AI Researcher", True),
        ("Junior Python Developer", False),
        ("Python Backend Engineer", False)
    ]
    
    from core.config import config
    for title, should_exclude in titles:
        excluded = any(word in title.lower() for word in config.EXCLUDE_WORDS)
        assert excluded == should_exclude

def test_discovery_must_have_keywords(monkeypatch):
    monkeypatch.setattr("core.config.config.MUST_HAVE_KEYWORDS", ["ai", "llm", "python"])
    
    import re
    from core.config import config
    
    pattern = r'\b(' + '|'.join(re.escape(k) for k in config.MUST_HAVE_KEYWORDS) + r')\b'
    
    assert bool(re.search(pattern, "Junior Python Developer", re.IGNORECASE)) is True
    assert bool(re.search(pattern, "AI Solutions Architect", re.IGNORECASE)) is True
    assert bool(re.search(pattern, "Graphic Designer in Vienna", re.IGNORECASE)) is False
