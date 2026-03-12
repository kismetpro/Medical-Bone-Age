# 前后端分离部署指南

本项目已实现前后端分离，可以部署在两台独立的服务器或不同的域名下。

## 后端部署 (API Server)

后端使用 FastAPI (Python 3.9+) 构建。

1. **环境准备**：
   - 安装 Python 环境。
   - `pip install -r requirements.txt`。

2. **环境变量配置**：
   - 在 `backend/` 目录下创建 `.env` 文件（参考 `.env.example`）。
   - **核心配置 `ALLOWED_ORIGINS`**：必须包含前端部署的域名。例如：
     ```env
     ALLOWED_ORIGINS=https://your-frontend-domain.com
     ```

3. **模型文件**：
   - 确保 `app/models/` 目录下放置了必要的 `.pth` 模型文件。

4. **运行**：
   - 使用 `uvicorn app.main:app --host 0.0.0.0 --port 8000` 启动。

## 前端部署 (Vite + React)

前端使用 Vite 构建，部署前需要生成静态文件。

1. **环境准备**：
   - 安装 Node.js。
   - `npm install`。

2. **环境变量配置**：
   - 在 `frontend/` 目录下创建 `.env` 文件（参考 `.env.example`）。
   - **核心配置 `VITE_API_BASE`**：指向后端的 API 基础路径。
     ```env
     VITE_API_BASE=https://your-api-domain.com
     ```

3. **构建生产版本**：
   - 运行 `npm run build`。
   - 这将生成 `dist/` 文件夹。

4. **服务器部署**：
   - 将 `dist/` 文件夹中的内容上传到 Web 服务器（如 Nginx, Apache, Vercel 等）。

## 跨域说明

- 后端通过 `CORSMiddleware` 处理跨域。
- 前端在向后端发送请求时，如果跨域名，必须确保后端 `.env` 中的 `ALLOWED_ORIGINS` 包含前端所在的 URL（包括协议和端口，如 `https://boneage.example.com`）。
- 由于使用了 HttpOnly Cookie，如果前后端部署在不同的二级域名下（例如 `api.test.com` 和 `app.test.com`），请确保 `AUTH_COOKIE_SAMESITE=lax`。

---
*注：本项目默认使用 SQLite 数据库，数据文件位于 `app/data/` 目录下，部署时请确保持久化该目录。*
