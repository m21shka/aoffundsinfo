import os
import sqlite3
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="AoF Funds Panel")
DB_PATH = "funds.db"
# Пароль берется из переменной окружения, если нет - используется 1234
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "1234")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # Таблица теперь хранит ИСТОРИЮ записей (удален CHECK id=1, добавлен AUTOINCREMENT)
    conn.execute("""CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jackpot INTEGER DEFAULT 0,
        aif INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def admin_page():
    conn = get_db()
    row = conn.execute("SELECT jackpot, aif, created_at FROM funds ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    if row:
        updated = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%d.%m %H:%M")
        jp_val = row["jackpot"]
        aif_val = row["aif"]
    else:
        updated = "Нет данных"
        jp_val = 0
        aif_val = 0
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AoF Funds Manager</title>
        <style>
            :root {{ --bg: #0f1115; --card: #1a1d24; --accent: #00d4aa; --text: #e0e0e0; }}
            body {{ margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; box-sizing: border-box; }}
            .card {{ background: var(--card); padding: 24px; border-radius: 16px; width: 100%; max-width: 400px; box-shadow: 0 8px 30px rgba(0,0,0,0.5); }}
            h1 {{ text-align: center; color: var(--accent); margin-bottom: 8px; }}
            .meta {{ text-align: center; opacity: 0.5; font-size: 0.85rem; margin-bottom: 20px; }}
            .input-group {{ margin-bottom: 16px; }}
            label {{ display: block; margin-bottom: 6px; font-weight: 500; }}
            input {{ width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #111; color: #fff; font-size: 1rem; box-sizing: border-box; }}
            input:focus {{ outline: none; border-color: var(--accent); }}
            button {{ width: 100%; padding: 14px; background: var(--accent); color: #000; font-weight: bold; border: none; border-radius: 10px; cursor: pointer; font-size: 1rem; margin-top: 8px; }}
            button:hover {{ opacity: 0.9; }}
            .footer {{ text-align: center; margin-top: 16px; opacity: 0.4; font-size: 0.75rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🎰 AoF Funds</h1>
            <div class="meta">Обновлено: {updated}</div>
            <form method="post" action="/update">
                <div class="input-group">
                    <label>Jackpot (BB)</label>
                    <input type="number" name="jackpot" value="{jp_val}" required>
                </div>
                <div class="input-group">
                    <label>All-in-Fortune (BB)</label>
                    <input type="number" name="aif" value="{aif_val}" required>
                </div>
                <div class="input-group">
                    <label>🔑 Пароль</label>
                    <input type="password" name="password" required placeholder="Введи секрет">
                </div>
                <button type="submit">💾 Сохранить</button>
            </form>
            <div class="footer">PokerOK • AoF • Telegram Bot Ready</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/update")
async def update_funds(jackpot: int = Form(...), aif: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    if jackpot < 0 or aif < 0:
        raise HTTPException(status_code=400, detail="Значения не могут быть отрицательными")
        
    conn = get_db()
    # Теперь данные ДОБАВЛЯЮТСЯ, а не перезаписываются. Это нужно для истории и средних значений.
    conn.execute("INSERT INTO funds (jackpot, aif) VALUES (?, ?)", (jackpot, aif))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Данные сохранены"}

@app.get("/api/data")
async def get_funds_data():
    conn = get_db()
    rows = conn.execute("SELECT jackpot, aif, created_at FROM funds ORDER BY created_at ASC").fetchall()
    conn.close()

    if not rows:
        return {"latest": {"jackpot": 0, "aif": 0}, "monthly_averages": []}

    latest = rows[-1]
    latest_data = {
        "jackpot": latest["jackpot"],
        "aif": latest["aif"],
        "updated": latest["created_at"]
    }

    # Группировка по месяцам для расчета средних
    monthly = defaultdict(list)
    month_names = {
        "01": "Январь", "02": "Февраль", "03": "Март", "04": "Апрель", "05": "Май",
        "06": "Июнь", "07": "Июль", "08": "Август", "09": "Сентябрь", "10": "Октябрь",
        "11": "Ноябрь", "12": "Декабрь"
    }

    for r in rows:
        try:
            dt = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
            key = dt.strftime("%Y-%m")
            monthly[key].append((r["jackpot"], r["aif"]))
        except Exception:
            continue

    averages = []
    for month_key in sorted(monthly.keys()):
        data = monthly[month_key]
        jp_avg = sum(d[0] for d in data) / len(data)
        aif_avg = sum(d[1] for d in data) / len(data)
        month_num = month_key.split("-")[1]
        averages.append({
            "month_key": month_key,
            "month_name": month_names.get(month_num, "Месяц"),
            "jackpot_avg": round(jp_avg, 1),
            "aif_avg": round(aif_avg, 1)
        })

    return {"latest": latest_data, "monthly_averages": averages}
