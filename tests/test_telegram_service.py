import pytest
from unittest.mock import AsyncMock, patch
from telegram.constants import ParseMode
from services.telegram_service import TelegramService

@pytest.mark.asyncio
async def test_telegram_service_unconfigured(monkeypatch):
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_CHAT_ID", None)

    service = TelegramService()
    # When token is None, bot should be None and methods should gracefully return without error
    await service.send_message("Test message")
    await service.send_document("dummy_path.pdf")
    assert service.bot is None

@pytest.mark.asyncio
async def test_telegram_service_send_message_and_document(tmp_path, monkeypatch):
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_CHAT_ID", "999888777")

    mock_bot = AsyncMock()
    with patch("services.telegram_service.Bot", return_value=mock_bot):
        service = TelegramService()
        
        # Test send_message
        await service.send_message("Hello from test")
        mock_bot.send_message.assert_awaited_once_with(
            chat_id="999888777",
            text="Hello from test",
            parse_mode=ParseMode.MARKDOWN
        )

        # Test send_document
        dummy_file = tmp_path / "CV_Test.pdf"
        dummy_file.write_bytes(b"%PDF-1.4 mock content")

        await service.send_document(str(dummy_file))
        assert mock_bot.send_document.await_count == 1


@pytest.mark.asyncio
async def test_telegram_service_send_message_markdown_fallback(monkeypatch):
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_CHAT_ID", "999888777")

    mock_bot = AsyncMock()
    mock_bot.send_message.side_effect = [Exception("BadRequest: Can't parse entities"), None]

    with patch("services.telegram_service.Bot", return_value=mock_bot):
        service = TelegramService()
        await service.send_message("Unclosed *markdown_text")

    assert mock_bot.send_message.await_count == 2
    first_call = mock_bot.send_message.await_args_list[0].kwargs
    second_call = mock_bot.send_message.await_args_list[1].kwargs
    assert first_call["parse_mode"] == ParseMode.MARKDOWN
    assert "parse_mode" not in second_call


@pytest.mark.asyncio
async def test_telegram_service_send_document_markdown_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setattr("services.telegram_service.config.TELEGRAM_CHAT_ID", "999888777")

    dummy_file = tmp_path / "CV_Fallback_Test.pdf"
    dummy_file.write_bytes(b"%PDF-1.4 mock content")

    mock_bot = AsyncMock()
    mock_bot.send_document.side_effect = [Exception("BadRequest: Can't parse entities"), None]

    with patch("services.telegram_service.Bot", return_value=mock_bot):
        service = TelegramService()
        await service.send_document(str(dummy_file), caption="Unclosed *caption_markdown")

    assert mock_bot.send_document.await_count == 2
    first_call = mock_bot.send_document.await_args_list[0].kwargs
    second_call = mock_bot.send_document.await_args_list[1].kwargs
    assert first_call["parse_mode"] == ParseMode.MARKDOWN
    assert "parse_mode" not in second_call
