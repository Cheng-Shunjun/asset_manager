from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
from datetime import datetime
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
    try:
        print(f"用户个人信息页面，用户名: {user['username']}")
        
        # 使用 user_service 获取用户个人信息
        user_profile = await user_service.get_user_profile(user["username"], db)
        
        # 获取用户资质信息
        user_qualifications = await user_service.get_user_qualifications(user["username"], db)
        
        # 获取用户统计信息
        stats = await get_user_basic_stats(user, db)

        today = datetime.now().strftime("%Y-%m-%d")

        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "user": user,
            "user_profile": user_profile,
            "user_qualifications": user_qualifications,  # 添加资质信息
            "stats": stats,
            "today": today
        })
    except Exception as e:
        # 如果获取个人信息失败，返回默认页面
        print(f"查询失败！！！错误: {str(e)}")
        import traceback
        print(f"完整错误: {traceback.format_exc()}")
        
        return templates.TemplateResponse("user_profile.html", {
            "request": request,
            "user": user,
            "user_profile": {},
            "user_qualifications": [],  # 空列表
            "stats": {},
            "today": today,
            "error": str(e)
        })

@router.post("/user_profile/update")
async def update_user_profile(
    request: Request,
    realname: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    department: str = Form(None),
    position: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """更新用户个人信息"""
    try:
        profile_data = {
            "realname": realname,
            "email": email,
            "phone": phone,
            "department": department,
            "position": position
        }
        
        # 移除空值
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        result = await user_service.update_user_profile(user["username"], profile_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)

@router.post("/user_profile/change_password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """修改用户密码"""
    try:
        print(current_password)
        print(new_password)
        print(new_password)
        # 验证新密码和确认密码是否匹配
        if new_password != confirm_password:
            return JSONResponse({
                "success": False, 
                "message": "新密码和确认密码不匹配"
            }, status_code=400)
        
        # 验证密码长度
        if len(new_password) < 8:
            return JSONResponse({
                "success": False,
                "message": "密码长度至少8位"
            }, status_code=400)
        
        # 可选：验证密码强度（包含字母和数字）
        import re
        if not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password):
            return JSONResponse({
                "success": False,
                "message": "密码应包含字母和数字"
            }, status_code=400)
        
        # 可选：验证不能与当前密码相同
        if new_password == current_password:
            return JSONResponse({
                "success": False,
                "message": "新密码不能与当前密码相同"
            }, status_code=400)
        
        password_data = {
            "current_password": current_password,
            "new_password": new_password
        }
        
        result = await user_service.change_password(user["username"], password_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)

# @router.get("/user_profile/data")
# async def get_user_profile_data(
#     user: dict = Depends(login_required),
#     db: sqlite3.Connection = Depends(get_db)
# ):
#     """获取用户个人信息数据（API接口）"""
#     try:
#         user_profile = await user_service.get_user_profile(user["username"], db)
#         return JSONResponse({"success": True, "data": user_profile})
#     except Exception as e:
#         return JSONResponse({"success": False, "message": str(e)}, status_code=400)

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