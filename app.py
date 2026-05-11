import os
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import FastAPI, Form, HTTPException, Request, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AoF Funds Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASS", "1234")
MSK_OFFSET = timedelta(hours=3)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в переменных окружения!")

def get_db():
    # Подключение к Neon PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Синтаксис Postgres: SERIAL для автоинкремента
    cur.execute("""CREATE TABLE IF NOT EXISTS funds (
        id SERIAL PRIMARY KEY,
        jackpot INTEGER DEFAULT 0,
        aif INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    cur.close()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

# === ГЛАВНАЯ СТРАНИЦА ===
@app.get("/", response_class=HTMLResponse)
async def admin_page():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT jackpot, aif, created_at FROM funds ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        # row[0]=jackpot, row[1]=aif, row[2]=created_at
        dt_utc = row[2]
        if dt_utc.tzinfo is None: dt_utc = dt_utc.replace(tzinfo=None)
        dt_msk = dt_utc + MSK_OFFSET
        updated = dt_msk.strftime("%d.%m %H:%M")
        jp_val = row[0]
        aif_val = row[1]
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
            :root {{ --bg: #0f1115; --card: #1a1d24; --accent: #00d4aa; --text: #e0e0e0; --error: #ff4757; }}
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
            .notification {{ position: fixed; top: 20px; right: 20px; padding: 16px 24px; border-radius: 12px; font-weight: 500; box-shadow: 0 4px 20px rgba(0,0,0,0.3); transform: translateX(400px); transition: transform 0.3s ease; z-index: 1000; }}
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
                <div class="input-group"><label>Jackpot (BB)</label><input type="number" name="jackpot" value="{jp_val}" required></div>
                <div class="input-group"><label>All-in-Fortune (BB)</label><input type="number" name="aif" value="{aif_val}" required></div>
                <div class="input-group"><label>🔑 Пароль</label><input type="password" name="password" required placeholder="Введи секрет"></div>
                <button type="submit" id="submitBtn"> Сохранить</button>
            </form>
            <div class="nav-links"><a href="/admin">⚙️ Админ-панель</a></div>
            <div class="footer">PokerOK • AoF • Telegram Bot Ready</div>
        </div>
        <script>
            const form = document.getElementById('fundsForm');
            const notif = document.getElementById('notification');
            const btn = document.getElementById('submitBtn');
            function show(msg, ok=true) {{ notif.textContent=msg; notif.className='notification show '+(ok?'success':'error'); setTimeout(()=>notif.classList.remove('show'),3000); }}
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const fd = new FormData(form); btn.disabled=true; btn.textContent='⏳...';
                try {{
                    const r = await fetch('/update', {{method:'POST', body:fd}});
                    const d = await r.json();
                    if(r.ok) {{ show('✅ Сохранено!'); document.querySelector('input[name="jackpot"]').value=d.jackpot; document.querySelector('input[name="aif"]').value=d.aif; }}
                    else show('❌ '+d.detail, false);
                }} catch(err) {{ show('❌ Ошибка сети', false); }}
                finally {{ btn.disabled=false; btn.textContent='💾 Сохранить'; }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/update")
async def update_funds(jackpot: int = Form(...), aif: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD: raise HTTPException(401, "Неверный пароль")
    conn = get_db(); cur = conn.cursor()
    # Postgres синтаксис: %s
    cur.execute("INSERT INTO funds (jackpot, aif) VALUES (%s, %s) RETURNING id, jackpot, aif", (jackpot, aif))
    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return {"status": "ok", "jackpot": row[1], "aif": row[2]}

# === АДМИНКА С ВХОДОМ ===
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, auth: str = Cookie(None)):
    if auth != "granted":
        return HTMLResponse("""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Вход</title>
        <style>body{background:#0f1115;color:#e0e0e0;font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
        .card{background:#1a1d24;padding:30px;border-radius:16px;width:300px;text-align:center;}
        input{width:100%;padding:12px;border-radius:8px;border:1px solid #333;background:#111;color:#fff;margin-bottom:15px;}
        button{width:100%;padding:12px;background:#00d4aa;border:none;border-radius:8px;color:#000;font-weight:bold;cursor:pointer;}
        </style></head><body><div class="card"><h2>🔒 Вход</h2>
        <form method="post" action="/admin/login"><input type="password" name="password" placeholder="Пароль" required><button>Войти</button></form></div></body></html>""")

    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM funds ORDER BY created_at DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    
    rows_html = ""
    for row in rows:
        # row: id, jackpot, aif, created_at
        dt_utc = row[3]
        if dt_utc.tzinfo is None: dt_utc = dt_utc.replace(tzinfo=None)
        dt_msk = dt_utc + MSK_OFFSET
        rows_html += f"""<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td>
        <td>{dt_msk.strftime('%d.%m %H:%M')}</td>
        <td><button onclick="editRec({row[0]},{row[1]},{row[2]})" style="background:#4ecdc4;padding:5px 10px;font-size:0.8rem;width:auto;margin:0;">✏️</button>
        <button onclick="delRec({row[0]})" style="background:#ff6b6b;padding:5px 10px;font-size:0.8rem;width:auto;margin:0 0 0 5px;">️</button></td></tr>"""
    
    html = f"""
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админ-панель</title>
    <style>
        :root{{--bg:#0f1115;--card:#1a1d24;--accent:#00d4aa;--text:#e0e0e0;--danger:#ff6b6b;}}
        body{{margin:0;font-family:system-ui;background:var(--bg);color:var(--text);padding:20px;}}
        .container{{max-width:1000px;margin:0 auto;}} h1{{color:var(--accent);text-align:center;}}
        .card{{background:var(--card);padding:24px;border-radius:16px;margin-bottom:20px;}}
        .nav{{text-align:center;margin-bottom:20px;}}.nav a{{color:var(--accent);text-decoration:none;margin:0 10px;}}
        table{{width:100%;border-collapse:collapse;margin-top:15px;}}
        th,td{{padding:10px;text-align:left;border-bottom:1px solid #333;}}th{{background:#111;color:var(--accent);}}
        .notif{{position:fixed;top:20px;right:20px;padding:15px 20px;border-radius:10px;font-weight:500;transform:translateX(400px);transition:0.3s;z-index:1000;}}
        .notif.show{{transform:translateX(0);}}.notif.ok{{background:#00d4aa;color:#000;}}.notif.err{{background:#ff6b6b;color:#fff;}}
    </style></head><body>
    <div class="notif" id="n"></div>
    <div class="container">
        <div class="nav"><a href="/"> На главную</a> | <a href="/admin/logout">🚪 Выйти</a></div>
        <h1>⚙️ Админ-панель (Neon DB)</h1>
        <div class="card"><h2>📊 Записи</h2>
        <table><thead><tr><th>ID</th><th>Jackpot</th><th>All-in-Fortune</th><th>Дата (МСК)</th><th>Действия</th></tr></thead>
        <tbody>{rows_html or '<tr><td colspan="5" style="text-align:center;opacity:0.5;">Нет записей</td></tr>'}</tbody></table></div>
    </div>
    <script>
    const n=document.getElementById('n');
    function msg(t,ok=true){{n.textContent=t;n.className='notif show '+(ok?'ok':'err');setTimeout(()=>n.classList.remove('show'),3000);}}
    async function delRec(id){{if(!confirm('Удалить #'+id+'?'))return;
    const p=prompt('Пароль админа:');const fd=new FormData();fd.append('id',id);fd.append('password',p);
    const r=await fetch('/admin/delete',{{method:'POST',body:fd}});const d=await r.json();
    r.ok?msg('✅ Удалено',true)&&setTimeout(()=>location.reload(),1000):msg('❌ '+d.detail,false);}}
    async function editRec(id,jp,aif){{
    const nj=prompt('Новый Jackpot:',jp);if(nj===null)return;
    const na=prompt('Новый All-in-Fortune:',aif);if(na===null)return;
    const p=prompt('Пароль админа:');const fd=new FormData();fd.append('id',id);fd.append('jackpot',nj);fd.append('aif',na);fd.append('password',p);
    const r=await fetch('/admin/edit',{{method:'POST',body:fd}});const d=await r.json();
    r.ok?msg('✅ Обновлено',true)&&setTimeout(()=>location.reload(),1000):msg('❌ '+d.detail,false);}}
    </script></body></html>
    """
    return HTMLResponse(html)

@app.post("/admin/login")
async def admin_login(password: str = Form(...), response: Response = None):
    if password == ADMIN_PASSWORD:
        response.set_cookie(key="auth", value="granted", httponly=True, samesite="lax")
        return RedirectResponse(url="/admin", status_code=302)
    raise HTTPException(401, "Неверный пароль")

@app.get("/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie("auth")
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/edit")
async def edit_record(id: int = Form(...), jackpot: int = Form(...), aif: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD: raise HTTPException(401, "Неверный пароль")
    conn = get_db(); cur = conn.cursor(); cur.execute("UPDATE funds SET jackpot=%s, aif=%s WHERE id=%s", (jackpot, aif, id)); conn.commit(); cur.close(); conn.close()
    return {"status": "ok"}

@app.post("/admin/delete")
async def delete_record(id: int = Form(...), password: str = Form(...)):
    if password != ADMIN_PASSWORD: raise HTTPException(401, "Неверный пароль")
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM funds WHERE id=%s", (id,)); conn.commit(); cur.close(); conn.close()
    return {"status": "ok"}

@app.get("/api/data")
async def get_funds_data():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT jackpot, aif, created_at FROM funds ORDER BY created_at ASC")
    rows = cur.fetchall(); cur.close(); conn.close()
    
    if not rows: return {"latest": {"jackpot": 0, "aif": 0}, "monthly_averages": []}
    
    latest = rows[-1]
    latest_data = {"jackpot": latest[0], "aif": latest[1], "updated": str(latest[2])}
    
    monthly = defaultdict(list)
    month_names = {"01":"Январь","02":"Февраль","03":"Март","04":"Апрель","05":"Май","06":"Июнь","07":"Июль","08":"Август","09":"Сентябрь","10":"Октябрь","11":"Ноябрь","12":"Декабрь"}
    
    for r in rows:
        dt = r[2]
        if dt.tzinfo is None: dt = dt.replace(tzinfo=None)
        monthly[dt.strftime("%Y-%m")].append((r[0], r[1]))
        
    averages = []
    for mk in sorted(monthly.keys()):
        d = monthly[mk]
        averages.append({
            "month_key": mk, 
            "month_name": month_names.get(mk.split("-")[1], "Месяц"), 
            "jackpot_avg": round(sum(x[0] for x in d)/len(d), 1), 
            "aif_avg": round(sum(x[1] for x in d)/len(d), 1)
        })
    return {"latest": latest_data, "monthly_averages": averages}
