@echo off
title 资产管理系统 - 开发模式
cd /d "%~dp0"

set "VPY=%~dp0venv\Scripts\python.exe"

rem ========= [1/3] 确保虚拟环境存在 =========
if not exist "%VPY%" (
    echo [1/3] 未找到虚拟环境，正在自动创建...
    py -3 -m venv venv 2>nul
    if errorlevel 1 (
        python -m venv venv
        if errorlevel 1 (
            echo [错误] 创建虚拟环境失败，请先运行 deploy.bat
            pause
            exit /b 1
        )
    )
) else (
    echo [1/3] 虚拟环境已就绪
)

rem ========= [2/3] 检查依赖，缺失则自动补装 =========
"%VPY%" -c "import fastapi, uvicorn, jinja2, multipart, dateutil, itsdangerous" >nul 2>&1
if errorlevel 1 (
    echo [2/3] 依赖不完整，正在自动安装...
    "%VPY%" -m pip install -r requirements.txt --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        "%VPY%" -m pip install -r requirements.txt --quiet
        if errorlevel 1 (
            echo [错误] 依赖安装失败，请检查网络后重试
            pause
            exit /b 1
        )
    )
) else (
    echo [2/3] 依赖检查通过
)

rem ========= [3/3] 启动开发服务器 =========
"%VPY%" --version
echo [3/3] 启动开发服务器: http://127.0.0.1:8000
echo.
"%VPY%" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
