from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
import sqlite3

router = APIRouter()
templates = Jinja2Templates(directory="templates")

from services.user_service import user_service

# 更新现有的路由函数
async def get_user_dashboard_data(request, user, db):
    data = await user_service.get_user_dashboard_data(request, user, db)
    return templates.TemplateResponse("user_dashboard.html", {
        "request": request,
        "user": user,
        "dashboard_data": data
    })

async def get_user_projects_data(request, user, project_type, db):
    projects = await user_service.get_user_projects_data(request, user, project_type, db)
    return templates.TemplateResponse("user_projects.html", {
        "request": request,
        "user": user,
        "projects": projects,
        "project_type": project_type
    })

async def get_user_reports_data(request, user, report_type, db):
    reports = await user_service.get_user_reports_data(request, user, report_type, db)
    return templates.TemplateResponse("user_reports.html", {
        "request": request,
        "user": user,
        "reports": reports,
        "report_type": report_type
    })

async def get_user_profile_data(request, user, db):
    profile_data = await user_service.get_user_profile_data(request, user, db)
    return templates.TemplateResponse("user_profile.html", {
        "request": request,
        "user": user,
        "profile_data": profile_data
    })

@router.get("/user_manager", response_class=HTMLResponse)
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
        # 获取用户资质
        c.execute("SELECT qualification_type FROM user_qualifications WHERE username = ?", (user_row[0],))
        qualifications = [row[0] for row in c.fetchall()]
        
        users_list.append({
            'username': user_row[0],
            'realname': user_row[1],
            'user_type': user_row[2],
            'password': user_row[3],
            'qualifications': qualifications  # 添加资质信息
        })
    
    return templates.TemplateResponse("user_manager.html", {
        "request": request,
        "users": users_list,
        "user": user
    })

@router.get("/user_dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户首页 - Dashboard"""
    return await get_user_dashboard_data(request, user, db)

@router.get("/user_projects", response_class=HTMLResponse)
async def user_projects(
    request: Request,
    type: str = "participated",  # participated, created, responsible
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户项目页面"""
    return await get_user_projects_data(request, user, type, db)

@router.get("/user_reports", response_class=HTMLResponse)
async def user_reports(
    request: Request,
    type: str = "created",  # created, reviewed, signed
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户报告页面"""
    return await get_user_reports_data(request, user, type, db)

@router.get("/user_profile", response_class=HTMLResponse)
async def user_profile(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户个人信息页面"""
    return await get_user_profile_data(request, user, db)