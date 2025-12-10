from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
from datetime import datetime
import sqlite3
from fastapi import UploadFile, File

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
        stats = await user_service.get_user_basic_stats(user, db)

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
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)\

@router.get("/user_manager", response_class=HTMLResponse)
async def user_manager(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """用户管理页面"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return RedirectResponse(url="/user_dashboard")
    
    try:
        # 获取所有用户信息
        users = await user_service.get_all_users(db)
        
        # 为每个用户获取资质信息
        for user_item in users:
            user_item["qualifications"] = await user_service.get_user_qualifications(user_item["username"], db)
        
        return templates.TemplateResponse("user_manager.html", {
            "request": request,
            "user": user,
            "users": users,
            "current_user": user["username"]
        })
    except Exception as e:
        return templates.TemplateResponse("user_manager.html", {
            "request": request,
            "user": user,
            "users": [],
            "current_user": user["username"],
            "error": str(e)
        })

@router.post("/user_manager/create")
async def create_user_route(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    realname: str = Form(None),
    user_type: str = Form(...),
    phone: str = Form(None),
    email: str = Form(None),
    hire_date: str = Form(None),
    education: str = Form(None),
    position: str = Form(None),
    department: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """创建新用户"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        user_data = {
            "username": username,
            "password": password,
            "realname": realname,
            "user_type": user_type,
            "phone": phone,
            "email": email,
            "hire_date": hire_date,
            "education": education,
            "position": position,
            "department": department
        }
        
        result = await user_service.create_user(user_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.post("/user_manager/update/{username}")
async def update_user_route(
    request: Request,
    username: str,
    realname: str = Form(None),
    user_type: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    hire_date: str = Form(None),
    education: str = Form(None),
    position: str = Form(None),
    department: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """更新用户信息"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        user_data = {
            "realname": realname,
            "user_type": user_type,
            "phone": phone,
            "email": email,
            "hire_date": hire_date,
            "education": education,
            "position": position,
            "department": department
        }
        
        # 移除空值
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        result = await user_service.update_user(username, user_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.post("/user_manager/delete/{username}")
async def delete_user_route(
    request: Request,
    username: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """删除用户"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        result = await user_service.delete_user(username, user["username"], db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.post("/user_manager/reset_password/{username}")
async def reset_user_password_route(
    request: Request,
    username: str,
    new_password: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """重置用户密码"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        # 验证密码长度
        if len(new_password) < 8:
            return JSONResponse({
                "success": False,
                "message": "密码长度至少8位"
            }, status_code=400)
        
        result = await user_service.reset_user_password(username, new_password, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.get("/user_manager/get_user/{username}")
async def get_user(
    request: Request,
    username: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """获取单个用户信息"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        user_details = await user_service.get_user_details(username, db)
        return JSONResponse({
            "success": True, 
            "user": user_details
        })
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.get("/admin/user_profile/{username}", response_class=HTMLResponse)
async def admin_user_profile(
    request: Request,
    username: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员查看用户详情页面"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return RedirectResponse(url="/user_dashboard")
    
    try:
        # 获取用户基本信息
        user_profile = await user_service.get_user_profile(username, db)
        
        # 获取用户资质信息
        user_qualifications = await user_service.get_user_qualifications(username, db)
        
        today = datetime.now().strftime("%Y-%m-%d")

        return templates.TemplateResponse("admin_user_profile.html", {
            "request": request,
            "current_user": user,  # 当前登录的管理员
            "user_profile": user_profile,
            "user_qualifications": user_qualifications,
            "today": today
        })
    except Exception as e:
        return RedirectResponse(url="/user_manager")

@router.post("/admin/user_profile/update/{username}")
async def admin_update_user_profile(
    request: Request,
    username: str,
    realname: str = Form(None),
    user_type: str = Form(None),
    status: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    department: str = Form(None),
    position: str = Form(None),
    education: str = Form(None),
    hire_date: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员更新用户信息"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        profile_data = {
            "realname": realname,
            "user_type": user_type,
            "status": status,
            "phone": phone,
            "email": email,
            "department": department,
            "position": position,
            "education": education,
            "hire_date": hire_date
        }
        
        # 移除空值
        profile_data = {k: v for k, v in profile_data.items() if v is not None}
        
        result = await user_service.update_user(username, profile_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=400)

@router.post("/admin/user_profile/add_qualification/{username}")
async def admin_add_user_qualification(
    request: Request,
    username: str,
    qualification_type: str = Form(...),
    qualification_number: str = Form(None),
    issue_authority: str = Form(None),
    issue_date: str = Form(None),
    expiry_date: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员添加用户资质"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        qualification_data = {
            "qualification_type": qualification_type,
            "qualification_number": qualification_number,
            "issue_authority": issue_authority,
            "issue_date": issue_date,
            "expiry_date": expiry_date
        }
        
        result = await user_service.add_user_qualification(username, qualification_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@router.post("/admin/user_profile/delete_qualification/{username}")
async def admin_delete_user_qualification(
    request: Request,
    username: str,
    qualification_type: str = Form(...),
    qualification_number: str = Form(None),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员删除用户资质"""
    # 检查用户权限
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        result = await user_service.delete_user_qualification(username, qualification_type, qualification_number, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/company_qualifications", response_class=HTMLResponse)
async def company_qualifications(
    request: Request,
    category: str = None,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """公司资质页面"""
    try:
        # 获取公司资质列表
        qualifications = await user_service.get_company_qualifications(category, db)
        
        # 获取资质类别列表（用于筛选器）
        categories = await user_service.get_qualification_categories(db)

        all_users = await user_service.get_all_users_for_qualifications(db)
        
        return templates.TemplateResponse("company_qualifications.html", {
            "request": request,
            "user": user,
            "all_users": all_users,
            "qualifications": qualifications,
            "categories": categories,
            "current_category": category or "all"
        })
    except Exception as e:
        return templates.TemplateResponse("company_qualifications.html", {
            "request": request,
            "user": user,
            "all_users": all_users,
            "qualifications": [],
            "categories": [],
            "current_category": category or "all",
            "error": str(e)
        })

@router.get("/company_qualifications/download/{qualification_id}")
async def download_company_qualification(
    request: Request,
    qualification_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """下载公司资质文件"""
    try:
        c = db.cursor()
        c.execute("""
            SELECT file_path, file_name 
            FROM company_qualifications 
            WHERE id = ? AND status = 'active'
        """, (qualification_id,))
        
        result = c.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="资质文件不存在")
        
        file_path = result[0]
        file_name = result[1]
        
        # 检查文件是否存在
        import os
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 返回文件流
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

@router.post("/admin/company_qualifications/add")
async def admin_add_company_qualification(
    request: Request,
    category: str = Form(...),
    owner: str = Form(None),
    certificate_file: UploadFile = File(...),
    file_name: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员添加公司资质（支持文件上传）"""
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        # 创建上传目录
        import os
        upload_dir = "static/uploads/company_qualifications"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 生成文件路径
        file_extension = certificate_file.filename.split('.')[-1]
        safe_filename = f"{certificate_file.filename.replace(' ', '_')}.{file_extension}"
        file_path = f"{upload_dir}/{safe_filename}"
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await certificate_file.read()
            buffer.write(content)
        
        qualification_data = {
            "category": category,
            "owner": owner,
            "file_path": file_path,
            "file_name": file_name,
            "uploader_username": user["username"]
        }
        
        result = await user_service.add_company_qualification(qualification_data, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.post("/admin/company_qualifications/delete/{qualification_id}")
async def admin_delete_company_qualification(
    request: Request,
    qualification_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员删除公司资质"""
    if user.get("user_type") != "admin":
        return JSONResponse({"success": False, "message": "权限不足"}, status_code=403)
    
    try:
        result = await user_service.delete_company_qualification(qualification_id, db)
        return JSONResponse({"success": True, "message": result["message"]})
    except HTTPException as e:
        return JSONResponse({"success": False, "message": e.detail}, status_code=e.status_code)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)