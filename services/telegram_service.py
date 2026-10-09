from core.logger import logger
import os
from telegram import Bot
from telegram.constants import ParseMode
from core.config import config

class TelegramService:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None

    async def send_document(self, document_path: str, caption: str = ""):
        """Sends a document (like a PDF) to the configured Telegram chat."""
        if not self.bot:
            logger.info("Telegram Bot is not configured. Skipping send.")
            return
            
        with open(document_path, 'rb') as doc:
            await self.bot.send_document(
                chat_id=self.chat_id,
                document=doc,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
        filename = os.path.basename(document_path)
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii')
        logger.info(f"[SUCCESS] Document {safe_filename} sent to Telegram.")

    async def send_message(self, text: str):
        if not self.bot:
            return
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
