import os
import sqlite3
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AoF Funds Panel")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "funds.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "1234")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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

# === ГЛАВНАЯ СТРАНИЦА (форма ввода) ===
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
            :root {{ --bg: #0f1115; --card: #1a1d24; --accent: #00d4aa; --text: #e0e0e0; --error: #ff4757; --danger: #ff6b6b; }}
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
            button:disabled {{ opacity: 0.6; cursor: not-allowed; }}
            .footer {{ text-align: center; margin-top: 16px; opacity: 0.4; font-size: 0.75rem; }}
            .nav-links {{ text-align: center; margin-top: 16px; }}
            .nav-links a {{ color: var(--accent); text-decoration: none; margin: 0 10px; }}
            .nav-links a:hover {{ text-decoration: underline; }}
            
            .notification {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 16px 24px;
                border-radius: 12px;
                font-weight: 500;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                transform: translateX(400px);
                transition: transform 0.3s ease;
                z-index: 1000;
            }}
            .notification.show {{ transform: translateX(0); }}
            .notification.success {{ background: var(--accent); color: #000; }}
            .notification.error {{ background: var(--error); color: #fff; }}
        </style>
    </head>
    <body>
        <div class="notification" id="notification"></div>
        
        <div class="card">
            <h1>🎰 AoF Funds</h1>
            <div class="meta">Обновлено: {updated}</div>
            <form id="fundsForm" method="post">
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
                <button type="submit" id="submitBtn">💾 Сохранить</button>
            </form>
            <div class="nav-links">
                <a href="/admin">⚙️ Админ-панель</a>
            </div>
            <div class="footer">PokerOK • AoF • Telegram Bot Ready</div>
        </div>

        <script>
            const form = document.getElementById('fundsForm');
            const notification = document.getElementById('notification');
            const submitBtn = document.getElementById('submitBtn');

            function showNotification(message, isSuccess = true) {{
                notification.textContent = message;
                notification.className = 'notification show ' + (isSuccess ? 'success' : 'error');
                setTimeout(() => {{
                    notification.classList.remove('show');
                }}, 3000);
            }}

            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const formData = new FormData(form);
                submitBtn.disabled = true;
                submitBtn.textContent = '⏳ Сохранение...';
                
                try {{
                    const response = await fetch('/update', {{
                        method: 'POST',
                        body: formData
                    }});
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showNotification('✅ Данные успешно сохранены!', true);
                        form.reset();
                        document.querySelector('input[name="jackpot"]').value = result.jackpot || formData.get('jackpot');
                        document.querySelector('input[name="aif"]').value = result.aif || formData.get('aif');
                    }} else {{
                        showNotification('❌ ' + (result.detail || 'Ошибка'), false);
                    }}
                }} catch (error) {{
                    showNotification('❌ Ошибка соединения', false);
                }} finally {{
                    submitBtn.disabled = false;
                    submitBtn.textContent = '💾 Сохранить';
                }}
            }});
        </script>
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
    conn.execute("INSERT INTO funds (jackpot, aif) VALUES (?, ?)", (jackpot, aif))
    conn.commit()
    
    row = conn.execute("SELECT jackpot, aif FROM funds ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    return {
        "status": "ok", 
        "message": "Данные сохранены",
        "jackpot": row["jackpot"],
        "aif": row["aif"]
    }

# === АДМИН-ПАНЕЛЬ ===
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = get_db()
    rows = conn.execute("SELECT * FROM funds ORDER BY created_at DESC").fetchall()
    conn.close()
    
    rows_html = ""
    for row in rows:
        rows_html += f"""
        <tr>
            <td>{row['id']}</td>
            <td>{row['jackpot']}</td>
            <td>{row['aif']}</td>
            <td>{row['created_at']}</td>
            <td>
                <button onclick="editRecord({row['id']}, {row['jackpot']}, {row['aif']})" style="background: #4ecdc4; padding: 6px 12px; font-size: 0.85rem; width: auto; margin: 0;">✏️</button>
                <button onclick="deleteRecord({row['id']})" style="background: var(--danger); padding: 6px 12px; font-size: 0.85rem; width: auto; margin: 0 0 0 5px;">🗑️</button>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Админ-панель - AoF Funds</title>
        <style>
            :root {{ --bg: #0f1115; --card: #1a1d24; --accent: #00d4aa; --text: #e0e0e0; --danger: #ff6b6b; }}
            body {{ margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            h1 {{ color: var(--accent); text-align: center; }}
            .card {{ background: var(--card); padding: 24px; border-radius: 16px; margin-bottom: 20px; }}
            .nav {{ text-align: center; margin-bottom: 20px; }}
            .nav a {{ color: var(--accent); text-decoration: none; margin: 0 10px; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
            th {{ background: #111; color: var(--accent); }}
            tr:hover {{ background: #222; }}
            
            .password-section {{ margin-top: 30px; }}
            .input-group {{ margin-bottom: 16px; }}
            label {{ display: block; margin-bottom: 6px; font-weight: 500; }}
            input {{ width: 100%; max-width: 300px; padding: 12px; border-radius: 10px; border: 1px solid #333; background: #111; color: #fff; }}
            button {{ padding: 12px 24px; background: var(--accent); color: #000; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; }}
            button:hover {{ opacity: 0.9; }}
            
            .notification {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 16px 24px;
                border-radius: 12px;
                font-weight: 500;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                transform: translateX(400px);
                transition: transform 0.3s ease;
                z-index: 1000;
            }}
            .notification.show {{ transform: translateX(0); }}
            .notification.success {{ background: var(--accent); color: #000; }}
            .notification.error {{ background: var(--danger); color: #fff; }}
        </style>
    </head>
    <body>
        <div class="notification" id="notification"></div>
        
        <div class="container">
            <div class="nav">
                <a href="/">🏠 На главную</a>
            </div>
            
            <h1>⚙️ Админ-панель</h1>
            
            <div class="card">
                <h2>📊 Все записи</h2>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Jackpot</th>
                            <th>All-in-Fortune</th>
                            <th>Дата</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="5" style="text-align: center; opacity: 0.5;">Нет записей</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            <div class="card password-section">
                <h2>🔐 Сменить пароль</h2>
                <div class="input-group">
                    <label>Текущий пароль:</label>
                    <input type="password" id="currentPassword" placeholder="Введи текущий пароль">
                </div>
                <div class="input-group">
                    <label>Новый пароль:</label>
                    <input type="password" id="newPassword" placeholder="Введи новый пароль">
                </div>
                <button onclick="changePassword()">💾 Сохранить новый пароль</button>
            </div>
        </div>

        <script>
            const notification = document.getElementById('notification');
            
            function showNotification(message, isSuccess = true) {{
                notification.textContent = message;
                notification.className = 'notification show ' + (isSuccess ? 'success' : 'error');
                setTimeout(() => notification.classList.remove('show'), 3000);
            }}
            
            async function deleteRecord(id) {{
                if (!confirm('Удалить запись #' + id + '?')) return;
                
                const formData = new FormData();
                formData.append('password', prompt('Введи пароль для подтверждения:'));
                formData.append('id', id);
                
                const response = await fetch('/admin/delete', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                if (response.ok) {{
                    showNotification('✅ Запись удалена');
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    showNotification('❌ ' + result.detail, false);
                }}
            }}
            
            async function editRecord(id, currentJackpot, currentAif) {{
                const newJackpot = prompt('Новый Jackpot:', currentJackpot);
                if (newJackpot === null) return;
                
                const newAif = prompt('Новый All-in-Fortune:', currentAif);
                if (newAif === null) return;
                
                const password = prompt('Введи пароль для подтверждения:');
                
                const formData = new FormData();
                formData.append('id', id);
                formData.append('jackpot', newJackpot);
                formData.append('aif', newAif);
                formData.append('password', password);
                
                const response = await fetch('/admin/edit', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                if (response.ok) {{
                    showNotification('✅ Запись обновлена');
                    setTimeout(() => location.reload(), 1000);
                }} else {{
                    showNotification('❌ ' + result.detail, false);
                }}
            }}
            
            async function changePassword() {{
                const currentPass = document.getElementById('currentPassword').value;
                const newPass = document.getElementById('newPassword').value;
                
                if (!currentPass || !newPass) {{
                    showNotification('❌ Заполни все поля', false);
                    return;
                }}
                
                const formData = new FormData();
                formData.append('current_password', currentPass);
                formData.append('new_password', newPass);
                
                const response = await fetch('/admin/change_password', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                if (response.ok) {{
                    showNotification('✅ Пароль изменён');
                    document.getElementById('currentPassword').value = '';
                    document.getElementById('newPassword').value = '';
                }} else {{
                    showNotification('❌ ' + result.detail, false);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/admin/edit")
async def edit_record(id: int = Form(...), jackpot: int = Form(...), aif: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    conn = get_db()
    conn.execute("UPDATE funds SET jackpot = ?, aif = ? WHERE id = ?", (jackpot, aif, id))
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": "Запись обновлена"}

@app.post("/admin/delete")
async def delete_record(id: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    
    conn = get_db()
    conn.execute("DELETE FROM funds WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return {"status": "ok", "message": "Запись удалена"}

@app.post("/admin/change_password")
async def change_password(current_password: str = Form(...), new_password: str = Form(...)):
    global ADMIN_PASSWORD
    
    if current_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Текущий пароль неверен")
    
    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="Пароль должен быть минимум 4 символа")
    
    # Обновляем переменную окружения (временно, до перезапуска)
    ADMIN_PASSWORD = new_password
    os.environ["ADMIN_PASS"] = new_password
    
    return {"status": "ok", "message": "Пароль изменён"}

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
