import { AuthCookie } from './cookieManager';
import { API_BASE } from '../config';

/**
 * 构建认证头
 */
export const buildAuthHeaders = (json = false) => {
    const token = localStorage.getItem('boneage_token') || AuthCookie.getToken();
    const headers: Record<string, string> = {};
    if (json) headers['Content-Type'] = 'application/json';
    if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
};

/**
 * 翻译错误消息
 */
const translateErrorMessage = (englishMessage: string): string => {
    const errorMap: Record<string, string> = {
        'Username already exists': '用户名已存在',
        'Password must include upper/lower letters and digits, minimum 8 chars': '密码必须包含大小写字母和数字，至少8个字符',
        'Username format invalid': '用户名格式无效，仅支持3-64位字母/数字/_.-',
        'Doctor self-register is disabled': '医生自注册已关闭，请联系系统管理员',
        'Access denied': '医生注册密钥错误',
        'Invalid username or password': '用户名或密码错误',
        'Not authenticated': '未认证，请先登录',
        'Session expired or invalid': '会话已过期或无效，请重新登录',
        'You cannot change your own role': '不能修改自己的角色',
        'User not found': '用户不存在',
        'At least one super admin must remain': '至少需要保留一个超级管理员',
        'Too many requests': '请求过多，请稍后再试',
        'Register success': '注册成功',
        'Login success': '登录成功'
    };
    
    return errorMap[englishMessage] || englishMessage;
};

/**
 * 解析错误消息
 */
export const readErrorMessage = async (response: Response) => {
    const payload = await response.json().catch(() => ({}));
    const englishMessage = typeof payload.detail === 'string' ? payload.detail : '请求失败';
    return translateErrorMessage(englishMessage);
};

/**
 * 小关节检测API（使用joint-grading接口）
 */
export const detectJoints = async (file: File, gender: string, realAge: string, usePreprocessing: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('gender', gender);

    const response = await fetch(`${API_BASE}/joint-grading`, {
        method: 'POST',
        headers: buildAuthHeaders(),
        body: formData,
    });

    if (!response.ok) {
        throw new Error(await readErrorMessage(response));
    }

    const data = await response.json();
    
    // 转换返回格式为前端需要的格式
    const jointsData = data.joint_detect_13?.joints;
    const jointsArray = jointsData && typeof jointsData === 'object' ? Object.entries(jointsData) : [];
    
    return {
        joints: jointsArray.map(([id, joint]: [string, any]) => ({
            id,
            name: id,
            bbox: joint.bbox,
            grade: data.joint_grades?.[id]?.grade_raw,
            score: joint.confidence || 1.0,
            status: 'ok'
        })),
        joint_grades: data.joint_grades,
        joint_semantic_13: data.joint_semantic_13,
        joint_rus_total_score: data.joint_rus_total_score,
        joint_rus_details: data.joint_rus_details
    };
};

/**
 * 公式法骨龄预测API
 */
export const predictBoneAgeByFormula = async (file: File, gender: string, realAge: string, joints: any[]) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('gender', gender);
    formData.append('real_age', realAge);
    formData.append('joints', JSON.stringify(joints));

    const response = await fetch(`${API_BASE}/formula-calculation`, {
        method: 'POST',
        headers: buildAuthHeaders(),
        body: formData,
    });

    if (!response.ok) {
        throw new Error(await readErrorMessage(response));
    }

    return response.json();
};