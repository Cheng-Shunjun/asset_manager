from fastapi import APIRouter, Request, Form, File, UploadFile, Depends, HTTPException
from fastapi.responses import RedirectResponse
from database.database import db_manager, get_db
from auth.auth import login_required
from services.report_service import ReportService
import sqlite3

router = APIRouter()
report_service = ReportService()

@router.post("/project/{project_id}/update_report/{report_no}")
async def update_report(
    project_id: int,
    report_no: str,
    reviewer1: str = Form(None),
    reviewer2: str = Form(None),
    reviewer3: str = Form(None),
    signer1: str = Form(None),
    signer2: str = Form(None),
    report_files: list[UploadFile] = File([]),
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await report_service.update_report(
        project_id, report_no, reviewer1, reviewer2, reviewer3,
        signer1, signer2, report_files, user, db
    )

@router.post("/project/{project_id}/generate_report_no")
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
    return await report_service.generate_report_no(
        project_id, report_type, is_filing, reviewer1, reviewer2,
        reviewer3, signer1, signer2, user, db
    )

@router.post("/project/{project_id}/delete_report/{report_no}")
async def delete_report(
    project_id: int,
    report_no: str,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await report_service.delete_report(project_id, report_no, user, db)

@router.post("/project/{project_id}/delete_report_file/{report_id}/{file_id}")
async def delete_report_file(
    project_id: int,
    report_id: int,
    file_id: int,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    return await report_service.delete_report_file(project_id, report_id, file_id, user, db)