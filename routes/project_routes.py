from fastapi import APIRouter, Request, Form, Depends, HTTPException, File, UploadFile
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

@router.get("/admin", response_class=HTMLResponse)
async def admin(
    request: Request,
    user: dict = Depends(admin_required),  # 使用管理员权限检查
    db: sqlite3.Connection = Depends(get_db)
):
    """管理员后台页面 - 仅管理员可访问"""
    return await project_service.get_admin_page(request, user, db)

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

@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_info(
    request: Request,
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.get_project_info(request, project_id, user, db)

@router.post("/project/{project_id}/pause")
async def pause_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_id, 'paused', user, db)

@router.post("/project/{project_id}/resume")
async def resume_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_id, 'active', user, db)

@router.post("/project/{project_id}/complete")
async def complete_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_id, 'completed', user, db)

@router.post("/project/{project_id}/reopen")
async def reopen_project(
    project_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.update_project_status(project_id, 'active', user, db)

@router.post("/project/{project_id}/update_progress")
async def update_progress(
    project_id: int,
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    form_data = await request.form()
    progress = form_data.get("progress", "").strip()
    return await project_service.update_project_progress(project_id, progress, user, db)

@router.post("/project/{project_id}/add_contract")
async def add_contract_files(
    request: Request,
    project_id: int,
    contract_files: list[UploadFile] = File(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    print("add contract router")
    return await project_service.add_contract_files(project_id, request, user, db)

@router.post("/project/{project_id}/delete_contract_file/{file_id}")
async def delete_contract_file(
    project_id: int,
    file_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.delete_contract_file(project_id, file_id, user, db)

@router.get("/project/{project_id}/edit")
async def edit_project_page(
    project_id: int,
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await project_service.get_edit_project_page(request, project_id, user, db)

@router.post("/project/{project_id}/edit")
async def update_project(
    project_id: int,
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
        project_id, name, project_type, client_name, market_leader,
        project_leader, amount, is_paid, start_date, user, db
    )

