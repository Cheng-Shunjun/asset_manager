from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
import sqlite3

router = APIRouter()
templates = Jinja2Templates(directory="templates")

from services.user_service import user_service

@router.get("/user_dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户首页 - Dashboard"""
    data = await user_service.get_user_dashboard_data(request, user, db)
    return templates.TemplateResponse("user_dashboard.html", {
        "request": request,
        "user": user,
        "dashboard_data": data
    })

@router.get("/user_projects", response_class=HTMLResponse)
async def user_projects(
    request: Request,
    type: str = "participated",  # participated, created, responsible
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户项目页面"""
    projects = await user_service.get_user_projects_data(request, user, type, db)
    return templates.TemplateResponse("user_projects.html", {
        "request": request,
        "user": user,
        "projects": projects,
        "project_type": type
    })

@router.get("/user_reports", response_class=HTMLResponse)
async def user_reports(
    request: Request,
    type: str = "created",  # created, reviewed, signed
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户报告页面"""
    reports = await user_service.get_user_reports_data(request, user, type, db)
    return templates.TemplateResponse("user_reports.html", {
        "request": request,
        "user": user,
        "reports": reports,
        "report_type": type
    })

@router.get("/user_profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户个人信息页面"""
    profile_data = await get_user_profile_data(request, user, db)
    return templates.TemplateResponse("user_profile.html", {
        "request": request,
        "user": user,
        "user_profile": profile_data["user_profile"],
        "user_qualifications": profile_data["user_qualifications"],
        "stats": profile_data["stats"]
    })

async def get_user_profile_data(request, user, db):
    """获取用户个人信息数据"""
    c = db.cursor()
    
    # 获取用户详细信息
    c.execute("""
        SELECT username, realname, user_type, phone, email, 
               hire_date, education, position, department 
        FROM users WHERE username = ?
    """, (user["username"],))
    
    user_data = c.fetchone()
    user_profile = dict(user_data) if user_data else {}
    
    # 获取用户资质
    c.execute("""
        SELECT qualification_type, qualification_number, 
               issue_date, expiry_date, issue_authority 
        FROM user_qualifications WHERE username = ?
    """, (user["username"],))
    
    user_qualifications = [dict(row) for row in c.fetchall()]
    
    # 获取用户统计信息
    stats = await get_user_basic_stats(user, db)
    
    return {
        "user_profile": user_profile,
        "user_qualifications": user_qualifications,
        "stats": stats
    }

async def get_user_basic_stats(user, db):
    """获取用户基本统计信息"""
    c = db.cursor()
    username = user["username"]
    
    # 负责的项目数
    c.execute("SELECT COUNT(*) FROM projects WHERE project_leader = ?", (username,))
    responsible_projects = c.fetchone()[0]
    
    # 参与的项目数
    c.execute("""
        SELECT COUNT(DISTINCT p.id) FROM projects p
        LEFT JOIN reports r ON p.id = r.project_id
        WHERE p.project_leader = ? OR p.market_leader = ? OR p.creator = ?
           OR r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
           OR r.signer1 = ? OR r.signer2 = ?
    """, (username, username, username, username, username, username, username, username))
    participated_projects = c.fetchone()[0]
    
    # 创建的报告数
    c.execute("SELECT COUNT(*) FROM reports WHERE creator = ?", (username,))
    created_reports = c.fetchone()[0]
    
    return {
        "responsible_projects": responsible_projects,
        "participated_projects": participated_projects,
        "created_reports": created_reports
    }