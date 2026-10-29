import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import main

@pytest.mark.asyncio
async def test_main_reaches_target_applications(monkeypatch, tmp_path):
    # Setup temporary master CV
    cv_dir = tmp_path / "data"
    cv_dir.mkdir(parents=True)
    cv_file = cv_dir / "master_cv.md"
    cv_file.write_text("# Candidate CV\nSkills: AI, Python", encoding="utf-8")

    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.config, "TARGET_APPLICATIONS", 2)
    monkeypatch.setattr(main.config, "MAX_SCANNED_VACANCIES", 10)
    monkeypatch.setattr(main.config, "validate", lambda: None)

    # Mock DB
    mock_db = MagicMock()
    mock_db.get_all_seen_urls.return_value = set()
    monkeypatch.setattr(main, "db", mock_db)

    # Mock DiscoveryAgent
    mock_discovery = MagicMock()
    discovered_urls = [
        "https://job.test/1",
        "https://job.test/2",
        "https://job.test/3",
        "https://job.test/4",
    ]
    mock_discovery.find_recent_vacancies = AsyncMock(return_value=discovered_urls)

    # Mock Orchestrator (Vacancy 1: match, Vacancy 2: reject, Vacancy 3: match)
    mock_orchestrator = MagicMock()
    run_results = {
        "https://job.test/1": {"cover_letter": "Match 1"},
        "https://job.test/2": {},
        "https://job.test/3": {"cover_letter": "Match 2"},
        "https://job.test/4": {"cover_letter": "Match 3"},
    }
    mock_orchestrator.run = AsyncMock(side_effect=lambda url, cv_path: run_results.get(url, {}))

    with patch("agents.discovery_agent.DiscoveryAgent", return_value=mock_discovery), \
         patch("main.AgenticApplyGraph", return_value=mock_orchestrator), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):

        await main.main()

    # Should stop on Vacancy 3 because target is 2 applications
    assert mock_orchestrator.run.call_count == 3
    assert mock_db.mark_url_seen.call_count == 3
    mock_db.mark_url_seen.assert_any_call("https://job.test/1")
    mock_db.mark_url_seen.assert_any_call("https://job.test/2")
    mock_db.mark_url_seen.assert_any_call("https://job.test/3")


@pytest.mark.asyncio
async def test_main_stops_at_max_scanned_vacancies(monkeypatch, tmp_path):
    cv_dir = tmp_path / "data"
    cv_dir.mkdir(parents=True)
    cv_file = cv_dir / "master_cv.md"
    cv_file.write_text("# Candidate CV\nSkills: AI, Python", encoding="utf-8")

    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.config, "TARGET_APPLICATIONS", 5)
    monkeypatch.setattr(main.config, "MAX_SCANNED_VACANCIES", 3)
    monkeypatch.setattr(main.config, "validate", lambda: None)

    mock_db = MagicMock()
    mock_db.get_all_seen_urls.return_value = set()
    monkeypatch.setattr(main, "db", mock_db)

    mock_discovery = MagicMock()
    discovered_urls = [f"https://job.test/{i}" for i in range(1, 10)]
    mock_discovery.find_recent_vacancies = AsyncMock(return_value=discovered_urls)

    mock_orchestrator = MagicMock()
    mock_orchestrator.run = AsyncMock(return_value={})

    with patch("agents.discovery_agent.DiscoveryAgent", return_value=mock_discovery), \
         patch("main.AgenticApplyGraph", return_value=mock_orchestrator), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):

        await main.main()

    # Should stop at 3 scanned vacancies regardless of 0 matches
    assert mock_orchestrator.run.call_count == 3
    assert mock_db.mark_url_seen.call_count == 3


@pytest.mark.asyncio
async def test_main_triggers_multiple_discovery_passes(monkeypatch, tmp_path):
    cv_dir = tmp_path / "data"
    cv_dir.mkdir(parents=True)
    cv_file = cv_dir / "master_cv.md"
    cv_file.write_text("# Candidate CV\nSkills: AI, Python", encoding="utf-8")

    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.config, "TARGET_APPLICATIONS", 2)
    monkeypatch.setattr(main.config, "MAX_SCANNED_VACANCIES", 10)
    monkeypatch.setattr(main.config, "validate", lambda: None)

    mock_db = MagicMock()
    mock_db.get_all_seen_urls.return_value = set()
    monkeypatch.setattr(main, "db", mock_db)

    # Pass 1 yields 1 rejected vacancy, Pass 2 yields 2 matching vacancies
    pass1_urls = ["https://job.test/p1"]
    pass2_urls = ["https://job.test/p2_1", "https://job.test/p2_2"]
    
    mock_discovery = MagicMock()
    mock_discovery.find_recent_vacancies = AsyncMock(side_effect=[pass1_urls, pass2_urls])

    mock_orchestrator = MagicMock()
    def fake_run(url, cv_path):
        if url == "https://job.test/p1":
            return {}
        return {"cover_letter": f"Letter for {url}"}

    mock_orchestrator.run = AsyncMock(side_effect=fake_run)

    with patch("agents.discovery_agent.DiscoveryAgent", return_value=mock_discovery), \
         patch("main.AgenticApplyGraph", return_value=mock_orchestrator), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):

        await main.main()

    assert mock_discovery.find_recent_vacancies.call_count == 2
    assert mock_orchestrator.run.call_count == 3


@pytest.mark.asyncio
async def test_main_stops_gracefully_when_no_fresh_vacancies(monkeypatch, tmp_path):
    cv_dir = tmp_path / "data"
    cv_dir.mkdir(parents=True)
    cv_file = cv_dir / "master_cv.md"
    cv_file.write_text("# Candidate CV\nSkills: AI, Python", encoding="utf-8")

    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.config, "TARGET_APPLICATIONS", 5)
    monkeypatch.setattr(main.config, "MAX_SCANNED_VACANCIES", 50)
    monkeypatch.setattr(main.config, "validate", lambda: None)

    mock_db = MagicMock()
    mock_db.get_all_seen_urls.return_value = set()
    monkeypatch.setattr(main, "db", mock_db)

    mock_discovery = MagicMock()
    mock_discovery.find_recent_vacancies = AsyncMock(return_value=[])

    mock_orchestrator = MagicMock()

    with patch("agents.discovery_agent.DiscoveryAgent", return_value=mock_discovery), \
         patch("main.AgenticApplyGraph", return_value=mock_orchestrator), \
         patch("asyncio.sleep", AsyncMock(return_value=None)):

        await main.main()

    assert mock_discovery.find_recent_vacancies.call_count == 1
    assert mock_orchestrator.run.call_count == 0
