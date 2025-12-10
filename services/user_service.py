from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

templates = Jinja2Templates(directory="templates")

class UserService:
    def __init__(self):
        pass

    async def get_user_profile(self, username: str, db):
        """获取用户个人信息"""
        try:
            c = db.cursor()
            # 修改查询，使用 datetime 函数转换时区
            c.execute("""
                SELECT username, user_type, realname, email, phone, department, 
                    position, education, hire_date, status,
                    datetime(create_time, 'localtime') as create_time,
                    datetime(update_time, 'localtime') as update_time
                FROM users 
                WHERE username = ?
            """, (username,))
            
            user_data = c.fetchone()
            
            if not user_data:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 转换为字典格式
            column_names = [col[0] for col in c.description]
            user_profile = dict(zip(column_names, user_data))
            
            return user_profile
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")

    async def update_user_profile(self, username: str, profile_data: Dict, db):
        """更新用户个人信息"""
        c = db.cursor()
        
        # 检查用户是否存在
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        allowed_fields = ["realname", "email", "phone", "department", "position"]
        for field in allowed_fields:
            if field in profile_data:
                update_fields.append(f"{field} = ?")
                update_values.append(profile_data[field])
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有可更新的字段")
        
        # 添加用户名作为WHERE条件
        update_values.append(username)
        
        # 执行更新
        update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
        c.execute(update_query, update_values)
        db.commit()
        
        return {"message": "个人信息更新成功"}

    async def change_password(self, username: str, password_data: Dict, db):
        """修改用户密码"""
        c = db.cursor()
        
        # 验证当前密码
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        current_password_hash = result[0]
        # 这里应该添加密码验证逻辑，比如使用密码哈希比较
        # 假设有一个函数 verify_password(plain_password, hashed_password)
        
        # 更新密码
        new_password = password_data.get("new_password")
        if not new_password:
            raise HTTPException(status_code=400, detail="新密码不能为空")
        
        # 这里应该对新密码进行哈希处理
        # new_password_hash = hash_password(new_password)
        new_password_hash = new_password  # 暂时直接存储，实际应用中应该使用哈希
        
        c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password_hash, username))
        db.commit()
        
        return {"message": "密码修改成功"}

    async def get_user_dashboard_data(self, request, user, db):
        """获取用户Dashboard数据"""
        c = db.cursor()
        username = user["username"]
        
        # 1. 项目统计数据
        # 负责的项目数（项目负责人）
        c.execute("""
            SELECT status, COUNT(*) FROM projects 
            WHERE project_leader = ? 
            GROUP BY status
        """, (username,))
        responsible_projects = dict(c.fetchall())
        
        # 参与的项目数（项目负责人、市场部负责人、创建人、复核人或签字人）
        c.execute("""
            SELECT p.status, COUNT(DISTINCT p.id) 
            FROM projects p
            LEFT JOIN reports r ON p.id = r.project_id
            WHERE p.project_leader = ? 
            OR p.market_leader = ? 
            OR p.creator = ?
            OR r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
            OR r.signer1 = ? OR r.signer2 = ?
            GROUP BY p.status
        """, (username, username, username, username, username, username, username, username))
        participated_projects = dict(c.fetchall())
        
        # 2. 报告统计数据
        # 创建的报告数
        c.execute("SELECT COUNT(*) FROM reports WHERE creator = ?", (username,))
        created_reports = c.fetchone()[0]
        
        # 复核的报告数
        c.execute("""
            SELECT COUNT(*) FROM reports 
            WHERE reviewer1 = ? OR reviewer2 = ? OR reviewer3 = ?
        """, (username, username, username))
        reviewed_reports = c.fetchone()[0]
        
        # 签字的报告数
        c.execute("""
            SELECT COUNT(*) FROM reports 
            WHERE signer1 = ? OR signer2 = ?
        """, (username, username))
        signed_reports = c.fetchone()[0]
        
        # 3. 获取用户参与的所有项目详细信息
        user_projects = await self.get_user_all_projects(username, db)
        
        return {
            "responsible_projects": responsible_projects,
            "participated_projects": participated_projects,
            "created_reports": created_reports,
            "reviewed_reports": reviewed_reports,
            "signed_reports": signed_reports,
            "user_projects": user_projects
        }

    async def get_user_all_projects(self, username: str, db):
        """获取用户参与的所有项目详细信息"""
        c = db.cursor()
        
        # 获取用户参与的所有项目（项目负责人、市场部负责人、创建人、复核人或签字人）
        c.execute("""
            SELECT DISTINCT p.*
            FROM projects p
            LEFT JOIN reports r ON p.id = r.project_id
            WHERE p.project_leader = ? 
               OR p.market_leader = ? 
               OR p.creator = ?
               OR r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
               OR r.signer1 = ? OR r.signer2 = ?
            ORDER BY p.create_date DESC
        """, (username, username, username, username, username, username, username, username))
        
        projects = []
        rows = c.fetchall()
        
        if not rows:
            return projects
            
        # 获取列名
        column_names = [col[0] for col in c.description]
        
        # 收集所有需要查询的用户名
        usernames_to_query = set()
        for row in rows:
            project_dict = dict(zip(column_names, row))
            if project_dict.get("project_leader"):
                usernames_to_query.add(project_dict["project_leader"])
            if project_dict.get("market_leader"):
                usernames_to_query.add(project_dict["market_leader"])
        
        # 批量查询用户真实姓名 - 使用新的游标
        user_realnames = {}
        if usernames_to_query:
            c2 = db.cursor()
            placeholders = ','.join('?' * len(usernames_to_query))
            c2.execute(f"SELECT username, realname FROM users WHERE username IN ({placeholders})", list(usernames_to_query))
            for row in c2.fetchall():
                user_realnames[row[0]] = row[1]
            c2.close()
        
        # 处理每个项目
        for row in rows:
            project_dict = dict(zip(column_names, row))
            
            # 设置项目负责人真实姓名
            if project_dict.get("project_leader"):
                project_dict["project_leader_realname"] = user_realnames.get(project_dict["project_leader"], project_dict["project_leader"])
            else:
                project_dict["project_leader_realname"] = ""
            
            # 设置市场部负责人真实姓名
            if project_dict.get("market_leader"):
                project_dict["market_leader_realname"] = user_realnames.get(project_dict["market_leader"], project_dict["market_leader"])
            else:
                project_dict["market_leader_realname"] = ""
            
            # 确保所有必要的字段都有默认值
            project_dict.setdefault("project_no", "")
            project_dict.setdefault("name", "")
            project_dict.setdefault("project_type", "")
            project_dict.setdefault("client_name", "")
            project_dict.setdefault("progress", "")
            project_dict.setdefault("report_numbers", "")
            project_dict.setdefault("amount", 0)
            project_dict.setdefault("is_paid", "")
            project_dict.setdefault("start_date", "")
            project_dict.setdefault("status", "active")
            
            projects.append(project_dict)
        
        return projects

    async def get_user_projects_data(self, request, user, project_type, db):
        """获取用户项目数据"""
        c = db.cursor()
        username = user["username"]
        
        if project_type == "responsible":
            # 我负责的项目（项目负责人）
            c.execute("""
                SELECT p.*, 
                    (SELECT COUNT(*) FROM reports r WHERE r.project_id = p.id) as report_count
                FROM projects p
                WHERE p.project_leader = ?
                ORDER BY p.create_date DESC
            """, (username,))
        elif project_type == "created":
            # 我创建的项目
            c.execute("""
                SELECT p.*, 
                    (SELECT COUNT(*) FROM reports r WHERE r.project_id = p.id) as report_count
                FROM projects p
                WHERE p.creator = ?
                ORDER BY p.create_date DESC
            """, (username,))
        else:  # participated
            # 我参与的项目（项目负责人、市场部负责人、创建人、复核人或签字人）
            c.execute("""
                SELECT DISTINCT p.*, 
                    (SELECT COUNT(*) FROM reports r WHERE r.project_id = p.id) as report_count
                FROM projects p
                LEFT JOIN reports r ON p.id = r.project_id
                WHERE p.project_leader = ? 
                   OR p.market_leader = ? 
                   OR p.creator = ?
                   OR r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
                   OR r.signer1 = ? OR r.signer2 = ?
                ORDER BY p.create_date DESC
            """, (username, username, username, username, username, username, username, username))
        
        projects = []
        rows = c.fetchall()
        
        if not rows:
            return projects
            
        column_names = [col[0] for col in c.description]
        
        # 收集所有需要查询的用户名
        usernames_to_query = set()
        for row in rows:
            project_dict = dict(zip(column_names, row))
            if project_dict.get("project_leader"):
                usernames_to_query.add(project_dict["project_leader"])
        
        # 批量查询用户真实姓名 - 使用新的游标
        user_realnames = {}
        if usernames_to_query:
            c2 = db.cursor()
            placeholders = ','.join('?' * len(usernames_to_query))
            c2.execute(f"SELECT username, realname FROM users WHERE username IN ({placeholders})", list(usernames_to_query))
            for row in c2.fetchall():
                user_realnames[row[0]] = row[1]
            c2.close()
        
        # 处理每个项目
        for row in rows:
            project_dict = dict(zip(column_names, row))
            
            # 设置项目负责人真实姓名
            if project_dict.get("project_leader"):
                project_dict["project_leader_realname"] = user_realnames.get(project_dict["project_leader"], project_dict["project_leader"])
            else:
                project_dict["project_leader_realname"] = ""
            
            # 确保所有必要的字段都有默认值
            project_dict.setdefault("project_no", "")
            project_dict.setdefault("name", "")
            project_dict.setdefault("project_type", "")
            project_dict.setdefault("client_name", "")
            project_dict.setdefault("progress", "")
            project_dict.setdefault("report_numbers", "")
            project_dict.setdefault("amount", 0)
            project_dict.setdefault("is_paid", "")
            project_dict.setdefault("start_date", "")
            project_dict.setdefault("status", "active")
            
            projects.append(project_dict)
        
        return projects

    async def get_user_reports_data(self, request, user, report_type, db):
        """获取用户报告数据"""
        c = db.cursor()
        username = user["username"]
        
        if report_type == "created":
            # 我创建的报告
            c.execute("""
                SELECT r.*, p.name as project_name, p.project_no
                FROM reports r
                JOIN projects p ON r.project_id = p.id
                WHERE r.creator = ?
                ORDER BY r.create_date DESC
            """, (username,))
        elif report_type == "reviewed":
            # 我复核的报告
            c.execute("""
                SELECT r.*, p.name as project_name, p.project_no
                FROM reports r
                JOIN projects p ON r.project_id = p.id
                WHERE r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
                ORDER BY r.create_date DESC
            """, (username, username, username))
        else:  # signed
            # 我签字的报告
            c.execute("""
                SELECT r.*, p.name as project_name, p.project_no
                FROM reports r
                JOIN projects p ON r.project_id = p.id
                WHERE r.signer1 = ? OR r.signer2 = ?
                ORDER BY r.create_date DESC
            """, (username, username))
        
        reports = []
        for row in c.fetchall():
            report_dict = dict(zip([col[0] for col in c.description], row))
            reports.append(report_dict)
        
        return reports

    async def get_user_qualifications(self, username: str, db):
        """获取用户资质信息"""
        c = db.cursor()
        
        # 首先检查 user_qualifications 表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_qualifications'")
        table_exists = c.fetchone()
        
        if not table_exists:
            print("user_qualifications 表不存在")
            return []
        
        # 查询用户资质信息
        c.execute("""
            SELECT qualification_type, qualification_number, 
                issue_date, expiry_date, issue_authority 
            FROM user_qualifications 
            WHERE username = ?
            ORDER BY issue_date DESC
        """, (username,))
        
        qualifications = []
        for row in c.fetchall():
            qual_dict = dict(zip([col[0] for col in c.description], row))
            qualifications.append(qual_dict)
        
        return qualifications
    
    async def get_user_basic_stats(self, user, db):
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

    async def get_all_users(self, db):
        """获取所有用户信息"""
        try:
            c = db.cursor()
            # 修改查询，使用 datetime 函数转换时区
            c.execute("""
                SELECT username, realname, user_type, hire_date, education, 
                    position, department, status, phone, email,
                    datetime(create_time, 'localtime') as create_time,
                    datetime(update_time, 'localtime') as update_time
                FROM users 
                ORDER BY create_time DESC
            """)
            
            users = []
            for row in c.fetchall():
                user_dict = dict(zip([col[0] for col in c.description], row))
                users.append(user_dict)
            
            return users
        except Exception as e:
            print(f"Error in get_all_users: {e}")
            raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")

    async def create_user(self, user_data: Dict, db):
        """创建新用户"""
        c = db.cursor()
        
        # 检查用户名是否已存在
        c.execute("SELECT username FROM users WHERE username = ?", (user_data.get("username"),))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 构建插入语句
        required_fields = ["username", "password", "user_type"]
        optional_fields = ["realname", "phone", "email", "hire_date", "education", "position", "department", "status"]
        
        # 验证必填字段
        for field in required_fields:
            if not user_data.get(field):
                raise HTTPException(status_code=400, detail=f"{field} 是必填字段")
        
        # 设置默认状态
        if "status" not in user_data or not user_data["status"]:
            user_data["status"] = "active"
        
        # 准备插入数据
        insert_fields = required_fields + optional_fields
        insert_values = []
        placeholders = []
        
        for field in insert_fields:
            if field in user_data:
                insert_values.append(user_data[field])
                placeholders.append("?")
            else:
                insert_values.append(None)
                placeholders.append("?")
        
        # 执行插入
        insert_query = f"INSERT INTO users ({', '.join(insert_fields)}) VALUES ({', '.join(placeholders)})"
        c.execute(insert_query, insert_values)
        db.commit()
        
        return {"message": "用户创建成功"}

    async def update_user(self, username: str, user_data: Dict, db):
        """更新用户信息"""
        c = db.cursor()
        
        # 检查用户是否存在
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        allowed_fields = ["realname", "user_type", "phone", "email", "hire_date", "education", "position", "department", "status"]
        for field in allowed_fields:
            if field in user_data:
                update_fields.append(f"{field} = ?")
                update_values.append(user_data[field])
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有可更新的字段")
        
        # 添加用户名作为WHERE条件
        update_values.append(username)
        
        # 执行更新
        update_query = f"UPDATE users SET {', '.join(update_fields)}, update_time = CURRENT_TIMESTAMP WHERE username = ?"
        c.execute(update_query, update_values)
        db.commit()
        
        return {"message": "用户信息更新成功"}

    async def delete_user(self, username: str, current_username: str, db):
        """删除用户"""
        c = db.cursor()
        
        # 检查用户是否存在
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 不能删除自己
        if username == current_username:
            raise HTTPException(status_code=400, detail="不能删除当前登录用户")
        
        # 检查用户是否有关联的项目
        c.execute("SELECT COUNT(*) FROM projects WHERE creator = ? OR project_leader = ? OR market_leader = ?", 
                (username, username, username))
        project_count = c.fetchone()[0]
        
        if project_count > 0:
            raise HTTPException(status_code=400, detail="该用户有关联的项目，无法删除")
        
        # 检查用户是否有关联的报告
        c.execute("""
            SELECT COUNT(*) FROM reports 
            WHERE creator = ? OR reviewer1 = ? OR reviewer2 = ? OR reviewer3 = ? OR signer1 = ? OR signer2 = ?
        """, (username, username, username, username, username, username))
        report_count = c.fetchone()[0]
        
        if report_count > 0:
            raise HTTPException(status_code=400, detail="该用户有关联的报告，无法删除")
        
        # 删除用户资质信息
        c.execute("DELETE FROM user_qualifications WHERE username = ?", (username,))
        
        # 删除用户
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        db.commit()
        
        return {"message": "用户删除成功"}

    async def reset_user_password(self, username: str, new_password: str, db):
        """重置用户密码"""
        c = db.cursor()
        
        # 检查用户是否存在
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新密码（实际应用中应该使用密码哈希）
        c.execute("UPDATE users SET password = ?, update_time = CURRENT_TIMESTAMP WHERE username = ?", 
                (new_password, username))
        db.commit()
        
        return {"message": "密码重置成功"}

    async def get_user_details(self, username: str, db):
        """获取用户详细信息"""
        try:
            c = db.cursor()
            # 修改查询，使用 datetime 函数转换时区
            c.execute("""
                SELECT username, realname, user_type, phone, email, hire_date, 
                    education, position, department, status,
                    datetime(create_time, 'localtime') as create_time,
                    datetime(update_time, 'localtime') as update_time
                FROM users 
                WHERE username = ?
            """, (username,))
            
            user_data = c.fetchone()
            if not user_data:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 转换为字典
            column_names = [col[0] for col in c.description]
            user_dict = dict(zip(column_names, user_data))
            
            return user_dict
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")
    
    async def add_user_qualification(self, username: str, qualification_data: Dict, db):
        """添加用户资质"""
        c = db.cursor()
        
        # 检查用户是否存在
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查资质类型是否有效
        valid_qualifications = ["土地估价师", "资产评估师", "房地产估价师"]
        if qualification_data.get("qualification_type") not in valid_qualifications:
            raise HTTPException(status_code=400, detail="无效的资质类型")
        
        # 检查是否已存在相同类型的资质
        c.execute("""
            SELECT id FROM user_qualifications 
            WHERE username = ? AND qualification_type = ?
        """, (username, qualification_data.get("qualification_type")))
        
        if c.fetchone():
            raise HTTPException(status_code=400, detail="该用户已拥有此类型资质")
        
        # 插入资质信息
        c.execute("""
            INSERT INTO user_qualifications 
            (username, qualification_type, qualification_number, issue_authority, issue_date, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            qualification_data.get("qualification_type"),
            qualification_data.get("qualification_number"),
            qualification_data.get("issue_authority"),
            qualification_data.get("issue_date"),
            qualification_data.get("expiry_date")
        ))
        db.commit()
        
        return {"message": "资质添加成功"}

    async def delete_user_qualification(self, username: str, qualification_type: str, qualification_number: str, db):
        """删除用户资质"""
        c = db.cursor()
        
        # 检查资质是否存在
        if qualification_number:
            c.execute("""
                SELECT id FROM user_qualifications 
                WHERE username = ? AND qualification_type = ? AND qualification_number = ?
            """, (username, qualification_type, qualification_number))
        else:
            c.execute("""
                SELECT id FROM user_qualifications 
                WHERE username = ? AND qualification_type = ?
            """, (username, qualification_type))
        
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="资质不存在")
        
        # 删除资质信息
        if qualification_number:
            c.execute("""
                DELETE FROM user_qualifications 
                WHERE username = ? AND qualification_type = ? AND qualification_number = ?
            """, (username, qualification_type, qualification_number))
        else:
            c.execute("""
                DELETE FROM user_qualifications 
                WHERE username = ? AND qualification_type = ?
            """, (username, qualification_type))
        
        db.commit()
        
        return {"message": "资质删除成功"}

    async def get_all_users_for_qualifications(self, db=None):
        """获取所有用户用于资质选择（只返回在职用户）"""
        try:
            c = db.cursor()
            c.execute("""
                SELECT username, realname 
                FROM users 
                WHERE status = 'active' AND realname IS NOT NULL AND realname != ''
                ORDER BY realname
            """)
            users = []
            for row in c.fetchall():
                user_dict = {
                    'username': row[0],
                    'realname': row[1]
                }
                users.append(user_dict)
            return users
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    async def get_company_qualifications(self, category: str = None, db=None):
        """获取公司资质列表"""
        try:
            c = db.cursor()
            
            if category and category != 'all':
                c.execute("""
                    SELECT id, category, owner, file_path, file_name,
                        datetime(update_time, 'localtime') as update_time,
                        uploader_username, status
                    FROM company_qualifications 
                    WHERE category = ? AND status = 'active'
                    ORDER BY update_time DESC
                """, (category,))
            else:
                c.execute("""
                    SELECT id, category, owner, file_path, file_name,
                        datetime(update_time, 'localtime') as update_time,
                        uploader_username, status
                    FROM company_qualifications 
                    WHERE status = 'active'
                    ORDER BY update_time DESC
                """)
            
            qualifications = []
            for row in c.fetchall():
                qual_dict = dict(zip([col[0] for col in c.description], row))
                qualifications.append(qual_dict)
            
            return qualifications
        except Exception as e:
            print(f"获取公司资质失败: {e}")
            return []

    async def add_company_qualification(self, qualification_data: Dict, db=None):
        """添加公司资质"""
        try:
            c = db.cursor()
            
            # 检查是否已存在相同名称的证书
            c.execute("""
                SELECT id FROM company_qualifications 
                WHERE file_name = ? AND status = 'active'
            """, (qualification_data.get("file_name"),))
            
            if c.fetchone():
                raise HTTPException(status_code=400, detail="已存在相同名称的证书")
            
            # 处理拥有人字段，如果为空则设置为"公司"
            owner = qualification_data.get("owner", "").strip()
            if not owner:
                owner = "公司"
            
            # 插入新资质
            c.execute("""
                INSERT INTO company_qualifications 
                (category, owner, file_path, file_name, uploader_username)
                VALUES (?, ?, ?, ?, ?)
            """, (
                qualification_data.get("category"),
                owner,  # 使用处理后的拥有人
                qualification_data.get("file_path"),
                qualification_data.get("file_name"),
                qualification_data.get("uploader_username")
            ))
            
            db.commit()
            return {"message": "公司资质添加成功"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"添加公司资质失败: {str(e)}")

    async def delete_company_qualification(self, qualification_id: int, db=None):
        """删除公司资质（硬删除）"""
        try:
            c = db.cursor()
            
            # 检查资质是否存在
            c.execute("SELECT id, file_path FROM company_qualifications WHERE id = ?", (qualification_id,))
            result = c.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="资质不存在")
            
            # 获取文件路径用于删除物理文件
            file_path = result[1]
            
            # 硬删除数据库记录
            c.execute("DELETE FROM company_qualifications WHERE id = ?", (qualification_id,))
            db.commit()
            
            return {"message": "公司资质删除成功"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除公司资质失败: {str(e)}")

    async def get_qualification_categories(self, db=None):
        """获取资质类别列表"""
        try:
            c = db.cursor()
            c.execute("SELECT DISTINCT category FROM company_qualifications WHERE status = 'active' ORDER BY category")
            categories = [row[0] for row in c.fetchall()]
            return categories
        except Exception as e:
            print(f"获取资质类别失败: {e}")
            return []

user_service = UserService()