from fastapi import APIRouter, Request, Query, Form, Depends, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
from services.project_service import ProjectService
import sqlite3

router = APIRouter()
templates = Jinja2Templates(directory="templates")
project_service = ProjectService()

def admin_required(user: dict = Depends(login_required)):
    """管理员权限检查依赖"""
    if user.get("user_type") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="权限不足，只有管理员可以访问此页面"
        )
    return user

@router.get("/admin_projects", response_class=HTMLResponse)
async def admin(
    request: Request,
    page: int = Query(1, ge=1),  # 添加分页参数
    limit: int = Query(20, ge=1, le=100),  # 添加每页数量参数
    search: str = Query(None),  # 添加搜索参数
    status: str = Query("all"),  # 添加状态筛选参数
    year: str = Query(None),  # 添加年份筛选参数
    user: dict = Depends(admin_required),  # 使用管理员权限检查
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员后台页面 - 支持分页和搜索"""
    try:
        # 如果有搜索、筛选或分页参数，使用新的分页查询
        if search or status != "all" or year or page > 1 or limit != 20:
            # 获取分页的项目数据
            project_data = await project_service.get_admin_projects_paginated(
                page=page,
                limit=limit,
                search=search,
                status=status,
                year=year,
                db=db
            )
            
            # 获取所有项目的年份列表（用于年份筛选器）
            c = db.cursor()
            c.execute("""
                SELECT DISTINCT strftime('%Y', start_date) as year 
                FROM projects 
                WHERE start_date IS NOT NULL AND start_date != ''
                ORDER BY year DESC
            """)
            years = [row[0] for row in c.fetchall()]
            
            # 计算显示范围
            start_item = ((project_data["current_page"] - 1) * project_data["page_size"]) + 1
            end_item = min(project_data["current_page"] * project_data["page_size"], project_data["total_count"])
            
            return templates.TemplateResponse("admin_projects.html", {
                "request": request,
                "user": user,
                "projects": project_data["projects"],
                "years": years,
                "total_count": project_data["total_count"],
                "total_pages": project_data["total_pages"],
                "current_page": project_data["current_page"],
                "page_size": project_data["page_size"],
                "current_search": search,
                "current_status": status,
                "current_year": year,
                "start_item": start_item,
                "end_item": end_item
            })
        else:
            # 如果没有搜索参数，使用传统的获取方式
            return await project_service.get_admin_page(request, user, db)
    except Exception as e:
        print(f"分页查询失败，使用旧方式: {e}")
        # 如果分页查询失败，回退到旧的方式
        return await project_service.get_admin_page(request, user, db)

@router.get("/admin_projects/api")
async def get_admin_projects_api(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    status: str = Query("all"),
    year: str = Query(None),
    user: dict = Depends(admin_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员项目分页数据API"""
    try:
        project_data = await project_service.get_admin_projects_paginated(
            page=page,
            limit=limit,
            search=search,
            status=status,
            year=year,
            db=db
        )
        
        return {
            "success": True,
            "data": project_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取项目列表失败: {str(e)}"
        }

@router.get("/create_project")
async def create_project_page(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.get_create_project_page(request, user, db)

@router.post("/create_project")
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
    return await project_service.create_project(
        name, project_type, client_name, market_leader, project_leader,
        amount, creator, start_date, user, db
    )

@router.get("/project/{project_no}", response_class=HTMLResponse)
async def project_info(
    request: Request,
    project_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.get_project_info(request, project_no, user, db)

@router.post("/project/{project_no}/cancel")
async def cancel_project(
    project_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_no, 'cancelled', user, db)

@router.post("/project/{project_no}/resume")
async def resume_project(
    project_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_no, 'active', user, db)

@router.post("/project/{project_no}/complete")
async def complete_project(
    project_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_no, 'completed', user, db)

@router.post("/project/{project_no}/reopen")
async def reopen_project(
    project_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_no, 'active', user, db)

@router.post("/project/{project_no}/update_progress")
async def update_progress(
    project_no: str,
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    form_data = await request.form()
    progress = form_data.get("progress", "").strip()
    return await project_service.update_project_progress(project_no, progress, user, db)

@router.post("/project/{project_no}/add_contract")
async def add_contract_files(
    request: Request,
    project_no: str,
    contract_files: list[UploadFile] = File(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    print("add contract router")
    return await project_service.add_contract_files(project_no, request, user, db)

@router.post("/project/{project_no}/delete_contract_file/{file_id}")
async def delete_contract_file(
    project_no: str,
    file_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.delete_contract_file(project_no, file_id, user, db)

@router.get("/project/{project_no}/edit")
async def edit_project_page(
    project_no: str,
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.get_edit_project_page(request, project_no, user, db)

@router.post("/project/{project_no}/edit")
async def update_project(
    project_no: str,
    request: Request,
    name: str = Form(...),
    project_type: str = Form(...),
    client_name: str = Form(...),
    market_leader: str = Form(...),
    project_leader: str = Form(...),
    amount: float = Form(0.0),
    is_paid: str = Form(...),
    start_date: str = Form(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    print(project_leader, market_leader)
    return await project_service.update_project(
        project_no, name, project_type, client_name, market_leader,
        project_leader, amount, is_paid, start_date, user, db
    )

