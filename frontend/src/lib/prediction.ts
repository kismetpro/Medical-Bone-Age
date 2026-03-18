import { API_BASE } from '../config';

/**
 * 提交骨龄预测请求
 */
export async function submitPredictionRequest({
  file,
  gender,
  currentHeight,
  realAge,
  targetUserId,
  preprocessingEnabled = false,
  brightness = 0,
  contrast = 1,
  headers = {},
}: {
  file: File;
  gender: string;
  currentHeight?: string | number;
  realAge?: string | number;
  targetUserId?: number;
  preprocessingEnabled?: boolean;
  brightness?: number;
  contrast?: number;
  headers?: Record<string, string>;
}) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('gender', gender);

  if (currentHeight !== undefined && currentHeight !== '') {
    formData.append('height', String(currentHeight));
  }
  if (realAge !== undefined && realAge !== '') {
    formData.append('real_age_years', String(realAge));
  }
  if (targetUserId !== undefined) {
    formData.append('target_user_id', String(targetUserId));
  }

  // 新增图像预处理参数
  formData.append('preprocessing_enabled', String(preprocessingEnabled));
  formData.append('brightness', String(brightness));
  formData.append('contrast', String(contrast));

  const response = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    body: formData,
    headers: {
      ...headers,
    },
    // 注意：不要手动设置 Content-Type，让浏览器自动处理以包含 boundary
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || '预测请求失败');
  }

  return response.json();
}

/**
 * 规范化预测结果，确保字段一致性
 */
export function normalizePredictionResult<T>(data: any, inputRealAge?: string | number): T {
  const result = { ...data };

  // 如果后端没返回 real_age_years 但输入中有，则进行补充
  if (result.real_age_years === undefined || result.real_age_years === null) {
      if (inputRealAge !== undefined && inputRealAge !== '') {
          result.real_age_years = Number(inputRealAge);
      }
  }

  // 确保 ID 和时间戳存在（即使后端在某些流程中未直接返回）
  if (!result.timestamp) {
    result.timestamp = Date.now();
  }

  return result as T;
}
