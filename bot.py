import os
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_ИЗ_ШАГА_1")
API_URL = os.getenv("API_URL", "http://localhost:8000/api/funds")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("jackpot"))
async def cmd_jackpot(message: Message):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(API_URL, timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            
            updated_dt = datetime.fromisoformat(data["updated"])
            updated_str = updated_dt.strftime("%d.%m %H:%M")
            
            text = (
                f"🎰 **AoF Funds**\n"
                f"🔹 Jackpot: `{data['jackpot']}` BB\n"
                f"🔹 All-in-Fortune: `{data['aif']}` BB\n"
                f"🕒 Обновлено: {updated_str}"
            )
            await message.answer(text, parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"⚠️ Ошибка загрузки: `{str(e)}`", parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())