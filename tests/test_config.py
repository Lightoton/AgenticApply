import pytest
import importlib
import core.config
from core.config import Config

def test_config_parsing_defaults(monkeypatch):
    orig_config_instance = core.config.config
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
    monkeypatch.setenv("EXCLUDE_WORDS", "senior, lead, staff")
    monkeypatch.setenv("MUST_HAVE_KEYWORDS", "ai, llm, python")

    reloaded_module = importlib.reload(core.config)
    cfg = reloaded_module.Config()
    try:
        assert cfg.GEMINI_API_KEY == "test_gemini_key"
        assert cfg.TELEGRAM_BOT_TOKEN == "test_bot_token"
        assert cfg.TELEGRAM_CHAT_ID == "test_chat_id"
        assert cfg.EXCLUDE_WORDS == ["senior", "lead", "staff"]
        assert cfg.MUST_HAVE_KEYWORDS == ["ai", "llm", "python"]
        assert cfg.GEMINI_MODEL == "gemini-3.8-flash"
        assert cfg.GEMINI_FLASH_MODEL == "gemini-3.8-flash"
        assert cfg.GEMINI_PRO_MODEL == "gemini-3.8-flash"
        assert cfg.TARGET_APPLICATIONS == 5
        assert cfg.MAX_SCANNED_VACANCIES == 50
    finally:
        # Restore original module state and singleton reference
        importlib.reload(core.config)
        core.config.config = orig_config_instance

def test_config_validate_success(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", "valid_key")
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", "valid_token")
    monkeypatch.setattr(Config, "TELEGRAM_CHAT_ID", "valid_chat_id")
    
    # Should not raise any exception
    Config.validate()

def test_config_validate_missing_keys(monkeypatch):
    monkeypatch.setattr(Config, "GEMINI_API_KEY", None)
    monkeypatch.setattr(Config, "TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr(Config, "TELEGRAM_CHAT_ID", None)

    with pytest.raises(ValueError) as excinfo:
        Config.validate()
    assert "Missing required environment variables" in str(excinfo.value)
    assert "GEMINI_API_KEY" in str(excinfo.value)
