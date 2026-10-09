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
