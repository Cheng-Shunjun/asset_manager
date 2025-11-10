from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List

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
        
        # 3. 近一年每月参与报告数
        one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        c.execute("""
            SELECT strftime('%Y-%m', create_date) as month, COUNT(*)
            FROM reports 
            WHERE (creator = ? OR reviewer1 = ? OR reviewer2 = ? OR reviewer3 = ? OR signer1 = ? OR signer2 = ?)
            AND create_date >= ?
            GROUP BY strftime('%Y-%m', create_date)
            ORDER BY month
        """, (username, username, username, username, username, username, one_year_ago))
        monthly_reports = dict(c.fetchall())
        
        # 4. 近一年每月参与项目数
        c.execute("""
            SELECT strftime('%Y-%m', p.create_date) as month, COUNT(DISTINCT p.id)
            FROM projects p
            LEFT JOIN reports r ON p.id = r.project_id
            WHERE (p.project_leader = ? OR p.market_leader = ? OR p.creator = ?
                   OR r.reviewer1 = ? OR r.reviewer2 = ? OR r.reviewer3 = ?
                   OR r.signer1 = ? OR r.signer2 = ?)
            AND p.create_date >= ?
            GROUP BY strftime('%Y-%m', p.create_date)
            ORDER BY month
        """, (username, username, username, username, username, username, username, username, one_year_ago))
        monthly_projects = dict(c.fetchall())
        
        # 5. 报告类型分布
        # 签字的报告类型分布
        c.execute("""
            SELECT report_type, COUNT(*) 
            FROM reports 
            WHERE signer1 = ? OR signer2 = ?
            GROUP BY report_type
        """, (username, username))
        signed_report_types_result = c.fetchall()
        print(f"签字报告类型查询结果: {signed_report_types_result}")

        # 转换为字典并打印具体内容
        signed_report_types = dict(signed_report_types_result)
        print(f"签字报告类型字典: {signed_report_types}")

        # 复核的报告类型分布
        c.execute("""
            SELECT report_type, COUNT(*) 
            FROM reports 
            WHERE reviewer1 = ? OR reviewer2 = ? OR reviewer3 = ?
            GROUP BY report_type
        """, (username, username, username))
        reviewed_report_types_result = c.fetchall()
        print(f"复核报告类型查询结果: {reviewed_report_types_result}")

        # 转换为字典并打印具体内容
        reviewed_report_types = dict(reviewed_report_types_result)
        print(f"复核报告类型字典: {reviewed_report_types}")
        
        return {
            "responsible_projects": responsible_projects,
            "participated_projects": participated_projects,
            "created_reports": created_reports,
            "reviewed_reports": reviewed_reports,
            "signed_reports": signed_reports,
            "monthly_reports": monthly_reports,
            "monthly_projects": monthly_projects,
            "signed_report_types": signed_report_types,
            "reviewed_report_types": reviewed_report_types
        }

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
        for row in c.fetchall():
            project_dict = dict(zip([col[0] for col in c.description], row))
            
            # 获取负责人真实姓名
            if project_dict["project_leader"]:
                c.execute("SELECT realname FROM users WHERE username = ?", (project_dict["project_leader"],))
                leader_result = c.fetchone()
                project_dict["project_leader_realname"] = leader_result[0] if leader_result else project_dict["project_leader"]
            
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

    async def get_user_profile_data(self, request, user, db):
        """获取用户个人信息"""
        c = db.cursor()
        username = user["username"]
        
        c.execute("SELECT username, realname, user_type FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        
        # 获取用户资质
        c.execute("SELECT qualification_type FROM user_qualifications WHERE username = ?", (username,))
        qualifications = [row[0] for row in c.fetchall()]
        
        return {
            "username": user_data[0],
            "realname": user_data[1],
            "user_type": user_data[2],
            "qualifications": qualifications
        }

user_service = UserService()