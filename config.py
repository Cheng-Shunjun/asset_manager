import os

# 应用配置
class Config:
    SECRET_KEY = "supersecretkey123"
    UPLOAD_FOLDER = 'static/uploads'
    DATABASE_PATH = 'db.sqlite3'
    
    # 文件相关配置
    DEBUG = True
    MAX_FILE_SIZE_MB = 10  # 最大文件大小 10MB
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 
        'jpg', 'jpeg', 'png', 'txt'
    }

# 创建必要的目录
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)