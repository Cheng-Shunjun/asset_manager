from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from database.database import db_manager
from routes import auth_routes, project_routes, report_routes, user_routes
import uvicorn
import config

app = FastAPI(
    title="项目管理系统",
    description="基于 FastAPI 的项目管理系统",
    version="1.0.0"
)

# 添加会话中间件
app.add_middleware(SessionMiddleware, secret_key=config.Config.SECRET_KEY)

# 挂载静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 全局异常处理
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"detail": "请求的资源不存在"}
    )

@app.exception_handler(500)
async def internal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"}
    )

# 注册路由
app.include_router(auth_routes.router)
app.include_router(project_routes.router)
app.include_router(report_routes.router)
app.include_router(user_routes.router)
#app.include_router(file_routes.router)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "服务运行正常"}

# 应用关闭时关闭数据库连接
@app.on_event("shutdown")
def shutdown_event():
    db_manager.close_connection()
    print("🗄️ 数据库连接已关闭")

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    print("🚀 项目管理系统启动成功")
    print("📊 数据库初始化完成")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )