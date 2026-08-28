import os
import secrets

# 应用配置
class Config:
    # 密钥优先从环境变量读取;否则生成随机密钥并持久化到 .secret_key 文件,
    # 保证重启后会话仍有效,且密钥不会进入代码仓库
    @staticmethod
    def _load_secret_key() -> str:
        env_key = os.environ.get("SECRET_KEY")
        if env_key and len(env_key) >= 32:
            return env_key
        key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret_key")
        try:
            if os.path.exists(key_file):
                with open(key_file, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                if key:
                    return key
            key = secrets.token_urlsafe(48)
            with open(key_file, "w", encoding="utf-8") as f:
                f.write(key)
            return key
        except OSError:
            # 文件读写失败时退化为每次启动随机(会话不跨重启)
            return secrets.token_urlsafe(48)

    SECRET_KEY = _load_secret_key()
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