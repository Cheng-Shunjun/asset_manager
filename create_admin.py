import sqlite3

def create_admin_user():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    
    # 创建管理员用户
    username = "admin"
    realname = "系统管理员"
    user_type = "admin"
    password = "123456"  # 你可以修改密码
    
    try:
        c.execute(
            "INSERT INTO users (username, realname, user_type, password) VALUES (?, ?, ?, ?)",
            (username, realname, user_type, password)
        )
        conn.commit()
        print(f"管理员用户创建成功！")
        print(f"用户名: {username}")
        print(f"密码: {password}")
        print(f"用户类型: {user_type}")
    except sqlite3.IntegrityError:
        print("管理员用户已存在！")
    
    try:
        c.execute(
            "INSERT INTO projects (name, creator, amount, start_date, end_date, contract_file, asset_files, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("中和拆迁", "admin", 1200000, "2025-12-26", "", "", "", "active")
        )
        conn.commit()
    except sqlite3.IntegrityError:
        print("创建项目失败！")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_user()