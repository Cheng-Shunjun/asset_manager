@echo off
title 资产管理系统 - 一键部署
cd /d "%~dp0"

echo ========================================
echo       资产管理系统 一键部署脚本
echo ========================================
echo.

rem ========= [1/5] 检测 Python =========
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [错误] 未检测到 Python，正在尝试通过 winget 安装...
    winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [错误] 自动安装 Python 失败，请手动安装 Python 3.10+ 后重新运行本脚本:
        echo        https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PY=py -3"
)
echo [1/5] Python 检测完成: %PY%

rem ========= [2/5] 创建虚拟环境 =========
if not exist "venv\Scripts\python.exe" (
    echo [2/5] 正在创建虚拟环境 venv ...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
) else (
    echo [2/5] 虚拟环境已存在，跳过创建
)
set "VPY=%~dp0venv\Scripts\python.exe"

rem ========= [3/5] 安装依赖 =========
echo [3/5] 正在安装依赖（首次安装约需几分钟）...
"%VPY%" -m pip install -r requirements.txt --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo 清华镜像失败，改用官方 PyPI 源重试...
    "%VPY%" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络后重新运行本脚本
        pause
        exit /b 1
    )
)
echo       依赖安装完成

rem ========= [4/5] 启动 FastAPI 服务 =========
echo [4/5] 正在启动 FastAPI 服务...
start "资产管理系统服务" cmd /k "%VPY% -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo       等待服务启动...
timeout /t 5 /nobreak >nul

rem ========= [5/5] 启动 ngrok 隧道（可选） =========
echo [5/5] 检查 ngrok ...
where ngrok >nul 2>&1
if %errorlevel%==0 (
    echo       检测到 ngrok，启动公网隧道...
    ngrok http 8000
) else if exist "C:\ngrok\ngrok.exe" (
    echo       检测到 C:\ngrok\ngrok.exe，启动公网隧道...
    cd /d C:\ngrok
    ngrok http 8000
) else (
    echo       未检测到 ngrok，跳过公网隧道。
    echo       本机访问: http://127.0.0.1:8000
)

echo.
echo ========================================
echo       部署完成！
echo       本机访问:  http://127.0.0.1:8000
echo       局域网访问: http://本机IP:8000
echo ========================================
echo.
pause
