from fastapi import HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import sqlite3
import os
import shutil
from typing import List

templates = Jinja2Templates(directory="templates")

class ProjectService:
    
    def _check_project_permission(self, project_id, user, db):
        """检查用户是否有操作项目的权限：管理员、项目创建人或项目负责人"""
        c = db.cursor()
        
        # 获取项目信息
        c.execute("SELECT creator, project_leader FROM projects WHERE id = ?", (project_id,))
        project = c.fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        creator = project[0]
        project_leader = project[1]
        user_type = user.get("user_type", "user")
        username = user.get("username")
        
        # 权限检查：管理员、项目创建人或项目负责人
        has_permission = (
            user_type == "admin" or 
            username == creator or
            username == project_leader
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="权限不足，只有管理员、项目创建人或项目负责人可执行此操作")
        
        return True

    async def get_admin_page(self, request, user, db):
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
                "creator_realname": p["creator_realname"],  # 新增字段
                "start_date": p["start_date"],
                "end_date": p["end_date"],
                "status": p["status"],
                "create_date": p["create_date"]
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

    async def get_create_project_page(self, request, user, db):
        c = db.cursor()
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
        
        return templates.TemplateResponse("create_project.html", {
            "request": request,
            "username": user["username"],
            "users": users
        })

    def generate_project_no(self, db):
        """生成项目编号：P2025_031 格式"""
        current_year = datetime.now().year
        
        c = db.cursor()
        c.execute("""
            SELECT COUNT(*) FROM projects 
            WHERE project_no LIKE ?
        """, (f"P{current_year}_%",))
        
        current_count = c.fetchone()[0]
        next_number = current_count + 1
        
        return f"P{current_year}_{next_number:03d}"

    async def create_project(self, name, project_type, client_name, market_leader, 
                       project_leader, amount, creator, start_date, user, db):
        try:
            project_no = self.generate_project_no(db)
            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            progress = "洽谈中"
            report_numbers = ""
            is_paid = "否"
            end_date = start_date
            status = "active"
            
            # 获取当前用户的真实姓名
            c = db.cursor()
            c.execute("SELECT realname FROM users WHERE username = ?", (creator,))
            creator_realname_result = c.fetchone()
            creator_realname = creator_realname_result[0] if creator_realname_result else creator
            
            c.execute("""
                INSERT INTO projects (
                    project_no, name, project_type, client_name, market_leader, 
                    project_leader, progress, report_numbers, amount, is_paid, 
                    creator, creator_realname, start_date, end_date, status, contract_file, create_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_no, name, project_type, client_name, market_leader,
                project_leader, progress, report_numbers, amount, is_paid, 
                creator, creator_realname, start_date, end_date, status, "", create_date
            ))
            db.commit()

            return RedirectResponse(url="/admin", status_code=303)

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")

    async def get_project_info(self, request, project_id, user, db):
        c = db.cursor()
        c.execute("""
            SELECT 
                id, project_no, name, project_type, client_name, 
                market_leader, project_leader, progress, report_numbers, 
                amount, is_paid, creator, creator_realname, start_date, end_date, 
                status, contract_file, create_date
            FROM projects WHERE id=?
        """, (project_id,))
        
        project = c.fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        columns = [description[0] for description in c.description]
        project_dict = dict(zip(columns, project))
        
        # 获取报告信息
        c.execute("""
            SELECT id, report_no, file_paths, creator, creator_realname, create_date, 
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
                "creator_realname": row[4],
                "create_date": row[5],
                "reviewer1": row[6],
                "reviewer2": row[7],
                "reviewer3": row[8],
                "signer1": row[9],
                "signer2": row[10],
                "files": []
            }
            
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
        
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
        
        # 检查当前用户是否有操作权限：管理员、项目创建人或项目负责人
        has_operation_permission = (
            user.get("user_type") == "admin" or 
            user.get("username") == project_dict["creator"] or
            user.get("username") == project_dict["project_leader"]
        )
        
        return templates.TemplateResponse("project_info.html", {
            "request": request,
            "project": project_dict,
            "reports": reports,
            "users": users,
            "user": user,
            "has_operation_permission": has_operation_permission
        })

    async def update_project_status(self, project_id, status, user, db):
        """更新项目状态（带权限检查）"""
        # 检查权限
        self._check_project_permission(project_id, user, db)
        
        c = db.cursor()
        c.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
        db.commit()
        return RedirectResponse(url=f"/project/{project_id}", status_code=303)

    async def update_project_progress(self, project_id, progress, user, db):
        """更新项目进度（带权限检查）"""
        try:
            # 检查权限
            self._check_project_permission(project_id, user, db)
            
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以更新进度")
            
            if len(progress) > 50:
                raise HTTPException(status_code=400, detail="进度描述不能超过50字")
            
            c.execute("UPDATE projects SET progress = ? WHERE id = ?", (progress, project_id))
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"更新进度失败: {str(e)}")