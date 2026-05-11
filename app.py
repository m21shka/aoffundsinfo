import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="AoF Funds Panel")
DB_PATH = "funds.db"
# Пароль для панели. Пока оставь так, настроим позже в хостинге
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "1234")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS funds (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        jackpot INTEGER DEFAULT 0,
        aif INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.execute("INSERT OR IGNORE INTO funds (id, jackpot, aif) VALUES (1, 0, 0)")
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def admin_page():
    conn = get_db()
    row = conn.execute("SELECT * FROM funds WHERE id = 1").fetchone()
    conn.close()
    
    updated = datetime.fromisoformat(row["updated_at"]).strftime("%d.%m %H:%M")
    
    # CSS-скобки удвоены, чтобы не конфликтовать с f-строкой
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
                    <input type="number" name="jackpot" value="{row['jackpot']}" required>
                </div>
                <div class="input-group">
                    <label>All-in-Fortune (BB)</label>
                    <input type="number" name="aif" value="{row['aif']}" required>
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
    conn.execute("UPDATE funds SET jackpot = ?, aif = ?, updated_at = datetime('now') WHERE id = 1", (jackpot, aif))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Данные сохранены"}

@app.get("/api/funds")
async def get_funds():
    conn = get_db()
    row = conn.execute("SELECT * FROM funds WHERE id = 1").fetchone()
    conn.close()
    return {
        "jackpot": row["jackpot"],
        "aif": row["aif"],
        "updated": row["updated_at"]
    }