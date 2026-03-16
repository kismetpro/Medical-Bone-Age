import { API_BASE } from '../config';

/**
 * 构建认证头
 */
export const buildAuthHeaders = (json = false) => {
    const token = localStorage.getItem('boneage_token');
    const headers: Record<string, string> = {};
    if (json) headers['Content-Type'] = 'application/json';
    if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
};

/**
 * 解析错误消息
 */
export const readErrorMessage = async (response: Response) => {
    const payload = await response.json().catch(() => ({}));
    return typeof payload.detail === 'string' ? payload.detail : '请求失败';
};
