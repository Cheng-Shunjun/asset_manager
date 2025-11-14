from fastapi import HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import sqlite3
import os
import shutil
from typing import List
from utils.helpers import secure_filename

templates = Jinja2Templates(directory="templates")

class ProjectService:
    def _get_project_permission(self, user, project_creator, project_leader):
        user_type = user.get("user_type", "user")
        username = user.get("username")
        return (
            user_type == "admin" or 
            username == project_creator or
            username == project_leader
        )
    
    def _check_project_permission(self, project_id, user, db):
        """检查用户是否有操作项目的权限：管理员、项目创建人或项目负责人"""
        c = db.cursor()
        
        # 获取项目信息
        c.execute("SELECT creator, project_leader FROM projects WHERE id = ?", (project_id,))
        project = c.fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        project_creator = project[0]
        project_leader = project[1]
        
        # 权限检查：管理员或项目负责人
        has_permission = self._get_project_permission(user, project_creator, project_leader)
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="权限不足，只有管理员、项目创建人或项目负责人可执行此操作")
        
        return True

    async def get_admin_page(self, request, user, db):
        c = db.cursor()
        c.execute("SELECT * FROM projects ORDER BY start_date DESC")
        projects = c.fetchall()
        print(len(projects))

        projects_list = []
        years = set()

        for p in projects:
            print(p['name'])
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
                "creator_realname": p["creator_realname"],
                "start_date": p["start_date"],
                "end_date": p["end_date"],
                "status": p["status"],
                "create_date": p["create_date"]
            }
            
            # 将负责人用户名转换为真实姓名
            if project_dict["market_leader"]:
                c.execute("SELECT realname FROM users WHERE username = ?", (project_dict["market_leader"],))
                market_leader_result = c.fetchone()
                project_dict["market_leader_realname"] = market_leader_result[0] if market_leader_result else project_dict["market_leader"]
            else:
                project_dict["market_leader_realname"] = ""
            
            if project_dict["project_leader"]:
                c.execute("SELECT realname FROM users WHERE username = ?", (project_dict["project_leader"],))
                project_leader_result = c.fetchone()
                project_dict["project_leader_realname"] = project_leader_result[0] if project_leader_result else project_dict["project_leader"]
            else:
                project_dict["project_leader_realname"] = ""
            
            projects_list.append(project_dict)
            if p["start_date"]:
                years.add(int(p["start_date"][:4]))

        years_sorted = sorted(years, reverse=True)

        return templates.TemplateResponse("admin_projects.html", {
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
            "user": user,  # 传递完整的用户对象
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
        
        # 将负责人用户名转换为真实姓名
        if project_dict["market_leader"]:
            c.execute("SELECT realname FROM users WHERE username = ?", (project_dict["market_leader"],))
            market_leader_result = c.fetchone()
            project_dict["market_leader_realname"] = market_leader_result[0] if market_leader_result else project_dict["market_leader"]
        else:
            project_dict["market_leader_realname"] = ""
        
        if project_dict["project_leader"]:
            c.execute("SELECT realname FROM users WHERE username = ?", (project_dict["project_leader"],))
            project_leader_result = c.fetchone()
            project_dict["project_leader_realname"] = project_leader_result[0] if project_leader_result else project_dict["project_leader"]
        else:
            project_dict["project_leader_realname"] = ""
        
        # 获取合同文件信息
        c.execute("""
            SELECT id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size
            FROM contract_files 
            WHERE project_id = ? 
            ORDER BY upload_time DESC
        """, (project_id,))
        
        contract_files = []
        for row in c.fetchall():
            contract_files.append({
                "id": row[0],
                "file_path": row[1],
                "file_name": row[2],
                "uploader_username": row[3],
                "uploader_realname": row[4],
                "upload_time": row[5],
                "file_size": row[6]
            })
        
        # 获取报告信息
        c.execute("""
            SELECT id, report_no, report_type, file_paths, creator, creator_realname, create_date, 
                reviewer1, reviewer2, reviewer3, signer1, signer2
            FROM reports WHERE project_id = ? ORDER BY create_date DESC
        """, (project_id,))

        reports = []
        for row in c.fetchall():
            report_data = {
                "id": row[0],
                "report_no": row[1],
                "report_type": row[2],
                "file_paths": row[3],
                "creator": row[4],
                "creator_realname": row[5],
                "create_date": row[6],
                "reviewer1": row[7],
                "reviewer2": row[8],
                "reviewer3": row[9],
                "signer1": row[10],
                "signer2": row[11],
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
        
        # 获取用户列表时包含资质信息
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = []
        for row in users_data:
            # 获取每个用户的资质
            c.execute("SELECT qualification_type FROM user_qualifications WHERE username = ?", (row[0],))
            qualifications = [qual_row[0] for qual_row in c.fetchall()]
            
            users.append({
                "username": row[0], 
                "realname": row[1] or row[0],
                "qualifications": qualifications
            })
        
        # 检查当前用户是否有操作权限：管理员或项目负责人
        project_creator = project_dict["creator"]
        project_leader = project_dict["project_leader"]
        project_operation_permission = self._get_project_permission(user, project_creator, project_leader)
        
        return templates.TemplateResponse("project_info.html", {
            "request": request,
            "project": project_dict,
            "contract_files": contract_files,  # 新增合同文件数据
            "reports": reports,
            "users": users,
            "user": user,
            "project_operation_permission": project_operation_permission
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

    async def get_edit_project_page(self, request, project_id, user, db):
        """获取项目编辑页面"""
        # 检查权限
        self._check_project_permission(project_id, user, db)
        
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
        
        # 获取用户列表用于选择框
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
        
        return templates.TemplateResponse("edit_project.html", {
            "request": request,
            "project": project_dict,
            "users": users,
            "user": user
        })

    async def update_project(self, project_id, name, project_type, client_name, market_leader,
                            project_leader, amount, is_paid, start_date, user, db):
        """更新项目信息"""
        try:
            # 检查权限
            self._check_project_permission(project_id, user, db)
            
            c = db.cursor()
            
            # 验证项目是否存在
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            # 更新项目信息
            c.execute("""
                UPDATE projects 
                SET name = ?, project_type = ?, client_name = ?, 
                    market_leader = ?, project_leader = ?, amount = ?, 
                    is_paid = ?, start_date = ?
                WHERE id = ?
            """, (
                name, project_type, client_name, market_leader,
                project_leader, amount, is_paid, start_date, project_id
            ))
            
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")

    async def add_contract_files(self, project_id, request, user, db):
        """添加合同文件"""
        try:
            # 检查权限
            self._check_project_permission(project_id, user, db)
            
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status in ['completed', 'cancelled']:
                raise HTTPException(status_code=400, detail=f"项目状态为{status}，无法添加合同文件")
            
            form_data = await request.form()
            contract_files = form_data.getlist("contract_files")
            
            if not contract_files:
                raise HTTPException(status_code=400, detail="请选择要上传的文件")
            
            # 获取当前用户的真实姓名
            c.execute("SELECT realname FROM users WHERE username = ?", (user["username"],))
            uploader_realname_result = c.fetchone()
            uploader_realname = uploader_realname_result[0] if uploader_realname_result else user["username"]
            
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for contract_file in contract_files:
                if contract_file.filename:
                    contract_filename = secure_filename(contract_file.filename)
                    contract_path = os.path.join('static/uploads', contract_filename)
                    
                    with open(contract_path, "wb") as f:
                        content = await contract_file.read()
                        f.write(content)
                    
                    file_size = os.path.getsize(contract_path)
                    
                    # 插入到 contract_files 表
                    c.execute("""
                        INSERT INTO contract_files 
                        (project_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        project_id, contract_path, contract_file.filename, user["username"],
                        uploader_realname, upload_time, file_size
                    ))
            
            db.commit()
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"添加合同文件失败: {str(e)}")

    async def delete_contract_file(self, project_id, file_id, user, db):
        """删除合同文件"""
        try:
            # 检查权限
            self._check_project_permission(project_id, user, db)
            
            c = db.cursor()
            
            # 检查项目状态
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以删除合同文件")
            
            # 获取文件信息
            c.execute("SELECT file_path FROM contract_files WHERE id = ? AND project_id = ?", (file_id, project_id))
            file_result = c.fetchone()
            
            if not file_result:
                raise HTTPException(status_code=404, detail="文件不存在")
            
            file_path = file_result[0]
            
            # 删除物理文件
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ 已删除合同文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除合同文件失败 {file_path}: {e}")
            
            # 从数据库删除文件记录
            c.execute("DELETE FROM contract_files WHERE id = ? AND project_id = ?", (file_id, project_id))
            
            db.commit()
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除合同文件失败: {str(e)}")