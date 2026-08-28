from fastapi import HTTPException, Request, UploadFile, File, Form
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
    
    def _check_project_permission_by_no(self, project_no, user, db):
        """检查用户是否有操作项目的权限：管理员、项目创建人或项目负责人"""
        c = db.cursor()
        
        # 获取项目信息
        c.execute("SELECT creator, project_leader FROM projects WHERE project_no = ?", (project_no,))
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

    # 在 project_service.py 中修改 get_admin_page 方法
    async def get_admin_page(self, request: Request, user: dict, db):
        """获取管理员页面（初始加载）"""
        try:
            # 获取所有项目（初始加载使用）
            c = db.cursor()
            c.execute("SELECT * FROM projects ORDER BY create_date DESC")
            rows = c.fetchall()
            
            projects = []
            if rows:
                column_names = [col[0] for col in c.description]
                
                # 收集所有需要查询的用户名
                usernames_to_query = set()
                for row in rows:
                    project_dict = dict(zip(column_names, row))
                    
                    if project_dict.get("project_leader"):
                        usernames_to_query.add(project_dict["project_leader"])
                    if project_dict.get("market_leader"):
                        usernames_to_query.add(project_dict["market_leader"])
                    
                    projects.append(project_dict)
                
                # 批量查询用户真实姓名
                user_realnames = {}
                if usernames_to_query:
                    c2 = db.cursor()
                    placeholders = ','.join('?' * len(usernames_to_query))
                    c2.execute(f"SELECT username, realname FROM users WHERE username IN ({placeholders})", list(usernames_to_query))
                    for row in c2.fetchall():
                        user_realnames[row[0]] = row[1]
                    c2.close()
                
                # 处理每个项目，添加真实姓名
                for project in projects:
                    if project.get("project_leader"):
                        project["project_leader_realname"] = user_realnames.get(project["project_leader"], project["project_leader"])
                    else:
                        project["project_leader_realname"] = ""
                    
                    if project.get("market_leader"):
                        project["market_leader_realname"] = user_realnames.get(project["market_leader"], project["market_leader"])
                    else:
                        project["market_leader_realname"] = ""
            
            # 获取所有项目的年份列表
            c.execute("""
                SELECT DISTINCT strftime('%Y', start_date) as year 
                FROM projects 
                WHERE start_date IS NOT NULL AND start_date != ''
                ORDER BY year DESC
            """)
            years = [row[0] for row in c.fetchall()]
            
            # 计算分页相关信息
            total_count = len(projects)
            current_page = 1
            page_size = 20
            total_pages = max(1, (total_count + page_size - 1) // page_size)
            
            # 计算显示范围
            start_item = ((current_page - 1) * page_size) + 1
            end_item = min(current_page * page_size, total_count)
            
            return templates.TemplateResponse(request, "admin_projects.html", {
                "user": user,
                "projects": projects,
                "years": years,
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": current_page,
                "page_size": page_size,
                "current_search": None,
                "current_status": "all",
                "current_year": None,
                "start_item": start_item,
                "end_item": end_item
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取管理页面失败: {str(e)}")

    async def get_create_project_page(self, request, user, db):
        c = db.cursor()
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
        
        return templates.TemplateResponse(request, "create_project.html", {
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

            return RedirectResponse(url="/user_dashboard", status_code=303)

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")

    async def get_project_info(self, request, project_no, user, db):
        c = db.cursor()
        c.execute("""
            SELECT 
                id, project_no, name, project_type, client_name, 
                market_leader, project_leader, progress, report_numbers, 
                amount, is_paid, creator, creator_realname, start_date, end_date, 
                status, contract_file, create_date
            FROM projects WHERE project_no=?
        """, (project_no,))
        
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
        """, (project_dict["id"],))
        
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
        """, (project_dict["id"],))

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
        
        return templates.TemplateResponse(request, "project_info.html", {
            "project": project_dict,
            "contract_files": contract_files,  # 新增合同文件数据
            "reports": reports,
            "users": users,
            "user": user,
            "project_operation_permission": project_operation_permission
        })

    async def update_project_status(self, project_no, status, user, db):
        """更新项目状态（带权限检查）"""
        # 检查权限
        self._check_project_permission_by_no(project_no, user, db)
        
        c = db.cursor()
        c.execute("UPDATE projects SET status = ? WHERE project_no = ?", (status, project_no))
        db.commit()
        return RedirectResponse(url=f"/project/{project_no}", status_code=303)

    async def update_project_progress(self, project_no, progress, user, db):
        """更新项目进度（带权限检查）"""
        try:
            # 检查权限
            self._check_project_permission_by_no(project_no, user, db)
            
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE project_no = ?", (project_no,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以更新进度")
            
            if len(progress) > 50:
                raise HTTPException(status_code=400, detail="进度描述不能超过50字")
            
            c.execute("UPDATE projects SET progress = ? WHERE project_no = ?", (progress, project_no))
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_no}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"更新进度失败: {str(e)}")

    async def get_edit_project_page(self, request, project_no, user, db):
        """获取项目编辑页面"""
        # 检查权限
        self._check_project_permission_by_no(project_no, user, db)
        
        c = db.cursor()
        c.execute("""
            SELECT 
                id, project_no, name, project_type, client_name, 
                market_leader, project_leader, progress, report_numbers, 
                amount, is_paid, creator, creator_realname, start_date, end_date, 
                status, contract_file, create_date
            FROM projects WHERE project_no=?
        """, (project_no,))
        
        project = c.fetchone()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        columns = [description[0] for description in c.description]
        project_dict = dict(zip(columns, project))
        
        # 获取用户列表用于选择框
        c.execute("SELECT username, realname FROM users")
        users_data = c.fetchall()
        users = [{"username": row[0], "realname": row[1] or row[0]} for row in users_data]
        
        return templates.TemplateResponse(request, "edit_project.html", {
            "project": project_dict,
            "users": users,
            "user": user
        })

    async def update_project(self, project_no, name, project_type, client_name, market_leader,
                            project_leader, amount, is_paid, start_date, user, db):
        """更新项目信息"""
        try:
            # 检查权限
            self._check_project_permission_by_no(project_no, user, db)
            
            c = db.cursor()
            
            # 验证项目是否存在
            c.execute("SELECT status FROM projects WHERE project_no = ?", (project_no,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            # 更新项目信息
            c.execute("""
                UPDATE projects 
                SET name = ?, project_type = ?, client_name = ?, 
                    market_leader = ?, project_leader = ?, amount = ?, 
                    is_paid = ?, start_date = ?
                WHERE project_no = ?
            """, (
                name, project_type, client_name, market_leader,
                project_leader, amount, is_paid, start_date, project_no
            ))
            
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_no}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")

    async def add_contract_files(self, project_no, request, user, db):
        """添加合同文件"""
        try:
            # 检查权限
            self._check_project_permission_by_no(project_no, user, db)
            
            c = db.cursor()
            c.execute("SELECT id, status FROM projects WHERE project_no = ?", (project_no,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            project_id = result[0]
            status = result[1]
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
                    
                    # 创建项目专用的上传目录
                    contract_dir = os.path.join('static/uploads/contract_file', project_no)
                    os.makedirs(contract_dir, exist_ok=True)  # 创建目录，如果不存在的话
                    
                    contract_path = os.path.join(contract_dir, contract_filename)
                    
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
            return RedirectResponse(url=f"/project/{project_no}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"添加合同文件失败: {str(e)}")

    async def delete_contract_file(self, project_no, file_id, user, db):
        """删除合同文件"""
        try:
            # 检查权限
            self._check_project_permission_by_no(project_no, user, db)
            
            c = db.cursor()
            
            # 获取项目ID
            c.execute("SELECT id, status FROM projects WHERE project_no = ?", (project_no,))
            project_result = c.fetchone()
            
            if not project_result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            project_id = project_result[0]
            status = project_result[1]
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
            return RedirectResponse(url=f"/project/{project_no}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除合同文件失败: {str(e)}")
        
    async def get_admin_projects_paginated(self, page: int = 1, limit: int = 20, 
                                     search: str = None, status: str = None, 
                                     year: str = None, db=None):
        """分页获取所有项目（管理员使用）"""
        try:
            c = db.cursor()
            
            # 计算偏移量
            offset = (page - 1) * limit
            
            # 构建基础查询
            base_query = """
                SELECT p.* 
                FROM projects p
                WHERE 1=1
            """
            
            # 构建计数查询
            count_query = """
                SELECT COUNT(*) 
                FROM projects p
                WHERE 1=1
            """
            
            # 查询参数
            params = []
            count_params = []
            
            # 添加搜索条件
            if search and search.strip():
                search_term = f"%{search.strip()}%"
                base_query += " AND (p.project_no LIKE ? OR p.name LIKE ? OR p.client_name LIKE ?)"
                count_query += " AND (p.project_no LIKE ? OR p.name LIKE ? OR p.client_name LIKE ?)"
                params.extend([search_term, search_term, search_term])
                count_params.extend([search_term, search_term, search_term])
            
            # 添加状态筛选条件
            if status and status != 'all':
                base_query += " AND p.status = ?"
                count_query += " AND p.status = ?"
                params.append(status)
                count_params.append(status)
            
            # 添加年份筛选条件
            if year and year.strip():
                base_query += " AND strftime('%Y', p.start_date) = ?"
                count_query += " AND strftime('%Y', p.start_date) = ?"
                params.append(year)
                count_params.append(year)
            
            # 添加排序和分页
            base_query += " ORDER BY p.create_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            # 执行计数查询
            c.execute(count_query, count_params)
            total_count = c.fetchone()[0]
            
            # 执行数据查询
            c.execute(base_query, params)
            rows = c.fetchall()
            
            # 获取列名
            column_names = [col[0] for col in c.description] if rows else []
            
            # 收集所有需要查询的用户名
            usernames_to_query = set()
            projects = []
            
            for row in rows:
                project_dict = dict(zip(column_names, row))
                
                if project_dict.get("project_leader"):
                    usernames_to_query.add(project_dict["project_leader"])
                if project_dict.get("market_leader"):
                    usernames_to_query.add(project_dict["market_leader"])
                
                projects.append(project_dict)
            
            # 批量查询用户真实姓名
            user_realnames = {}
            if usernames_to_query:
                c2 = db.cursor()
                placeholders = ','.join('?' * len(usernames_to_query))
                c2.execute(f"SELECT username, realname FROM users WHERE username IN ({placeholders})", 
                        list(usernames_to_query))
                for row in c2.fetchall():
                    user_realnames[row[0]] = row[1]
                c2.close()
            
            # 处理每个项目，添加真实姓名
            for project in projects:
                if project.get("project_leader"):
                    project["project_leader_realname"] = user_realnames.get(
                        project["project_leader"], project["project_leader"]
                    )
                else:
                    project["project_leader_realname"] = ""
                
                if project.get("market_leader"):
                    project["market_leader_realname"] = user_realnames.get(
                        project["market_leader"], project["market_leader"]
                    )
                else:
                    project["market_leader_realname"] = ""
                
                # 确保所有必要的字段都有默认值
                project.setdefault("project_no", "")
                project.setdefault("name", "")
                project.setdefault("project_type", "")
                project.setdefault("client_name", "")
                project.setdefault("progress", "")
                project.setdefault("report_numbers", "")
                project.setdefault("amount", 0)
                project.setdefault("is_paid", "")
                project.setdefault("start_date", "")
                project.setdefault("status", "active")
            
            # 计算总页数
            total_pages = max(1, (total_count + limit - 1) // limit)  # 向上取整
            
            return {
                "projects": projects,
                "total_count": total_count,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": limit
            }
            
        except Exception as e:
            print(f"分页获取管理员项目失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")