import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "https://aoffundsinfo.onrender.com")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")
MSK_TIMEZONE = timedelta(hours=3)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_funds_data(retries=3, timeout=60):
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/api/data", timeout=timeout) as response:
                    if response.status == 200:
                        return await response.json()
        except asyncio.TimeoutError:
            if attempt < retries - 1: await asyncio.sleep(10)
        except Exception as e:
            print(f"API Error: {e}")
            if attempt < retries - 1: await asyncio.sleep(10)
    return None

def format_month(month_key):
    m_names = {"01":"Январь","02":"Февраль","03":"Март","04":"Апрель","05":"Май","06":"Июнь",
               "07":"Июль","08":"Август","09":"Сентябрь","10":"Октябрь","11":"Ноябрь","12":"Декабрь"}
    try:
        y, m = month_key.split("-")
        return f"{m_names.get(m, m)} {y}"
    except: 
        return month_key

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("<b>AoF Funds Bot</b>\nОтправь /funds для просмотра фондов.", parse_mode="HTML")

@dp.message(Command("funds"))
async def cmd_funds(m: types.Message):
    await m.answer("⏳ Загружаю данные...")
    data = await get_funds_data()
    
    if data is None:
        await m.answer("❌ Ошибка связи с сервером. Попробуй позже.", parse_mode="HTML")
        return

    latest = data.get("latest", {})
    averages = data.get("monthly_averages", [])

    msg = ""
    # 1. Текущие значения
    msg += f"<b>Jackpot:</b> {latest.get('jackpot', 'N/A')} BB\n"
    msg += f"<b>All-in-Fortune:</b> {latest.get('aif', 'N/A')} BB\n\n"

    # 2. Дата обновления (ТЕПЕРЬ СРАЗУ ПОД ФОНДАМИ)
    upd_raw = latest.get("updated")
    if upd_raw:
        try:
            dt_str = str(upd_raw)[:19]
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            dt_msk = dt + MSK_TIMEZONE
            msg += f"<i>Обновлено: {dt_msk.strftime('%d.%m.%Y %H:%M')} (МСК)</i>\n\n"
        except:
            msg += "\n"
    else:
        msg += "\n"

    # 3. Средние по месяцам
    if averages:
        msg += " <b>Средние фонды:</b>\n"
        for av in averages:
            msg += f"{format_month(av['month_key'])}: {av['jackpot_avg']}/{av['aif_avg']}\n"
        msg += "\n"

    # 4. Ссылка и пароль
    msg += f"🔗 <a href='{API_URL}'>Обновить данные</a>\n"
    msg += f"<tg-spoiler>Пароль: {ADMIN_PASS}</tg-spoiler>"

    # Кнопки полностью убраны
    await m.answer(msg, parse_mode="HTML")

async def main():
    print("🤖 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
