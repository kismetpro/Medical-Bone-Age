#!/bin/bash

# ==============================================================================
#  🏥 Medical Bone Age - AI 骨龄智能评估系统
#  Linux 专属启动脚本 (含全套环境检查与自动修复)
# ==============================================================================

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "   ${BOLD}${BLUE}🏥 Medical Bone Age Assessment System (Linux Version)${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# --- 检查 Python 环境 ---
echo -e "\n${BOLD}${YELLOW}[1/3] 检查并配置后端环境...${NC}"

if [ ! -d "backend" ]; then
    echo -e "${RED}[错误] 找不到 backend 目录！${NC}"
    exit 1
fi

cd backend

# 查找虚拟环境
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
else
    echo -e "${YELLOW}[提示] 未发现虚拟环境，正在创建 .venv...${NC}"
    python3 -m venv .venv
    VENV_PATH=".venv"
fi

echo -e "${GREEN}[配置] 激活虚拟环境 ($VENV_PATH)...${NC}"
source "$VENV_PATH/bin/activate"

# 检查/安装依赖 (这是解决之前的 onnxruntime 问题的关键)
echo -e "${GREEN}[配置] 正在同步后端依赖 (requirements.txt)...${NC}"
pip install -r requirements.txt | grep -v 'already satisfied' || true

# --- 检查 Node.js 环境 ---
echo -e "\n${BOLD}${YELLOW}[2/3] 检查并配置前端环境...${NC}"

cd "$PROJECT_ROOT/frontend"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[提示] 找不到 node_modules，正在安装前端依赖...${NC}"
    npm install
else
    echo -e "${GREEN}[配置] 前端依赖已就绪。${NC}"
fi

# --- 启动服务 ---
echo -e "\n${BOLD}${YELLOW}[3/3] 正式启动服务...${NC}"

# 启动后端
cd "$PROJECT_ROOT/backend"
echo -e "${GREEN}[后端] 正在启动 FastAPI (端口 8000)...${NC}"
python3 entry_point.py > backend.log 2>&1 &
BACKEND_PID=$!

# 启动前端
cd "$PROJECT_ROOT/frontend"
echo -e "${GREEN}[前端] 正在启动 Vite 开发服务器 (端口 5173)...${NC}"
npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &
FRONTEND_PID=$!

# 记录 PID
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid"

# 等待一会看进程是否还在
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}[错误] 后端启动失败，请检查 backend.log${NC}"
    kill $FRONTEND_PID 2>/dev/null
    exit 1
fi

if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}[错误] 前端启动失败，请检查 frontend.log${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "\n${BOLD}${GREEN}==============================================================================${NC}"
echo -e "   🚀 ${BOLD}系统已成功启动！${NC}"
echo -e "   🔗 前端访问: ${CYAN}http://localhost:5173${NC}"
echo -e "   🔗 后端接口: ${CYAN}http://localhost:8000${NC}"
echo -e "   🔗 API 文档: ${CYAN}http://localhost:8000/docs${NC}"
echo -e "   📝 日志记录: ${BLUE}backend.log${NC} / ${BLUE}frontend.log${NC}"
echo -e "   🛑 停止系统: ${YELLOW}请按键盘 Ctrl+C${NC}"
echo -e "${BOLD}${GREEN}==============================================================================${NC}\n"

# 优雅退出处理
cleanup() {
    echo -e "\n${YELLOW}[停止] 正在关闭所有服务...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    rm -f "$PROJECT_ROOT/.backend.pid" "$PROJECT_ROOT/.frontend.pid"
    echo -e "${GREEN}[停止] 所有进程已退出。再见！${NC}"
    exit
}

trap cleanup SIGINT SIGTERM

# 保持脚本运行
wait
