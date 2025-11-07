from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database.database import db_manager, get_db
from auth.auth import login_required
import sqlite3

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/user_manager", response_class=HTMLResponse)
async def user_manager(
    request: Request,
    user: dict = Depends(login_required),
    db: sqlite3.Connection = Depends(get_db)
):
    c = db.cursor()
    c.execute("SELECT username, realname, user_type, password FROM users")
    users = c.fetchall()
    
    users_list = []
    for user_row in users:
        users_list.append({
            'username': user_row[0],
            'realname': user_row[1],
            'user_type': user_row[2],
            'password': user_row[3]
        })
    
    return templates.TemplateResponse("user_manager.html", {
        "request": request,
        "users": users_list,
        "user": user
    })