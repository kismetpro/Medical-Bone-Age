/**
 * 集中管理 API 基础路径
 * 开发环境下通过 Vite Proxy (/api) 转发到后端
 * 生产环境下通过 Nginx (/api) 转发到后端
 */
export const API_BASE = import.meta.env.VITE_API_BASE || '/api';
