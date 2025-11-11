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

user_service = UserService()