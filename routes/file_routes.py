from fastapi import APIRouter, Request, File, UploadFile, Depends
from fastapi.responses import RedirectResponse
from database.database import get_db
from auth.auth import login_required
from services.file_service import FileService
import sqlite3

router = APIRouter()
file_service = FileService()

@router.post("/project/{project_id}/add_contract")
async def add_contract_files(
    request: Request,
    project_id: int,
    contract_files: list[UploadFile] = File(...),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await file_service.add_contract_files(project_id, contract_files, user, db)

# 可选：添加其他文件相关路由
@router.post("/cleanup-files")
async def cleanup_files(
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    """清理孤立文件（需要管理员权限）"""
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    deleted_count = await file_service.cleanup_orphaned_files(db)
    return {"message": f"清理完成，删除了 {deleted_count} 个孤立文件"}