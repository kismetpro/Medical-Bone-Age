chcp 65001
@echo off
title BoneAgeWeb 一键启动

echo ================================================
echo   BoneAgeWeb - AI 骨龄评估系统
echo   一键启动脚本 (Windows)
echo ================================================
echo.

:: --- 切换到脚本所在目录 ---
cd /d "%~dp0"

:: --- 启动后端 ---
echo [后端] 正在启动 FastAPI 后端服务 (端口 8000)...
if exist "backend\venv\Scripts\activate.bat" (
    echo [后端] 检测到虚拟环境，正在激活...
    start "BoneAgeWeb-Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else if exist "backend\.venv\Scripts\activate.bat" (
    echo [后端] 检测到 .venv 虚拟环境，正在激活...
    start "BoneAgeWeb-Backend" cmd /k "cd /d %~dp0backend && call .venv\Scripts\activate.bat && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) else (
    echo [后端] 未检测到虚拟环境，使用系统 Python...
    start "BoneAgeWeb-Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

:: --- 等待后端初始化 ---
echo [后端] 等待 3 秒让后端完成初始化...
timeout /t 3 /nobreak > nul

:: --- 启动前端 ---
echo [前端] 正在启动 Vite 前端开发服务器 (端口 5173)...
start "BoneAgeWeb-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak > nul
start http://localhost:5173/