import pytest
import sqlite3
from unittest.mock import MagicMock
from core.database import DatabaseManager

@pytest.fixture
def sample_cv():
    return """# Jane Doe
## Senior Python Engineer
Email: jane.doe@example.com | Phone: +1234567890 | Location: Vienna, Austria

### Summary
Experienced Python Developer specializing in async backends, LangGraph, and API integrations.

### Skills
- Python, FastAPI, Docker, PostgreSQL, LangGraph, Playwright
- English (Fluent), German (B2)

### Experience
#### Backend Developer at TechCorp (2022 - Present)
- Designed and built scalable microservices using Python and FastAPI.
- Built automated web scrapers with Playwright for competitive intelligence.
"""

@pytest.fixture
def sample_jd_good():
    return """We are looking for a Python Developer in Vienna.
Requirements:
- Strong experience in Python, FastAPI, and Docker.
- Experience with web scraping (Playwright or Selenium) is a big plus.
- German B2 and English fluent.
- Junior to Mid level engineers welcome.
"""

@pytest.fixture
def sample_jd_bad():
    return """We are looking for a Principal React & Frontend Architect in New York.
Requirements:
- 10+ years of leading frontend engineering teams.
- Deep expertise in React, CSS, Next.js, and Swift iOS development.
- Must relocate to New York, USA.
"""

@pytest.fixture
def in_memory_db(tmp_path):
    test_db_file = str(tmp_path / "test_agentic_apply.db")
    db = DatabaseManager()
    db.db_path = test_db_file
    db._init_db()
    return db

@pytest.fixture
def mock_interaction():
    def _create_mock(output_text):
        mock_obj = MagicMock()
        mock_obj.output_text = output_text
        return mock_obj
    return _create_mock
