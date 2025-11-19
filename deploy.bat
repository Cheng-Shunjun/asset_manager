@echo off
chcp 65001
title 资产管理系统 - 公网访问

echo ========================================
echo       正在启动网站服务...
echo ========================================
echo.

echo [1/3] 启动 FastAPI 服务...
start cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2/3] 等待服务启动...
timeout /t 5

echo [3/3] 启动 ngrok 隧道...
cd C:\ngrok
ngrok http 8000

echo.
pause