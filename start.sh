#!/usr/bin/env bash
# ================================================
#   BoneAgeWeb - AI 骨龄评估系统
#   一键启动脚本 (Linux / macOS / WSL)
# ================================================

set -e

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  BoneAgeWeb - AI 骨龄评估系统"
echo "  一键启动脚本 (Unix)"
echo "================================================"
echo ""

# --- 后端启动 ---
echo "[后端] 正在启动 FastAPI 后端服务 (端口 8000)..."
(
  cd "$SCRIPT_DIR/backend"
  if [ -f "venv/bin/activate" ]; then
    echo "[后端] 检测到虚拟环境 venv，正在激活..."
    source venv/bin/activate
  elif [ -f ".venv/bin/activate" ]; then
    echo "[后端] 检测到虚拟环境 .venv，正在激活..."
    source .venv/bin/activate
  else
    echo "[后端] 未检测到虚拟环境，使用系统 Python..."
  fi
  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) &
BACKEND_PID=$!
echo "[后端] 进程 PID: $BACKEND_PID"

# 等待后端初始化
echo "[后端] 等待 3 秒让后端完成初始化..."
sleep 3

# --- 前端启动 ---
echo "[前端] 正在启动 Vite 前端开发服务器 (端口 5173)..."
(
  cd "$SCRIPT_DIR/frontend"
  npm run dev
) &
FRONTEND_PID=$!
echo "[前端] 进程 PID: $FRONTEND_PID"

echo ""
echo "================================================"
echo "  服务已启动！"
echo "  后端地址: http://127.0.0.1:8000"
echo "  前端地址: http://127.0.0.1:5173"
echo "  API 文档: http://127.0.0.1:8000/docs"
echo "================================================"
echo ""
echo "  按 Ctrl+C 以停止所有服务..."

# 捕获退出信号，并停止所有子进程
trap "echo ''; echo '[退出] 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 等待所有子进程结束
wait $BACKEND_PID $FRONTEND_PID
