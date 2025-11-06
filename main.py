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
                        project_no TEXT,                 -- ① 项目序号
                        name TEXT,                       -- ② 项目名称
                        project_type TEXT,               -- ③ 项目类型
                        client_name TEXT,                -- ④ 甲方名称
                        market_leader TEXT,              -- ⑤ 市场部负责人
                        project_leader TEXT,             -- ⑥ 项目负责人
                        progress TEXT,                   -- ⑦ 项目进度
                        report_numbers TEXT,             -- ⑧ 报告号（多个以逗号分隔）
                        amount REAL,                     -- ⑨ 合同金额
                        is_paid TEXT,                    -- ⑩ 是否收费（是/否）
                        creator TEXT,                    -- ⑪ 项目创建人
                        start_date TEXT,                 -- ⑫ 开始日期
                        end_date TEXT,                   -- ⑬ 结束日期
                        status TEXT,                     -- ⑭ 状态
                        contract_file TEXT,
                        create_date TEXT
                    )''')
        
        # 修改报告表，添加复核人和签字人字段
        c.execute('''CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_no TEXT NOT NULL,         -- 报告号
                        project_id INTEGER,              -- 关联的项目ID
                        file_paths TEXT,                 -- 文件路径（多个以逗号分隔）
                        creator TEXT,                    -- 创建人
                        create_date TEXT,                -- 创建日期
                        reviewer1 TEXT,                  -- 复核人1
                        reviewer2 TEXT,                  -- 复核人2
                        reviewer3 TEXT,                  -- 复核人3
                        signer1 TEXT,                    -- 签字人1
                        signer2 TEXT,                    -- 签字人2
                        FOREIGN KEY (project_id) REFERENCES projects (id)
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS report_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id INTEGER,                    -- 关联的报告ID
                        file_path TEXT NOT NULL,              -- 文件路径
                        file_name TEXT NOT NULL,              -- 原文件名
                        uploader_username TEXT NOT NULL,      -- 上传者用户名
                        uploader_realname TEXT NOT NULL,      -- 上传者真实姓名
                        upload_time TEXT NOT NULL,            -- 上传时间
                        file_size INTEGER,                    -- 文件大小（字节）
                        FOREIGN KEY (report_id) REFERENCES reports (id)
                    )''')
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

    projects_list = []
    years = set()

    for p in projects:
        project_dict = {
            "id": p["id"],
            "project_no": p["project_no"],
            "name": p["name"],
            "project_type": p["project_type"],
            "client_name": p["client_name"],
            "market_leader": p["market_leader"],
            "project_leader": p["project_leader"],
            "progress": p["progress"],
            "report_numbers": p["report_numbers"],
            "amount": p["amount"],
            "is_paid": p["is_paid"],
            "creator": p["creator"],
            "start_date": p["start_date"],
            "end_date": p["end_date"],
            "status": p["status"],
            "create_Date": p["create_date"]
        }
        projects_list.append(project_dict)
        if p["start_date"]:
            years.add(int(p["start_date"][:4]))

    years_sorted = sorted(years, reverse=True)

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

@app.get("/create_project")
async def create_project_page(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    # 获取所有用户列表用于负责人选择
    c = db.cursor()
    c.execute("SELECT username FROM users")
    users = [{"username": row[0]} for row in c.fetchall()]
    
    return templates.TemplateResponse("create_project.html", {
        "request": request,
        "username": user["username"],
        "users": users
    })

def generate_project_no(db: sqlite3.Connection) -> str:
    """生成项目编号：P2025_031 格式"""
    current_year = datetime.now().year
    
    # 查询今年已有的项目数量
    c = db.cursor()
    c.execute("""
        SELECT COUNT(*) FROM projects 
        WHERE project_no LIKE ?
    """, (f"P{current_year}_%",))
    
    current_count = c.fetchone()[0]
    next_number = current_count + 1
    
    # 格式化为三位数，如 001, 031, 125
    project_no = f"P{current_year}_{next_number:03d}"
    return project_no

from datetime import datetime

@app.post("/create_project")
async def create_project(
    request: Request,
    name: str = Form(...),
    project_type: str = Form(...),
    client_name: str = Form(...),
    market_leader: str = Form(...),
    project_leader: str = Form(...),
    amount: float = Form(0.0),
    creator: str = Form(...),
    start_date: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        # 生成项目编号
        project_no = generate_project_no(db)
        
        # 获取当前时间作为创建日期
        create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 设置默认值
        progress = "洽谈中"
        report_numbers = ""
        is_paid = "否"
        end_date = start_date
        status = "active"
        
        # 插入数据库
        c = db.cursor()
        c.execute("""
            INSERT INTO projects (
                project_no, name, project_type, client_name, market_leader, 
                project_leader, progress, report_numbers, amount, is_paid, 
                creator, start_date, end_date, status, contract_file, create_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_no,
            name, 
            project_type,
            client_name, 
            market_leader,
            project_leader,
            progress, 
            report_numbers, 
            amount, 
            is_paid, 
            creator, 
            start_date, 
            end_date, 
            status,
            "",  # 合同文件默认为空
            create_date,
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
    
    # 使用列名来查询，包含 create_date，移除 report_files
    c.execute("""
        SELECT 
            id, project_no, name, project_type, client_name, 
            market_leader, project_leader, progress, report_numbers, 
            amount, is_paid, creator, start_date, end_date, 
            status, contract_file, create_date
        FROM projects WHERE id=?
    """, (project_id,))
    
    project = c.fetchone()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 获取列名
    columns = [description[0] for description in c.description]
    
    # 创建字典映射
    project_dict = dict(zip(columns, project))
    
    # 获取该项目的所有报告（包含复核人和签字人信息）
    c.execute("""
        SELECT id, report_no, file_paths, creator, create_date, 
               reviewer1, reviewer2, reviewer3, signer1, signer2
        FROM reports WHERE project_id = ? ORDER BY create_date DESC
    """, (project_id,))
    
    reports = []
    for row in c.fetchall():
        report_data = {
            "id": row[0],
            "report_no": row[1],
            "file_paths": row[2],
            "creator": row[3],
            "create_date": row[4],
            "reviewer1": row[5],
            "reviewer2": row[6],
            "reviewer3": row[7],
            "signer1": row[8],
            "signer2": row[9],
            "files": []  # 添加文件详细信息
        }
        
        # 获取该报告的详细文件信息
        c.execute("""
            SELECT rf.id, rf.file_path, rf.file_name, rf.uploader_username, 
                   rf.uploader_realname, rf.upload_time, rf.file_size
            FROM report_files rf
            WHERE rf.report_id = ?
            ORDER BY rf.upload_time DESC
        """, (row[0],))
        
        file_info = c.fetchall()
        for file_row in file_info:
            report_data["files"].append({
                "id": file_row[0],
                "file_path": file_row[1],
                "file_name": file_row[2],
                "uploader_username": file_row[3],
                "uploader_realname": file_row[4],
                "upload_time": file_row[5],
                "file_size": file_row[6]
            })
        
        reports.append(report_data)
    
    # 获取所有用户列表用于选择复核人和签字人（包含真实姓名）
    c.execute("SELECT username, realname FROM users")
    users_data = c.fetchall()
    # 创建包含用户名和真实姓名的用户列表
    users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
    
    return templates.TemplateResponse("project_info.html", {
        "request": request,
        "project": project_dict,
        "reports": reports,
        "users": users,  # 传递包含真实姓名的用户列表
        "user": user
    })

# 暂停项目
@app.post("/project/{project_id}/pause")
async def pause_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("UPDATE projects SET status = 'paused' WHERE id = ?", (project_id,))
    db.commit()
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)

# 继续项目（从暂停状态恢复）
@app.post("/project/{project_id}/resume")
async def resume_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("UPDATE projects SET status = 'active' WHERE id = ?", (project_id,))
    db.commit()
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)

# 结束项目
@app.post("/project/{project_id}/complete")
async def complete_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("UPDATE projects SET status = 'completed' WHERE id = ?", (project_id,))
    db.commit()
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)

# 重新开启项目（从已完成或已取消状态恢复）
@app.post("/project/{project_id}/reopen")
async def reopen_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("UPDATE projects SET status = 'active' WHERE id = ?", (project_id,))
    db.commit()
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)

# 添加合同文件（支持多文件）
@app.post("/project/{project_id}/add_contract")
async def add_contract_files(
    project_id: int,
    contract_files: List[UploadFile] = File(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    # 检查项目状态
    c = db.cursor()
    c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
    result = c.fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    status = result[0]
    if status in ['completed', 'paused', 'cancelled']:
        raise HTTPException(status_code=400, detail=f"项目状态为{status}，无法添加文件")
    
    # 保存文件
    contract_paths = []
    for contract_file in contract_files:
        if contract_file.filename:
            contract_filename = secure_filename(contract_file.filename)
            contract_path = os.path.join(UPLOAD_FOLDER, contract_filename)
            with open(contract_path, "wb") as f:
                content = await contract_file.read()
                f.write(content)
            contract_paths.append(contract_path)
    
    if contract_paths:
        # 获取现有的合同文件
        c.execute("SELECT contract_file FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        existing_files = result[0] if result and result[0] else ""
        
        # 更新数据库
        if existing_files:
            new_files = existing_files + "," + ",".join(contract_paths)
        else:
            new_files = ",".join(contract_paths)
        
        c.execute("UPDATE projects SET contract_file = ? WHERE id = ?", (new_files, project_id))
        db.commit()
    
    return RedirectResponse(url=f"/project/{project_id}", status_code=303)

# 更新报告信息
@app.post("/project/{project_id}/update_report/{report_no}")
async def update_report(
    project_id: int,
    report_no: str,
    reviewer1: str = Form(None),
    reviewer2: str = Form(None),
    reviewer3: str = Form(None),
    signer1: str = Form(None),
    signer2: str = Form(None),
    report_files: List[UploadFile] = File([]),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        # 检查项目状态
        c = db.cursor()
        c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        status = result[0]
        if status in ['completed', 'paused', 'cancelled']:
            raise HTTPException(status_code=400, detail=f"项目状态为{status}，无法更新报告")
        
        # 获取现有的报告信息
        c.execute("SELECT id, file_paths, reviewer1, reviewer2, reviewer3, signer1, signer2 FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="报告不存在")
        
        report_id = result[0]
        existing_files = result[1] if result[1] else ""
        existing_reviewer1 = result[2]
        existing_reviewer2 = result[3]
        existing_reviewer3 = result[4]
        existing_signer1 = result[5]
        existing_signer2 = result[6]
        
        # 保存新上传的文件并记录信息
        file_paths = []
        for report_file in report_files:
            if report_file.filename:
                report_filename = secure_filename(report_file.filename)
                report_path = os.path.join(UPLOAD_FOLDER, report_filename)
                
                # 保存文件
                with open(report_path, "wb") as f:
                    content = await report_file.read()
                    f.write(content)
                
                file_paths.append(report_path)
                
                # 获取文件大小
                file_size = os.path.getsize(report_path)
                
                # 获取上传者真实姓名
                c.execute("SELECT realname FROM users WHERE username = ?", (user["username"],))
                uploader_realname_result = c.fetchone()
                uploader_realname = uploader_realname_result[0] if uploader_realname_result else user["username"]
                
                # 记录文件信息到数据库
                upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO report_files 
                    (report_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    report_path,
                    report_file.filename,
                    user["username"],
                    uploader_realname,
                    upload_time,
                    file_size
                ))
        
        # 合并文件路径
        if file_paths:
            if existing_files:
                all_files = existing_files + "," + ",".join(file_paths)
            else:
                all_files = ",".join(file_paths)
        else:
            all_files = existing_files
        
        # 确定要更新的字段值
        # 如果表单没有提交某个字段（值为None），则保持原有值
        final_reviewer1 = reviewer1 if reviewer1 is not None else existing_reviewer1
        final_reviewer2 = reviewer2 if reviewer2 is not None else existing_reviewer2
        final_reviewer3 = reviewer3 if reviewer3 is not None else existing_reviewer3
        final_signer1 = signer1 if signer1 is not None else existing_signer1
        final_signer2 = signer2 if signer2 is not None else existing_signer2
        
        # 验证复核人：必须3个都有且不能重复
        reviewers = [final_reviewer1, final_reviewer2, final_reviewer3]
        
        # 检查是否有空值
        if not all(reviewers):
            raise HTTPException(status_code=400, detail="必须设置3个复核人，不能有空缺")
        
        # 检查是否有重复
        if len(reviewers) != len(set(reviewers)):
            raise HTTPException(status_code=400, detail="复核人不能重复，请选择3个不同的复核人")
        
        # 验证签字人：必须2个都有且不能重复
        signers = [final_signer1, final_signer2]
        
        # 检查是否有空值
        if not all(signers):
            raise HTTPException(status_code=400, detail="必须设置2个签字人，不能有空缺")
        
        # 检查是否有重复
        if len(signers) != len(set(signers)):
            raise HTTPException(status_code=400, detail="签字人不能重复，请选择2个不同的签字人")
        
        # 更新报告信息
        c.execute("""
            UPDATE reports 
            SET reviewer1 = ?, reviewer2 = ?, reviewer3 = ?, 
                signer1 = ?, signer2 = ?, file_paths = ?
            WHERE report_no = ? AND project_id = ?
        """, (
            final_reviewer1, final_reviewer2, final_reviewer3,
            final_signer1, final_signer2, all_files,
            report_no, project_id
        ))
        
        db.commit()
        return RedirectResponse(url=f"/project/{project_id}", status_code=303)
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新报告失败: {str(e)}")

# 报告取号
@app.post("/project/{project_id}/generate_report_no")
async def generate_report_no(
    project_id: int,
    report_type: str = Form(...),
    is_filing: str = Form(None),
    reviewer1: str = Form(...),
    reviewer2: str = Form(...),
    reviewer3: str = Form(...),
    signer1: str = Form(...),
    signer2: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        # 检查项目状态
        c = db.cursor()
        c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        status = result[0]
        if status != 'active':
            raise HTTPException(status_code=400, detail="只有进行中的项目可以生成报告号")
        
        # 验证复核人重复
        reviewers = [reviewer1, reviewer2, reviewer3]
        if len(reviewers) != len(set(reviewers)):
            raise HTTPException(status_code=400, detail="复核人不能重复，请选择3个不同的复核人")
        
        # 验证签字人重复
        signers = [signer1, signer2]
        if len(signers) != len(set(signers)):
            raise HTTPException(status_code=400, detail="签字人不能重复，请选择2个不同的签字人")
        
        # 获取当前日期
        now = datetime.now()
        current_year = now.year
        current_month = now.strftime("%m")  # 两位数的月份
        
        # 报告类型映射
        report_type_prefixes = {
            "房地产咨询报告": "房咨",
            "房地产估价报告": "房估",
            "资产评估报告": "评报",
            "资产估值报告": "估评",
            "资产咨询报告": "咨评",
            "土地报告": "土估"
        }
        
        # 需要备案的报告类型
        filing_required_types = ["房地产估价报告", "资产评估报告", "土地报告"]
        
        # 验证报告类型
        if report_type not in report_type_prefixes:
            raise HTTPException(status_code=400, detail="无效的报告类型")
        
        # 验证备案选择
        if report_type in filing_required_types and not is_filing:
            raise HTTPException(status_code=400, detail=f"{report_type}需要选择是否备案")
        
        # 构建查询条件
        report_prefix = report_type_prefixes[report_type]
        year_pattern = f"[{current_year}]字第"
        
        # 查询当月同类型报告的所有序号
        if report_type in filing_required_types and is_filing == "是":
            # 备案的报告：查找 A月份XXX 格式的序号
            pattern = f"%{report_prefix}{year_pattern}A{current_month}%"
        else:
            # 未备案的报告：查找 月份XXX 格式的序号
            pattern = f"%{report_prefix}{year_pattern}{current_month}%"
        
        c.execute("""
            SELECT report_no FROM reports 
            WHERE report_no LIKE ? AND project_id = ?
        """, (pattern, project_id))
        
        existing_reports = c.fetchall()
        
        # 提取现有的序号
        existing_numbers = []
        for report in existing_reports:
            report_no = report[0]
            # 提取序号部分
            if report_type in filing_required_types and is_filing == "是":
                # 备案报告格式：川鼎土估[2025]字第A11001号
                # 提取 A11 后面的数字部分
                prefix_len = len(f"川鼎{report_prefix}{year_pattern}A{current_month}")
                number_part = report_no[prefix_len:-1]  # 去掉最后的"号"
            else:
                # 未备案报告格式：川鼎土估[2025]字第11001号
                # 提取 11 后面的数字部分
                prefix_len = len(f"川鼎{report_prefix}{year_pattern}{current_month}")
                number_part = report_no[prefix_len:-1]  # 去掉最后的"号"
            
            if number_part.isdigit():
                existing_numbers.append(int(number_part))
        
        # 查找最小的可用序号（从1开始，查找缺失的编号）
        next_number = 1
        while next_number in existing_numbers:
            next_number += 1
        
        # 格式化序号为三位数
        sequence_no = f"{next_number:03d}"
        
        # 生成报告号
        prefix = "川鼎"
        middle = f"[{current_year}]字第"
        
        if report_type in filing_required_types and is_filing == "是":
            # 备案的报告号格式：第A11001号
            suffix = f"A{current_month}{sequence_no}号"
        else:
            # 未备案的报告号格式：第11001号
            suffix = f"{current_month}{sequence_no}号"
        
        report_no = f"{prefix}{report_type_prefixes[report_type]}{middle}{suffix}"
        
        # 保存报告号到数据库
        create_date = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 插入报告记录（包含复核人和签字人）
        c.execute("""
            INSERT INTO reports (
                report_no, project_id, file_paths, creator, create_date,
                reviewer1, reviewer2, reviewer3, signer1, signer2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_no,
            project_id,
            "",  # 文件路径为空
            user["username"],
            create_date,
            reviewer1,
            reviewer2,
            reviewer3,
            signer1,
            signer2
        ))
        
        # 更新项目的报告号列表
        c.execute("SELECT report_numbers FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        existing_report_numbers = result[0] if result and result[0] else ""
        
        if existing_report_numbers:
            new_report_numbers = existing_report_numbers + "," + report_no
        else:
            new_report_numbers = report_no
        
        c.execute("UPDATE projects SET report_numbers = ? WHERE id = ?", (new_report_numbers, project_id))
        
        db.commit()
        
        # 返回报告号
        return {"report_no": report_no}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"生成报告号失败: {str(e)}")

# 删除报告
@app.post("/project/{project_id}/delete_report/{report_no}")
async def delete_report(
    project_id: int,
    report_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        c = db.cursor()
        
        # 检查项目状态
        c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        status = result[0]
        if status != 'active':
            raise HTTPException(status_code=400, detail="只有进行中的项目可以删除报告")
        
        # 获取报告ID和文件路径
        c.execute("SELECT id, file_paths FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="报告不存在")
        
        report_id = result[0]
        file_paths = result[1]
        
        # 获取报告的所有文件信息（从 report_files 表）
        c.execute("SELECT file_path FROM report_files WHERE report_id = ?", (report_id,))
        file_records = c.fetchall()
        
        # 删除物理文件（从 report_files 表获取的文件路径）
        for file_record in file_records:
            file_path = file_record[0]
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ 已删除文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除文件失败 {file_path}: {e}")
        
        # 同时删除原有的文件路径中的文件（为了兼容性）
        if file_paths:
            for file_path in file_paths.split(','):
                if file_path.strip() and os.path.exists(file_path.strip()):
                    try:
                        os.remove(file_path.strip())
                        print(f"🗑️ 已删除文件: {file_path.strip()}")
                    except Exception as e:
                        print(f"⚠️ 删除文件失败 {file_path.strip()}: {e}")
        
        # 删除 report_files 表中的文件记录
        c.execute("DELETE FROM report_files WHERE report_id = ?", (report_id,))
        
        # 从 reports 表中删除报告记录
        c.execute("DELETE FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
        
        # 更新项目的 report_numbers 字段
        c.execute("SELECT report_numbers FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        
        if result and result[0]:
            existing_report_numbers = result[0]
            # 从报告号列表中移除被删除的报告号
            report_list = existing_report_numbers.split(',')
            if report_no in report_list:
                report_list.remove(report_no)
                new_report_numbers = ','.join(report_list) if report_list else ""
                c.execute("UPDATE projects SET report_numbers = ? WHERE id = ?", (new_report_numbers, project_id))
        
        db.commit()
        
        return RedirectResponse(url=f"/project/{project_id}", status_code=303)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除报告失败: {str(e)}")
    
# 更新项目进度
@app.post("/project/{project_id}/update_progress")
async def update_progress(
    project_id: int,
    progress: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        # 检查项目状态
        c = db.cursor()
        c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        result = c.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        status = result[0]
        if status != 'active':
            raise HTTPException(status_code=400, detail="只有进行中的项目可以更新进度")
        
        # 验证进度描述长度
        if len(progress) > 50:
            raise HTTPException(status_code=400, detail="进度描述不能超过50字")
        
        # 更新项目进度
        c.execute("UPDATE projects SET progress = ? WHERE id = ?", (progress, project_id))
        db.commit()
        
        return RedirectResponse(url=f"/project/{project_id}", status_code=303)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新进度失败: {str(e)}")

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