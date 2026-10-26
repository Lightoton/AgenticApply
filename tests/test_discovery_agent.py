import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agents.discovery_agent import DiscoveryAgent


def _build_mock_playwright(local_jobs):
    mock_page = AsyncMock()
    mock_locator = MagicMock()
    mock_locator.count = AsyncMock(return_value=0)
    mock_page.locator = MagicMock(return_value=mock_locator)
    mock_page.evaluate = AsyncMock(return_value=local_jobs)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_pw_instance = AsyncMock()
    mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_cm = MagicMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_pw_instance)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_pw_cm


@pytest.mark.asyncio
async def test_discovery_find_recent_vacancies_end_to_end_filtering(sample_cv, mock_interaction, monkeypatch):
    monkeypatch.setattr("agents.discovery_agent.config.LOCAL_JOB_BOARDS", ["karriere.at"])
    monkeypatch.setattr("agents.discovery_agent.config.FALLBACK_JOB_BOARDS", [])
    monkeypatch.setattr("agents.discovery_agent.config.EXCLUDE_WORDS", ["senior", "lead", "principal"])
    monkeypatch.setattr("agents.discovery_agent.config.MUST_HAVE_KEYWORDS", ["ai", "llm", "python"])
    monkeypatch.setattr("agents.discovery_agent.config.ADDITIONAL_SEARCH_TERMS", [])
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_LOCAL", 5)
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_REMOTE", 5)

    local_jobs = [
        {"url": "https://www.karriere.at/jobs/111111", "title": "junior python developer"},
        {"url": "https://www.karriere.at/jobs/222222", "title": "senior python architect"},
        {"url": "https://www.karriere.at/jobs/333333", "title": "ai engineer wien"},
    ]
    mock_pw_cm = _build_mock_playwright(local_jobs)

    def fake_requests_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "remoteok.com" in url:
            resp.json.return_value = [
                {"legal": "metadata"},
                {"position": "AI Backend Engineer", "url": "https://remoteok.com/jobs/101"},
                {"position": "Lead AI Director", "url": "https://remoteok.com/jobs/102"},
                {"position": "Office Accountant", "url": "https://remoteok.com/jobs/103"},
                {"position": "Python Automation Developer", "url": "https://remoteok.com/jobs/104"},
            ]
        else:
            resp.json.return_value = {"data": [], "jobs": []}
        return resp

    agent = DiscoveryAgent()
    seen = {"https://www.karriere.at/jobs/333333"}

    with patch.object(agent.client.interactions, "create", return_value=mock_interaction("python, ai")) as mock_llm, \
         patch("agents.discovery_agent.async_playwright", return_value=mock_pw_cm), \
         patch("agents.discovery_agent.requests.get", side_effect=fake_requests_get):

        urls = await agent.find_recent_vacancies(sample_cv, seen_urls=seen)

        mock_llm.assert_called_once()
        # Local valid & unseen job included
        assert "https://www.karriere.at/jobs/111111" in urls
        # Local 'senior' job excluded via EXCLUDE_WORDS
        assert "https://www.karriere.at/jobs/222222" not in urls
        # Already seen URL excluded via seen_urls
        assert "https://www.karriere.at/jobs/333333" not in urls
        # Remote valid AI/Python jobs included
        assert "https://remoteok.com/jobs/101" in urls
        assert "https://remoteok.com/jobs/104" in urls
        # Remote 'Lead' job excluded via EXCLUDE_WORDS
        assert "https://remoteok.com/jobs/102" not in urls
        # Remote non-AI/non-Python job ('Office Accountant') excluded via MUST_HAVE_KEYWORDS
        assert "https://remoteok.com/jobs/103" not in urls


@pytest.mark.asyncio
async def test_discovery_llm_fallback_on_api_error(sample_cv, monkeypatch):
    monkeypatch.setattr("agents.discovery_agent.config.LOCAL_JOB_BOARDS", ["karriere.at"])
    monkeypatch.setattr("agents.discovery_agent.config.FALLBACK_JOB_BOARDS", [])
    monkeypatch.setattr("agents.discovery_agent.config.EXCLUDE_WORDS", ["senior"])
    monkeypatch.setattr("agents.discovery_agent.config.MUST_HAVE_KEYWORDS", ["ai"])
    monkeypatch.setattr("agents.discovery_agent.config.ADDITIONAL_SEARCH_TERMS", [])
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_LOCAL", 2)
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_REMOTE", 1)

    local_jobs = [{"url": "https://www.karriere.at/jobs/777777", "title": "junior ai developer"}]
    mock_pw_cm = _build_mock_playwright(local_jobs)

    resp_404 = MagicMock()
    resp_404.status_code = 404

    agent = DiscoveryAgent()
    with patch.object(agent.client.interactions, "create", side_effect= RuntimeError("Gemini quota exceeded")), \
         patch("agents.discovery_agent.async_playwright", return_value=mock_pw_cm), \
         patch("agents.discovery_agent.requests.get", return_value=resp_404):

        urls = await agent.find_recent_vacancies(sample_cv)
        assert urls == ["https://www.karriere.at/jobs/777777"]


@pytest.mark.asyncio
async def test_discovery_respects_local_and_remote_quotas(sample_cv, mock_interaction, monkeypatch):
    monkeypatch.setattr("agents.discovery_agent.config.LOCAL_JOB_BOARDS", ["karriere.at"])
    monkeypatch.setattr("agents.discovery_agent.config.FALLBACK_JOB_BOARDS", [])
    monkeypatch.setattr("agents.discovery_agent.config.EXCLUDE_WORDS", [])
    monkeypatch.setattr("agents.discovery_agent.config.MUST_HAVE_KEYWORDS", ["ai"])
    monkeypatch.setattr("agents.discovery_agent.config.ADDITIONAL_SEARCH_TERMS", [])
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_LOCAL", 2)
    monkeypatch.setattr("agents.discovery_agent.config.QUOTA_REMOTE", 2)

    local_jobs = [
        {"url": f"https://www.karriere.at/jobs/10000{i}", "title": f"ai engineer {i}"}
        for i in range(6)
    ]
    mock_pw_cm = _build_mock_playwright(local_jobs)

    def fake_requests_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {"legal": "meta"},
            *[{"position": f"AI Developer {i}", "url": f"https://remoteok.com/jobs/{i}"} for i in range(6)],
        ]
        return resp

    agent = DiscoveryAgent()
    with patch.object(agent.client.interactions, "create", return_value=mock_interaction("ai engineer")), \
         patch("agents.discovery_agent.async_playwright", return_value=mock_pw_cm), \
         patch("agents.discovery_agent.requests.get", side_effect=fake_requests_get):

        urls = await agent.find_recent_vacancies(sample_cv)
        local_returned = [u for u in urls if "karriere.at" in u]
        remote_returned = [u for u in urls if "remoteok.com" in u]

        assert len(local_returned) == 2
        assert len(remote_returned) == 2
        assert len(urls) == 4
