import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

class TelegramNotifier:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.bot = Bot(token=self.token) if self.token else None

    async def send_message(self, text):
        """Envía un mensaje de texto vía Telegram."""
        if not self.bot or not self.chat_id:
            print(f"Telegram no configurado. Mensaje: {text}")
            return False
        
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text)
            return True
        except Exception as e:
            print(f"Error al enviar mensaje de Telegram: {e}")
            return False

async def test_notification():
    notifier = TelegramNotifier()
    await notifier.send_message("🤖 CaucionBot iniciado correctamente.")

if __name__ == "__main__":
    asyncio.run(test_notification())
