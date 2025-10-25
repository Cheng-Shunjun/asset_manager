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
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin_user()