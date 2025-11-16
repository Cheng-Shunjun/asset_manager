import os
import sqlite3
from datetime import datetime

DB_FILE = "db.sqlite3"

def init_database():
    # 如果数据库文件已存在，先删除
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("🗑️ 已删除旧数据库文件。")

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ========= 创建 users 表 =========
    # 在 database.py 的 init_db 方法中更新 users 表
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        realname TEXT,
        user_type TEXT,
        password TEXT,
        phone TEXT,
        email TEXT,
        hire_date TEXT,
        education TEXT,
        position TEXT,
        department TEXT,
        status TEXT DEFAULT 'active',  -- active-在职, inactive-离职
        create_time TEXT DEFAULT CURRENT_TIMESTAMP,
        update_time TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    print("✅ users 表创建完成。")

    # ========= 创建 projects 表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_no TEXT,                 -- ① 项目序号
        name TEXT,                       -- ② 项目名称
        project_type TEXT,               -- ③ 项目类型
        client_name TEXT,                -- ④ 甲方名称
        market_leader TEXT,              -- ⑤ 市场部负责人用户名
        project_leader TEXT,             -- ⑥ 项目负责人用户名
        progress TEXT,                   -- ⑦ 项目进度
        report_numbers TEXT,             -- ⑧ 报告号（多个以逗号分隔）
        amount REAL,                     -- ⑨ 合同金额
        is_paid TEXT,                    -- ⑩ 是否收费（是/否）
        creator TEXT,                    -- ⑪ 项目创建人用户名
        creator_realname TEXT,           -- ⑫ 项目创建人真实姓名
        start_date TEXT,                 -- ⑬ 开始日期
        end_date TEXT,                   -- ⑭ 结束日期
        status TEXT,                     -- ⑮ 状态
        contract_file TEXT,
        create_date TEXT
    )
    """)
    print("✅ projects 表创建完成。")

    # ========= 创建 reports 表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_no TEXT NOT NULL,         -- 报告号
        project_id INTEGER,              -- 关联的项目ID
        report_type TEXT,                -- 报告类型（新增字段）
        file_paths TEXT,                 -- 文件路径（多个以逗号分隔）
        creator TEXT,                    -- 创建人用户名
        creator_realname TEXT,           -- 创建人真实姓名
        create_date TEXT,                -- 创建日期
        reviewer1 TEXT,                  -- 复核人1用户名
        reviewer2 TEXT,                  -- 复核人2用户名
        reviewer3 TEXT,                  -- 复核人3用户名
        signer1 TEXT,                    -- 签字人1用户名
        signer2 TEXT,                    -- 签字人2用户名
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    """)
    print("✅ reports 表创建完成。")

    # ========= 创建 report_files 表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS report_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,               -- 关联的报告ID
        file_path TEXT NOT NULL,         -- 文件路径
        file_name TEXT NOT NULL,         -- 原文件名
        uploader_username TEXT NOT NULL, -- 上传者用户名
        uploader_realname TEXT NOT NULL, -- 上传者真实姓名
        upload_time TEXT NOT NULL,       -- 上传时间
        file_size INTEGER,               -- 文件大小（字节）
        FOREIGN KEY (report_id) REFERENCES reports (id)
    )
    """)
    print("✅ report_files 表创建完成。")

    # ========= 创建 contract_files 表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS contract_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,               -- 关联的项目ID
        file_path TEXT NOT NULL,          -- 文件路径
        file_name TEXT NOT NULL,          -- 原文件名
        uploader_username TEXT NOT NULL,  -- 上传者用户名
        uploader_realname TEXT NOT NULL,  -- 上传者真实姓名
        upload_time TEXT NOT NULL,        -- 上传时间
        file_size INTEGER,                -- 文件大小（字节）
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    """)
    print("✅ contract_files 表创建完成。")

    # ========= 创建资质表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_qualifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        qualification_type TEXT NOT NULL,
        qualification_number TEXT,
        issue_date TEXT,
        expiry_date TEXT,
        issue_authority TEXT,
        FOREIGN KEY (username) REFERENCES users (username),
        UNIQUE(username, qualification_type)
    )
    """)
    print("✅ user_qualifications 表创建完成。")

    # ========= 插入管理员用户 =========
    admin_user = (
        "zhangwen", "张文", "admin", "123456",
        "13800138000", "zhangwen@company.com", "2020-03-15",
        "硕士", "总经理", "管理层", "2020-03-15 09:00:00", "2025-01-01 10:00:00"
    )

    c.execute("""
        INSERT INTO users (username, realname, user_type, password, 
                          phone, email, hire_date, education, position, department, create_time, update_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, admin_user)
    print("✅ 管理员账户创建成功。")

    # ========= 插入测试用户 =========
    test_users = [
        # (username, realname, user_type, password, phone, email, hire_date, education, position, department)
        ("zhangsan", "张三", "user", "123456", "13900139001", "zhangsan@company.com", "2021-05-10", "本科", "技术总监", "技术部"),
        ("lisi", "李四", "user", "123456", "13900139002", "lisi@company.com", "2021-08-20", "硕士", "资产评估师", "评估部"),
        ("wangwu", "王五", "user", "123456", "13900139003", "wangwu@company.com", "2022-01-15", "本科", "房地产估价师", "评估部"),
        ("zhaoliu", "赵六", "user", "123456", "13900139004", "zhaoliu@company.com", "2022-03-22", "博士", "土地估价师", "评估部"),
        ("sunqi", "孙七", "user", "123456", "13900139005", "sunqi@company.com", "2022-06-30", "本科", "评估助理", "评估部"),
        ("zhouba", "周八", "user", "123456", "13900139006", "zhouba@company.com", "2023-02-14", "硕士", "评估助理", "评估部"),
        ("wujiu", "吴九", "user", "123456", "13900139007", "wujiu@company.com", "2023-07-01", "本科", "行政", "行政部"),
        ("zhengshi", "郑十", "user", "123456", "13900139008", "zhengshi@company.com", "2024-01-08", "大专", "财务", "财务部"),
        ("liushi", "刘石", "user", "123456", "13900139009", "liushi@company.com", "2023-09-10", "硕士", "总经理助理", "管理层"),
        ("chenyi", "陈一", "user", "123456", "13900139010", "chenyi@company.com", "2024-03-01", "本科", "市场专员", "市场部")
    ]

    c.executemany("""
        INSERT INTO users (username, realname, user_type, password, phone, email, hire_date, education, position, department)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, test_users)
    print("✅ 测试用户创建完成。")

    # ========= 插入测试资质数据 =========
    qualifications = [
        # (username, qualification_type, qualification_number, issue_date, expiry_date, issue_authority)
        ("zhangwen", "资产评估师", "P123456789", "2018-06-15", "2028-06-15", "中国资产评估协会"),
        ("zhangwen", "房地产估价师", "F987654321", "2019-03-20", "2029-03-20", "中国房地产估价师协会"),
        ("zhangwen", "土地估价师", "L456789123", "2020-11-05", "2030-11-05", "中国土地估价师协会"),
        ("zhangsan", "资产评估师", "P234567890", "2020-08-12", "2030-08-12", "中国资产评估协会"),
        ("lisi", "房地产估价师", "F876543210", "2021-05-18", "2031-05-18", "中国房地产估价师协会"),
        ("wangwu", "土地估价师", "L567891234", "2022-02-25", "2032-02-25", "中国土地估价师协会"),
        ("zhaoliu", "资产评估师", "P345678901", "2019-11-30", "2029-11-30", "中国资产评估协会"),
        ("zhaoliu", "房地产估价师", "F765432109", "2021-09-15", "2031-09-15", "中国房地产估价师协会"),
        ("sunqi", "资产评估师", "P456789012", "2023-04-10", "2033-04-10", "中国资产评估协会"),
        ("zhouba", "房地产估价师", "F654321098", "2022-12-20", "2032-12-20", "中国房地产估价师协会"),
        ("wujiu", "土地估价师", "L678912345", "2023-07-05", "2033-07-05", "中国土地估价师协会"),
        ("zhengshi", "资产评估师", "P567890123", "2024-01-15", "2034-01-15", "中国资产评估协会"),
        ("liushi", "房地产估价师", "F543210987", "2022-08-08", "2032-08-08", "中国房地产估价师协会"),
        ("chenyi", "土地估价师", "L789123456", "2023-03-25", "2033-03-25", "中国土地估价师协会")
    ]

    c.executemany("""
        INSERT INTO user_qualifications (username, qualification_type, qualification_number, issue_date, expiry_date, issue_authority)
        VALUES (?, ?, ?, ?, ?, ?)
    """, qualifications)
    print("✅ 用户资质数据已添加。")

    # ========= 插入测试项目数据 =========
    current_year = datetime.now().year
    projects = [
        (
            f"P{current_year}_001", "中和拆迁项目", "土地", "中和市城市建设局",
            "zhangsan", "lisi", "前期规划阶段", "",
            1200000.00, "是", "zhangwen", "张文", "2025-01-10", "",
            "active", "", "2025-01-10 15:32:21"
        ),
        (
            f"P{current_year}_002", "智慧城市基础设施建设", "房地产", "中和市智慧城市办",
            "wangwu", "zhaoliu", "验收阶段", "",
            2800000.00, "是", "zhangwen", "张文", "2024-03-01", "2024-06-01",
            "completed", "", "2024-03-01 09:15:30"
        ),
        (
            f"P{current_year}_003", "学校翻新工程", "资产", "中和市教育局",
            "sunqi", "zhouba", "暂停中", "",
            800000.00, "否", "zhangwen", "张文", "2023-09-01", "2024-09-01",
            "cancelled", "", "2023-09-01 14:20:45"
        ),
        (
            f"P{current_year}_004", "新能源车站项目", "资产", "中和交通投资集团",
            "wujiu", "zhengshi", "执行中", "",
            10000000.00, "是", "zhangwen", "张文", "2025-06-01", "",
            "active", "", "2025-06-01 10:05:18"
        ),
        (
            f"P{current_year}_005", "旧城区道路改造", "房地产", "中和市市政建设局",
            "zhangsan", "wangwu", "已取消", "",
            15000000.00, "否", "zhangwen", "张文", "2022-05-10", "",
            "cancelled", "", "2022-05-10 16:45:22"
        ),
        (
            f"P{current_year}_006", "污水处理厂升级项目", "资产", "中和市环保局",
            "lisi", "zhaoliu", "施工阶段", "",
            4200000.00, "是", "zhangwen", "张文", "2025-02-01", "",
            "active", "", "2025-02-01 11:30:15"
        )
    ]

    c.executemany("""
        INSERT INTO projects (
            project_no, name, project_type, client_name, 
            market_leader, project_leader, progress, report_numbers, 
            amount, is_paid, creator, creator_realname, start_date, end_date, 
            status, contract_file, create_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, projects)
    print("✅ 所有示例项目数据已添加。")

    # ========= 插入测试报告数据 =========
    reports = [
        # 项目1的报告 - 土地报告
        (
            f"川鼎土估[{current_year}]字第01001号", 1, "土地报告",
            "static/uploads/zh_report1.pdf,static/uploads/zh_attachment1.docx",
            "zhangwen", "张文", "2025-01-15 10:30:00", "zhangsan", "lisi", "wangwu", "zhaoliu", "sunqi"
        ),
        (
            f"川鼎土估[{current_year}]字第01002号", 1, "土地报告",
            "static/uploads/zh_report2.pdf",
            "zhangwen", "张文", "2025-01-20 14:15:00", "wangwu", "zhaoliu", "sunqi", "zhouba", "wujiu"
        ),
        # 项目2的报告 - 房地产估价报告
        (
            f"川鼎房估[{current_year}]字第02001号", 2, "房地产估价报告",
            "static/uploads/sc_report.pdf,static/uploads/sc_data.xlsx,static/uploads/sc_charts.pdf",
            "zhangwen", "张文", "2024-05-20 09:45:00", "lisi", "wangwu", "zhaoliu", "sunqi", "zhouba"
        ),
        # 项目3的报告 - 资产评估报告
        (
            f"川鼎评报[{current_year}]字第03001号", 3, "资产评估报告",
            "static/uploads/edu_report.pdf",
            "zhangwen", "张文", "2023-10-10 16:20:00", "zhangsan", "lisi", "wangwu", "zhaoliu", "sunqi"
        ),
        # 项目4的报告 - 资产估值报告
        (
            f"川鼎估评[{current_year}]字第04001号", 4, "资产估值报告",
            "static/uploads/ev_report1.pdf,static/uploads/ev_design.docx",
            "zhangwen", "张文", "2025-06-15 11:00:00", "zhaoliu", "sunqi", "zhouba", "wujiu", "zhengshi"
        ),
        (
            f"川鼎估评[{current_year}]字第04002号", 4, "资产估值报告",
            "static/uploads/ev_report2.pdf",
            "zhangwen", "张文", "2025-07-01 15:30:00", "sunqi", "zhouba", "wujiu", "zhengshi", "zhangsan"
        ),
        # 项目5的报告 - 房地产咨询报告
        (
            f"川鼎房咨[{current_year}]字第05001号", 5, "房地产咨询报告",
            "static/uploads/rd_report.pdf",
            "zhangwen", "张文", "2022-06-01 13:45:00", "zhangsan", "lisi", "wangwu", "zhaoliu", "sunqi"
        ),
        # 项目6的报告 - 资产咨询报告
        (
            f"川鼎咨评[{current_year}]字第06001号", 6, "资产咨询报告",
            "static/uploads/wp_report1.pdf,static/uploads/wp_analysis.xlsx",
            "zhangwen", "张文", "2025-02-15 10:15:00", "lisi", "zhaoliu", "sunqi", "zhouba", "wujiu"
        ),
        (
            f"川鼎咨评[{current_year}]字第06002号", 6, "资产咨询报告",
            "static/uploads/wp_report2.pdf",
            "zhangwen", "张文", "2025-03-01 14:50:00", "wangwu", "sunqi", "zhouba", "wujiu", "zhengshi"
        ),
        (
            f"川鼎咨评[{current_year}]字第06003号", 6, "资产咨询报告",
            "static/uploads/wp_report3.pdf,static/uploads/wp_final.docx",
            "zhangwen", "张文", "2025-03-20 16:10:00", "zhaoliu", "zhouba", "wujiu", "zhengshi", "zhangsan"
        )
    ]

    c.executemany("""
        INSERT INTO reports (
            report_no, project_id, report_type, file_paths, creator, creator_realname, create_date,
            reviewer1, reviewer2, reviewer3, signer1, signer2
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, reports)
    print("✅ 所有示例报告数据已添加。")

    # ========= 插入测试文件数据 =========
    file_records = [
        # 报告1的文件
        (1, "static/uploads/zh_report1.pdf", "zh_report1.pdf", "zhangwen", "张文", "2025-01-15 10:30:00", 1024000),
        (1, "static/uploads/zh_attachment1.docx", "zh_attachment1.docx", "zhangwen", "张文", "2025-01-15 10:30:00", 512000),
        
        # 报告2的文件
        (2, "static/uploads/zh_report2.pdf", "zh_report2.pdf", "zhangwen", "张文", "2025-01-20 14:15:00", 1536000),
        
        # 报告3的文件
        (3, "static/uploads/sc_report.pdf", "sc_report.pdf", "zhangwen", "张文", "2024-05-20 09:45:00", 2048000),
        (3, "static/uploads/sc_data.xlsx", "sc_data.xlsx", "zhangwen", "张文", "2024-05-20 09:45:00", 256000),
        (3, "static/uploads/sc_charts.pdf", "sc_charts.pdf", "zhangwen", "张文", "2024-05-20 09:45:00", 768000),
        
        # 报告4的文件
        (4, "static/uploads/edu_report.pdf", "edu_report.pdf", "zhangwen", "张文", "2023-10-10 16:20:00", 896000),
        
        # 报告5的文件
        (5, "static/uploads/ev_report1.pdf", "ev_report1.pdf", "zhangwen", "张文", "2025-06-15 11:00:00", 1280000),
        (5, "static/uploads/ev_design.docx", "ev_design.docx", "zhangwen", "张文", "2025-06-15 11:00:00", 384000),
        
        # 报告6的文件
        (6, "static/uploads/ev_report2.pdf", "ev_report2.pdf", "zhangwen", "张文", "2025-07-01 15:30:00", 1152000),
        
        # 报告7的文件
        (7, "static/uploads/rd_report.pdf", "rd_report.pdf", "zhangwen", "张文", "2022-06-01 13:45:00", 960000),
        
        # 报告8的文件
        (8, "static/uploads/wp_report1.pdf", "wp_report1.pdf", "zhangwen", "张文", "2025-02-15 10:15:00", 1408000),
        (8, "static/uploads/wp_analysis.xlsx", "wp_analysis.xlsx", "zhangwen", "张文", "2025-02-15 10:15:00", 320000),
        
        # 报告9的文件
        (9, "static/uploads/wp_report2.pdf", "wp_report2.pdf", "zhangwen", "张文", "2025-03-01 14:50:00", 1664000),
        
        # 报告10的文件
        (10, "static/uploads/wp_report3.pdf", "wp_report3.pdf", "zhangwen", "张文", "2025-03-20 16:10:00", 1920000),
        (10, "static/uploads/wp_final.docx", "wp_final.docx", "zhangwen", "张文", "2025-03-20 16:10:00", 448000),
    ]

    c.executemany("""
        INSERT INTO report_files 
        (report_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, file_records)
    print("✅ 所有示例报告文件数据已添加。")

    # ========= 插入测试合同文件数据 =========
    contract_files_data = [
        (1, "static/uploads/contract1.pdf", "项目合同.pdf", "zhangwen", "张文", "2025-01-10 15:32:21", 2048000),
        (1, "static/uploads/contract_attachment.docx", "合同附件.docx", "zhangsan", "张三", "2025-01-12 10:15:30", 512000),
        (2, "static/uploads/sc_contract.pdf", "智慧城市项目合同.pdf", "zhangwen", "张文", "2024-03-01 09:15:30", 3072000),
        (4, "static/uploads/ev_contract.pdf", "新能源车站合同.pdf", "wujiu", "吴九", "2025-06-01 10:05:18", 2560000),
        (6, "static/uploads/wp_contract.pdf", "污水处理厂合同.pdf", "lisi", "李四", "2025-02-01 11:30:15", 1792000),
    ]

    c.executemany("""
        INSERT INTO contract_files 
        (project_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, contract_files_data)
    print("✅ 所有示例合同文件数据已添加。")

    # 更新项目的 report_numbers 字段
    for project_id in range(1, 7):  # 假设有6个项目
        c.execute("SELECT report_no FROM reports WHERE project_id = ?", (project_id,))
        project_reports = c.fetchall()
        if project_reports:
            report_numbers = ",".join([report[0] for report in project_reports])
            c.execute("UPDATE projects SET report_numbers = ? WHERE id = ?", (report_numbers, project_id))
    
    print("✅ 项目报告号已更新。")

    conn.commit()
    conn.close()
    print("🎉 数据库初始化完成！")
    print(f"📊 数据统计:")
    print(f"   - 用户数量: {len(test_users) + 1}")  # +1 管理员
    print(f"   - 项目数量: {len(projects)}")
    print(f"   - 报告数量: {len(reports)}")
    print(f"   - 文件记录数量: {len(file_records)}")
    print(f"   - 资质记录数量: {len(qualifications)}")

if __name__ == "__main__":
    init_database()