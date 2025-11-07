import secrets
import threading
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from database.database import db_manager

# 会话存储
sessions = {}
session_lock = threading.Lock()

def get_current_user(request: Request):
    """获取当前用户"""
    session_id = request.cookies.get("session_id")
    with session_lock:
        if session_id and session_id in sessions:
            return sessions[session_id]
    return None

def login_required(request: Request):
    """检查登录状态"""
    session_id = request.cookies.get("session_id")
    with session_lock:
        if not session_id or session_id not in sessions:
            raise HTTPException(
                status_code=HTTP_303_SEE_OTHER,
                detail="Redirect to login",
                headers={"Location": "/login"}
            )
        return sessions[session_id]

def create_session(username: str, user_type: str):
    """创建会话"""
    session_id = secrets.token_urlsafe(16)
    user_data = {"username": username, "user_type": user_type}
    with session_lock:
        sessions[session_id] = user_data
    return session_id

def delete_session(session_id: str):
    """删除会话"""
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]

def verify_user_credentials(username: str, password: str, db):
    """验证用户凭据"""
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()