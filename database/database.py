import sqlite3
import threading
from contextlib import contextmanager
from config import Config

class Database:
    def __init__(self, db_path=Config.DATABASE_PATH):
        self.db_path = db_path
        self.local = threading.local()
        self.init_db()
    
    def get_connection(self):
        """为每个线程创建独立的数据库连接"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            del self.local.connection
    
    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 用户表
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        realname TEXT,
                        user_type TEXT,
                        password TEXT)''')
        
        # 项目表
        c.execute('''CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_no TEXT,
                        name TEXT,
                        project_type TEXT,
                        client_name TEXT,
                        market_leader TEXT,
                        project_leader TEXT,
                        progress TEXT,
                        report_numbers TEXT,
                        amount REAL,
                        is_paid TEXT,
                        creator TEXT,
                        creator_realname TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        status TEXT,
                        contract_file TEXT,
                        create_date TEXT
                    )''')
        
        # 报告表
        c.execute('''CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_no TEXT NOT NULL,
                        project_id INTEGER,
                        file_paths TEXT,
                        creator TEXT,
                        creator_realname TEXT NOT NULL,
                        create_date TEXT,
                        reviewer1 TEXT,
                        reviewer2 TEXT,
                        reviewer3 TEXT,
                        signer1 TEXT,
                        signer2 TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects (id)
                    )''')
        
        # 报告文件表
        c.execute('''CREATE TABLE IF NOT EXISTS report_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_id INTEGER,
                        file_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        uploader_username TEXT NOT NULL,
                        uploader_realname TEXT NOT NULL,
                        upload_time TEXT NOT NULL,
                        file_size INTEGER,
                        FOREIGN KEY (report_id) REFERENCES reports (id)
                    )''')
        conn.commit()
    
    @contextmanager
    def get_db(self):
        """数据库上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e

# 创建全局数据库实例
db_manager = Database()

# FastAPI 依赖项
def get_db():
    """数据库依赖"""
    with db_manager.get_db() as conn:
        yield conn