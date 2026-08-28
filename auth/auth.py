import secrets
import threading
import time
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from database.database import db_manager
from utils.security import hash_password, verify_password, is_hashed

# 会话配置
SESSION_IDLE_TIMEOUT = 8 * 3600  # 会话空闲过期时间:8小时
SESSION_ABSOLUTE_TIMEOUT = 24 * 3600  # 会话最长存活时间:24小时

# 会话存储: {session_id: {"data": {...}, "created": ts, "last_seen": ts}}
sessions = {}
session_lock = threading.Lock()


def _cleanup_sessions_locked():
    """清理过期会话(调用方必须已持有 session_lock)"""
    now = time.time()
    expired = [
        sid for sid, s in sessions.items()
        if now - s["last_seen"] > SESSION_IDLE_TIMEOUT
        or now - s["created"] > SESSION_ABSOLUTE_TIMEOUT
    ]
    for sid in expired:
        del sessions[sid]


def _get_valid_session(session_id: str):
    """获取有效会话,过期返回 None"""
    if not session_id:
        return None
    with session_lock:
        _cleanup_sessions_locked()
        session = sessions.get(session_id)
        if session:
            session["last_seen"] = time.time()
            return session["data"]
    return None


def get_current_user(request: Request):
    """获取当前用户"""
    session_id = request.cookies.get("session_id")
    return _get_valid_session(session_id)


def login_required(request: Request):
    """检查登录状态"""
    session_id = request.cookies.get("session_id")
    user = _get_valid_session(session_id)
    if user is None:
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            detail="Redirect to login",
            headers={"Location": "/login"}
        )
    return user


def create_session(username: str, user_type: str):
    """创建会话"""
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    user_data = {"username": username, "user_type": user_type}
    with session_lock:
        _cleanup_sessions_locked()
        sessions[session_id] = {"data": user_data, "created": now, "last_seen": now}
    return session_id


def delete_session(session_id: str):
    """删除会话"""
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]


def verify_user_credentials(username: str, password: str, db):
    """验证用户凭据,兼容旧明文密码并在登录成功时自动升级为哈希"""
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if not row:
        return None

    cols = [d[0] for d in c.description]
    stored_password = row[cols.index("password")]
    if not verify_password(password, stored_password):
        return None

    # 旧明文密码自动升级为哈希存储
    if not is_hashed(stored_password):
        c.execute("UPDATE users SET password = ? WHERE username = ?",
                  (hash_password(password), username))
        db.commit()

    return row
