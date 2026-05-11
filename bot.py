import os
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_URL = os.getenv("API_URL", "https://aoffundsinfo.onrender.com")

# Московское время (UTC+3)
MSK_TIMEZONE = timedelta(hours=3)

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_funds_data(retries=3, timeout=60):
    """Получает данные из API с повторными попытками (для пробуждения Render)"""
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/api/data", timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API вернул статус: {response.status}")
        except asyncio.TimeoutError:
            print(f"Попытка {attempt + 1}: Таймаут (Render спит), ждем 10 сек...")
            if attempt < retries - 1:
                await asyncio.sleep(10)
        except Exception as e:
            print(f"Попытка {attempt + 1}: Ошибка - {e}")
            if attempt < retries - 1:
                await asyncio.sleep(10)
    
    return None

def format_month_name(month_key):
    """Преобразует '2026-05' в 'Май 2026'"""
    month_names = {
        "01": "Январь", "02": "Февраль", "03": "Март", "04": "Апрель",
        "05": "Май", "06": "Июнь", "07": "Июль", "08": "Август",
        "09": "Сентябрь", "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"
    }
    try:
        year, month = month_key.split("-")
        return f"{month_names.get(month, month)} {year}"
    except:
        return month_key

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        " *AoF Funds Bot*\n\n"
        "Отправь /funds чтобы увидеть текущие значения фондов.\n"
        "Данные обновляются автоматически.",
        parse_mode="Markdown"
    )

@dp.message(Command("funds"))
async def cmd_funds(message: types.Message):
    await message.answer("⏳ Загружаю данные...")
    
    data = await get_funds_data()
    
    if not data:
        await message.answer(
            "❌ *Ошибка!* Не удалось получить данные из API.\n\n"
            "Возможно, сервер временно недоступен. Попробуй позже.",
            parse_mode="Markdown"
        )
        return
    
    latest = data.get("latest", {})
    monthly_averages = data.get("monthly_averages", [])
    
    # Формируем сообщение
    text = ""
    
    # Текущие значения (без эмодзи)
    text += f"*Jackpot:* {latest.get('jackpot', 'N/A')} BB\n"
    text += f"*All-in-Fortune:* {latest.get('aif', 'N/A')} BB\n\n"
    
    # Средние по месяцам
    if monthly_averages:
        text += "📊 *Средние фонды:*\n"
        for month_data in monthly_averages:
            month_name = format_month_name(month_data.get("month_key", ""))
            jp_avg = month_data.get("jackpot_avg", 0)
            aif_avg = month_data.get("aif_avg", 0)
            text += f"{month_name}: {jp_avg}/{aif_avg}\n"
        text += "\n"
    
    # Время обновления
    updated_at = latest.get("updated")
    if updated_at:
        try:
            dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            dt_msk = dt + MSK_TIMEZONE
            text += f"_Обновлено: {dt_msk.strftime('%d.%m.%Y %H:%M')} (МСК)_\n\n"
        except:
            pass
    
    # Ссылка на обновление
    text += f"🔗 [Обновить данные]({API_URL})\n"
    
    # Скрытый пароль (спойлер)
    password = os.getenv("ADMIN_PASS", "1234")
    text += f"||Пароль: {password}||"
    
    # Кнопка
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить данные", url=API_URL)]
    ])
    
    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="MarkdownV2"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "*Доступные команды:*\n\n"
        "/start - Запустить бота\n"
        "/funds - Показать текущие значения фондов\n"
        "/help - Показать эту справку\n\n"
        "Данные берутся из панели управления AoF Funds."
    )
    await message.answer(help_text, parse_mode="Markdown")

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
