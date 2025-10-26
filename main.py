from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os
from datetime import datetime
from typing import List, Optional
import secrets
from contextlib import contextmanager
import threading
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

app = FastAPI(title="项目管理系统")

# 静态文件和模板配置
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
#app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")  # ✅ 添加这一行

# 上传文件夹配置
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 会话存储
sessions = {}
# 线程锁用于会话操作
session_lock = threading.Lock()

# --- 数据库连接池 ---
class Database:
    def __init__(self, db_path='db.sqlite3'):
        self.db_path = db_path
        self.local = threading.local()
        self.init_db()
    
    def get_connection(self):
        """为每个线程创建独立的数据库连接"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.connection.row_factory = sqlite3.Row  # 返回字典-like对象
        return self.local.connection
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            del self.local.connection
    
    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        realname TEXT,
                        user_type TEXT,
                        password TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        creator TEXT,
                        amount REAL,
                        start_date TEXT,
                        end_date TEXT,
                        contract_file TEXT,
                        asset_files TEXT,
                        status TEXT)''')
        conn.commit()
    
    @contextmanager
    def get_db(self):
        """数据库上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            # 注意：这里不关闭连接，因为连接是线程专用的
            pass

# 创建数据库实例
db_manager = Database()

# --- 依赖项 ---
def get_db():
    """数据库依赖"""
    with db_manager.get_db() as conn:
        yield conn

def get_current_user(request: Request):
    """获取当前用户"""
    session_id = request.cookies.get("session_id")
    with session_lock:
        if session_id and session_id in sessions:
            return sessions[session_id]
    return None


def login_required(request: Request):
    """检查登录状态"""
    session_id = request.cookies.get("session_id")
    with session_lock:
        if not session_id or session_id not in sessions:
            # 未登录时跳转登录页面
            raise HTTPException(
                status_code=HTTP_303_SEE_OTHER,
                detail="Redirect to login",
                headers={"Location": "/login"}
            )
        return sessions[session_id]


# --- 工具函数 ---
def secure_filename(filename: str) -> str:
    """安全的文件名"""
    if not filename:
        return ""
    return "".join(c for c in filename if c.isalnum() or c in ".-_ ").rstrip()

# --- 路由 ---
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    
    if user:
        # 创建会话
        session_id = secrets.token_urlsafe(16)
        user_data = {
            "username": username,
            "user_type": user[3]
        }
        with session_lock:
            sessions[session_id] = user_data
        
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "用户名或密码错误"
        })

@app.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("SELECT * FROM projects ORDER BY start_date DESC")
    projects = c.fetchall()
    
    # 转换为列表便于模板使用
    projects_list = []
    years = set()  # 用于存储有项目的年份
    
    for project in projects:
        project_dict = {
            'id': project[0],
            'name': project[1],
            'creator': project[2],
            'amount': project[3],
            'start_date': project[4],
            'end_date': project[5],
            'contract_file': project[6],
            'asset_files': project[7],
            'status': project[8] if len(project) > 8 else 'active',  # 默认状态为进行中
        }
        projects_list.append(project_dict)
        
        # 从开始日期提取年份
        if project_dict['start_date']:
            try:
                year = project_dict['start_date'][:4]  # 提取前4位作为年份
                if year.isdigit() and len(year) == 4:
                    years.add(int(year))
            except (ValueError, IndexError, AttributeError):
                pass
    
    # 按年份降序排列
    years_sorted = sorted(years, reverse=True) if years else []
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "projects": projects_list,
        "years": years_sorted,
        "user": user
    })

@app.get("/user_manager", response_class=HTMLResponse)
async def user_manager(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("SELECT username, realname, user_type, password FROM users")
    users = c.fetchall()
    
    users_list = []
    for user_row in users:
        users_list.append({
            'username': user_row[0],
            'realname': user_row[1],
            'user_type': user_row[2],
            'password': user_row[3]
        })
    
    return templates.TemplateResponse("user_manager.html", {
        "request": request,
        "users": users_list,
        "user": user
    })

@app.get("/create_project", response_class=HTMLResponse)
async def create_project_page(
    request: Request,
    user: dict = Depends(login_required)
):
    return templates.TemplateResponse("create_project.html", {
        "request": request,
        "user": user,
        "username": user["username"]  # 显式传递用户名
    })

# from typing import Optional, List
# from fastapi import File, Form, UploadFile, HTTPException
# from datetime import datetime
# from starlette.responses import RedirectResponse
# import os, sqlite3
# from werkzeug.utils import secure_filename

# UPLOAD_FOLDER = "uploads"

@app.post("/create_project")
async def create_project(
    request: Request,
    name: str = Form(...),
    creator: str = Form(...),
    amount: float = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    contract_file: Optional[UploadFile] = File(None),
    asset_files: Optional[List[UploadFile]] = File(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        # 1️⃣ 保存合同文件（可选）
        contract_path = None
        if contract_file and contract_file.filename:
            contract_filename = secure_filename(contract_file.filename)
            contract_path = os.path.join(UPLOAD_FOLDER, contract_filename)
            with open(contract_path, "wb") as f:
                f.write(await contract_file.read())

        # 2️⃣ 保存资产文件（可选）
        asset_paths = []
        if asset_files:
            for asset_file in asset_files:
                if asset_file.filename:
                    asset_filename = secure_filename(asset_file.filename)
                    asset_path = os.path.join(UPLOAD_FOLDER, asset_filename)
                    with open(asset_path, "wb") as f:
                        f.write(await asset_file.read())
                    asset_paths.append(asset_path)

        # 3️⃣ 插入数据库
        c = db.cursor()
        c.execute("""
            INSERT INTO projects 
            (name, creator, amount, start_date, end_date, contract_file, asset_files) 
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            name, creator, amount, start_date, end_date,
            contract_path or "", ','.join(asset_paths) or "",
        ))
        db.commit()

        return RedirectResponse(url="/admin", status_code=303)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@app.get("/project/{project_id}", response_class=HTMLResponse)
async def project_info(
    request: Request,
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("SELECT * FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project_dict = {
        'id': project[0],
        'name': project[1],
        'creator': project[2],
        'amount': project[3],
        'start_date': project[4],
        'end_date': project[5],
        'contract_file': project[6],
        'asset_files': project[7],
    }
    
    return templates.TemplateResponse("project_info.html", {
        "request": request,
        "project": project_dict,
        "user": user
    })

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        with session_lock:
            if session_id in sessions:
                del sessions[session_id]
    
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response

# 应用关闭时关闭所有数据库连接
@app.on_event("shutdown")
def shutdown_event():
    db_manager.close_connection()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)