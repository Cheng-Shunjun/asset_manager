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
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        realname TEXT,
        user_type TEXT,
        password TEXT
    )
    """)
    print("✅ users 表创建完成。")

    # ========= 创建 projects 表 =========
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_no TEXT,                 -- ① 项目序号
        name TEXT,                       -- ② 项目名称
        project_type TEXT,               -- ③ 项目类型
        client_name TEXT,                -- ④ 甲方名称
        market_leader TEXT,              -- ⑤ 市场部负责人
        project_leader TEXT,             -- ⑥ 项目负责人
        progress TEXT,                   -- ⑦ 项目进度
        report_numbers TEXT,             -- ⑧ 报告号（多个以逗号分隔）
        amount REAL,                     -- ⑨ 合同金额
        is_paid TEXT,                    -- ⑩ 是否收费（是/否）
        creator TEXT,                    -- ⑪ 项目创建人
        start_date TEXT,                 -- ⑫ 开始日期
        end_date TEXT,                   -- ⑬ 结束日期
        status TEXT,                     -- ⑭ 状态
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
        file_paths TEXT,                 -- 文件路径（多个以逗号分隔）
        creator TEXT,                    -- 创建人
        create_date TEXT,                -- 创建日期
        reviewer1 TEXT,                  -- 复核人1
        reviewer2 TEXT,                  -- 复核人2
        reviewer3 TEXT,                  -- 复核人3
        signer1 TEXT,                    -- 签字人1
        signer2 TEXT,                    -- 签字人2
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

    # ========= 插入管理员用户 =========
    username = "admin"
    realname = "系统管理员"
    user_type = "admin"
    password = "123456"

    c.execute(
        "INSERT INTO users (username, realname, user_type, password) VALUES (?, ?, ?, ?)",
        (username, realname, user_type, password)
    )
    print("✅ 管理员账户创建成功。")

    # ========= 插入测试用户 =========
    test_users = [
        ("zhangsan", "张三", "user", "123456"),
        ("lisi", "李四", "user", "123456"),
        ("wangwu", "王五", "user", "123456"),
        ("zhaoliu", "赵六", "user", "123456"),
        ("sunqi", "孙七", "user", "123456"),
        ("zhouba", "周八", "user", "123456"),
        ("wujiu", "吴九", "user", "123456"),
        ("zhengshi", "郑十", "user", "123456")
    ]
    
    c.executemany(
        "INSERT INTO users (username, realname, user_type, password) VALUES (?, ?, ?, ?)",
        test_users
    )
    print("✅ 测试用户创建完成。")

    # ========= 插入测试项目数据 =========
    current_year = datetime.now().year
    projects = [
        (
            f"P{current_year}_001", "中和拆迁项目", "土地", "中和市城市建设局",
            "张三", "李四", "前期规划阶段", "",
            1200000.00, "是", "admin", "2025-01-10", "",
            "active", "", "2025-01-10 15:32:21"
        ),
        (
            f"P{current_year}_002", "智慧城市基础设施建设", "房地产", "中和市智慧城市办",
            "王五", "赵六", "验收阶段", "",
            2800000.00, "是", "admin", "2024-03-01", "2024-06-01",
            "completed", "", "2024-03-01 09:15:30"
        ),
        (
            f"P{current_year}_003", "学校翻新工程", "资产", "中和市教育局",
            "孙七", "周八", "暂停中", "",
            800000.00, "否", "admin", "2023-09-01", "2024-09-01",
            "paused", "", "2023-09-01 14:20:45"
        ),
        (
            f"P{current_year}_004", "新能源车站项目", "资产", "中和交通投资集团",
            "吴九", "郑十", "执行中", "",
            10000000.00, "是", "admin", "2025-06-01", "",
            "active", "", "2025-06-01 10:05:18"
        ),
        (
            f"P{current_year}_005", "旧城区道路改造", "房地产", "中和市市政建设局",
            "张三", "王五", "已取消", "",
            15000000.00, "否", "admin", "2022-05-10", "",
            "cancelled", "", "2022-05-10 16:45:22"
        ),
        (
            f"P{current_year}_006", "污水处理厂升级项目", "资产", "中和市环保局",
            "李四", "赵六", "施工阶段", "",
            4200000.00, "是", "admin", "2025-02-01", "",
            "active", "", "2025-02-01 11:30:15"
        )
    ]

    c.executemany("""
        INSERT INTO projects (
            project_no, name, project_type, client_name, 
            market_leader, project_leader, progress, report_numbers, 
            amount, is_paid, creator, start_date, end_date, 
            status, contract_file, create_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, projects)
    print("✅ 所有示例项目数据已添加。")

    # ========= 插入测试报告数据 =========
    # 使用新的报告号格式
    reports = [
        # 项目1的报告 - 土地报告
        (
            f"川鼎土估[{current_year}]字第01001号", 1, "static/uploads/zh_report1.pdf,static/uploads/zh_attachment1.docx",
            "admin", "2025-01-15 10:30:00", "张三", "李四", "王五", "赵六", "孙七"
        ),
        (
            f"川鼎土估[{current_year}]字第01002号", 1, "static/uploads/zh_report2.pdf",
            "admin", "2025-01-20 14:15:00", "王五", "赵六", "孙七", "周八", "吴九"
        ),
        # 项目2的报告 - 房地产估价报告
        (
            f"川鼎房估[{current_year}]字第02001号", 2, "static/uploads/sc_report.pdf,static/uploads/sc_data.xlsx,static/uploads/sc_charts.pdf",
            "admin", "2024-05-20 09:45:00", "李四", "王五", "赵六", "孙七", "周八"
        ),
        # 项目3的报告 - 资产评估报告
        (
            f"川鼎评报[{current_year}]字第03001号", 3, "static/uploads/edu_report.pdf",
            "admin", "2023-10-10 16:20:00", "张三", "李四", "王五", "赵六", "孙七"
        ),
        # 项目4的报告 - 资产估值报告
        (
            f"川鼎估评[{current_year}]字第04001号", 4, "static/uploads/ev_report1.pdf,static/uploads/ev_design.docx",
            "admin", "2025-06-15 11:00:00", "赵六", "孙七", "周八", "吴九", "郑十"
        ),
        (
            f"川鼎估评[{current_year}]字第04002号", 4, "static/uploads/ev_report2.pdf",
            "admin", "2025-07-01 15:30:00", "孙七", "周八", "吴九", "郑十", "张三"
        ),
        # 项目5的报告 - 房地产咨询报告
        (
            f"川鼎房咨[{current_year}]字第05001号", 5, "static/uploads/rd_report.pdf",
            "admin", "2022-06-01 13:45:00", "张三", "李四", "王五", "赵六", "孙七"
        ),
        # 项目6的报告 - 资产咨询报告
        (
            f"川鼎咨评[{current_year}]字第06001号", 6, "static/uploads/wp_report1.pdf,static/uploads/wp_analysis.xlsx",
            "admin", "2025-02-15 10:15:00", "李四", "赵六", "孙七", "周八", "吴九"
        ),
        (
            f"川鼎咨评[{current_year}]字第06002号", 6, "static/uploads/wp_report2.pdf",
            "admin", "2025-03-01 14:50:00", "王五", "孙七", "周八", "吴九", "郑十"
        ),
        (
            f"川鼎咨评[{current_year}]字第06003号", 6, "static/uploads/wp_report3.pdf,static/uploads/wp_final.docx",
            "admin", "2025-03-20 16:10:00", "赵六", "周八", "吴九", "郑十", "张三"
        )
    ]

    c.executemany("""
        INSERT INTO reports (
            report_no, project_id, file_paths, creator, create_date,
            reviewer1, reviewer2, reviewer3, signer1, signer2
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, reports)
    print("✅ 所有示例报告数据已添加。")

    # ========= 插入测试文件数据 =========
    report_files_data = []
    
    # 为每个报告的文件创建详细记录
    file_records = [
        # 报告1的文件
        (1, "static/uploads/zh_report1.pdf", "zh_report1.pdf", "admin", "系统管理员", "2025-01-15 10:30:00", 1024000),
        (1, "static/uploads/zh_attachment1.docx", "zh_attachment1.docx", "admin", "系统管理员", "2025-01-15 10:30:00", 512000),
        
        # 报告2的文件
        (2, "static/uploads/zh_report2.pdf", "zh_report2.pdf", "admin", "系统管理员", "2025-01-20 14:15:00", 1536000),
        
        # 报告3的文件
        (3, "static/uploads/sc_report.pdf", "sc_report.pdf", "admin", "系统管理员", "2024-05-20 09:45:00", 2048000),
        (3, "static/uploads/sc_data.xlsx", "sc_data.xlsx", "admin", "系统管理员", "2024-05-20 09:45:00", 256000),
        (3, "static/uploads/sc_charts.pdf", "sc_charts.pdf", "admin", "系统管理员", "2024-05-20 09:45:00", 768000),
        
        # 报告4的文件
        (4, "static/uploads/edu_report.pdf", "edu_report.pdf", "admin", "系统管理员", "2023-10-10 16:20:00", 896000),
        
        # 报告5的文件
        (5, "static/uploads/ev_report1.pdf", "ev_report1.pdf", "admin", "系统管理员", "2025-06-15 11:00:00", 1280000),
        (5, "static/uploads/ev_design.docx", "ev_design.docx", "admin", "系统管理员", "2025-06-15 11:00:00", 384000),
        
        # 报告6的文件
        (6, "static/uploads/ev_report2.pdf", "ev_report2.pdf", "admin", "系统管理员", "2025-07-01 15:30:00", 1152000),
        
        # 报告7的文件
        (7, "static/uploads/rd_report.pdf", "rd_report.pdf", "admin", "系统管理员", "2022-06-01 13:45:00", 960000),
        
        # 报告8的文件
        (8, "static/uploads/wp_report1.pdf", "wp_report1.pdf", "admin", "系统管理员", "2025-02-15 10:15:00", 1408000),
        (8, "static/uploads/wp_analysis.xlsx", "wp_analysis.xlsx", "admin", "系统管理员", "2025-02-15 10:15:00", 320000),
        
        # 报告9的文件
        (9, "static/uploads/wp_report2.pdf", "wp_report2.pdf", "admin", "系统管理员", "2025-03-01 14:50:00", 1664000),
        
        # 报告10的文件
        (10, "static/uploads/wp_report3.pdf", "wp_report3.pdf", "admin", "系统管理员", "2025-03-20 16:10:00", 1920000),
        (10, "static/uploads/wp_final.docx", "wp_final.docx", "admin", "系统管理员", "2025-03-20 16:10:00", 448000),
    ]

    c.executemany("""
        INSERT INTO report_files 
        (report_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, file_records)
    print("✅ 所有示例文件数据已添加。")

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

if __name__ == "__main__":
    init_database()