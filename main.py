from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3, os, shutil

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")  # Session 密钥
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 初始化数据库
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    project_id TEXT,
    filename TEXT
)
""")
conn.commit()

# 静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

ADMIN_USER = "admin"
ADMIN_PASS = "123456"  # 可修改为更安全的密码

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(username: str = Form(...), project_id: str = Form(...), file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    conn.execute("INSERT INTO projects (username, project_id, filename) VALUES (?, ?, ?)",
                 (username, project_id, file.filename))
    conn.commit()
    return RedirectResponse("/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USER and password == ADMIN_PASS:
        request.session["is_admin"] = True
        return RedirectResponse("/admin", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
def admin_view(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/login")
    cursor = conn.execute("SELECT * FROM projects")
    rows = cursor.fetchall()
    return templates.TemplateResponse("admin.html", {"request": request, "rows": rows})
