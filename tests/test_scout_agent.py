import pytest
from agents.scout_agent import ScoutAgent

def test_scout_clean_html_removes_scripts_and_styles():
    scout = ScoutAgent()
    dirty_html = """
    <html>
        <head>
            <script>console.log("analytics tracking");</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <main>
                <h1>Python Backend Developer</h1>
                <p>We need an experienced developer in Vienna.</p>
            </main>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """

    clean_text = scout.clean_html_to_text(dirty_html)

    assert "analytics tracking" not in clean_text
    assert "color: red" not in clean_text
    assert "Python Backend Developer" in clean_text
    assert "We need an experienced developer in Vienna." in clean_text
    assert "Copyright 2026" not in clean_text

def test_scout_clean_html_truncates_long_content():
    scout = ScoutAgent()
    long_content = "A" * 20000
    dirty_html = f"<div><p>{long_content}</p></div>"

    clean_text = scout.clean_html_to_text(dirty_html)
    assert len(clean_text) <= 15000

def test_scout_clean_html_empty_input():
    scout = ScoutAgent()
    assert scout.clean_html_to_text("") == ""
    assert scout.clean_html_to_text(None) == ""

def test_scout_validate_content_length_and_waf_signatures():
    scout = ScoutAgent()
    
    # Too short (<100 chars)
    valid, reason = scout.validate_content("Short text")
    assert valid is False
    assert "too short" in reason

    # WAF Cloudflare interstitial
    blocked_text = "Please verify you are human by completing the security challenge. Cloudflare Ray ID: 8934ab12. Security by Cloudflare." * 2
    valid, reason = scout.validate_content(blocked_text)
    assert valid is False
    assert "WAF poison signature" in reason

    # Legitimate job description
    valid_text = "We are seeking a talented Python Backend Engineer in Vienna. You will design scalable FastAPI microservices and manage PostgreSQL databases. We offer competitive pay with market overpayment above IT-KV."
    valid, reason = scout.validate_content(valid_text)
    assert valid is True
    assert reason == "Valid"


@pytest.mark.asyncio
async def test_scout_fetch_page_content_uses_domcontentloaded():
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_page = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body><h1>Test JD</h1></body></html>")
    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    mock_pw_instance = AsyncMock()
    mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_cm = MagicMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_pw_instance)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=None)

    scout = ScoutAgent()
    with patch("agents.scout_agent.async_playwright", return_value=mock_pw_cm):
        content = await scout.fetch_page_content("https://example.com/job/123")
        assert "Test JD" in content

        mock_page.goto.assert_awaited_once_with(
            "https://example.com/job/123",
            wait_until="domcontentloaded",
            timeout=15000
        )
        mock_page.wait_for_timeout.assert_awaited_once_with(1000)
