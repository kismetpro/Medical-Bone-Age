import { API_BASE } from '../config';

export const ANOMALY_ALERT_THRESHOLD = 0.45;
export const FOREIGN_OBJECT_MESSAGE =
  '\u68c0\u6d4b\u5230\u5f02\u7269\uff0c\u53ef\u80fd\u5f71\u54cd\u9aa8\u9f84\u5224\u65ad\uff0c\u8bf7\u7ed3\u5408\u539f\u59cb\u5f71\u50cf\u590d\u6838';

const FOREIGN_OBJECT_TYPES = new Set(['foreignbody', 'metal']);

export type AnomalyItem = {
  type: string;
  score: number;
  coord: number[];
};

export type ForeignObjectDetection = {
  detected: boolean;
  count: number;
  threshold: number;
  message: string | null;
  items: AnomalyItem[];
};

export function buildForeignObjectDetection(anomalies?: AnomalyItem[] | null): ForeignObjectDetection {
  const items = (Array.isArray(anomalies) ? anomalies : []).filter((item) => {
    if (!item || typeof item.type !== 'string' || !Number.isFinite(item.score)) {
      return false;
    }
    return item.score >= ANOMALY_ALERT_THRESHOLD && FOREIGN_OBJECT_TYPES.has(item.type.toLowerCase());
  });

  return {
    detected: items.length > 0,
    count: items.length,
    threshold: ANOMALY_ALERT_THRESHOLD,
    message: items.length > 0 ? FOREIGN_OBJECT_MESSAGE : null,
    items,
  };
}

export function resolveForeignObjectDetection(
  source?: {
    anomalies?: AnomalyItem[] | null;
    foreign_object_detection?: Partial<ForeignObjectDetection> | null;
  } | null,
): ForeignObjectDetection {
  const fallback = buildForeignObjectDetection(source?.anomalies);
  const raw = source?.foreign_object_detection;

  if (!raw || typeof raw !== 'object') {
    return fallback;
  }

  const items = buildForeignObjectDetection(Array.isArray(raw.items) ? (raw.items as AnomalyItem[]) : source?.anomalies).items;

  return {
    detected: items.length > 0,
    count: items.length,
    threshold: typeof raw.threshold === 'number' ? raw.threshold : fallback.threshold,
    message: items.length > 0 ? (typeof raw.message === 'string' && raw.message.trim() ? raw.message : FOREIGN_OBJECT_MESSAGE) : null,
    items,
  };
}

export function getHighConfidenceFractures(anomalies?: AnomalyItem[] | null): AnomalyItem[] {
  return (Array.isArray(anomalies) ? anomalies : []).filter((item) => {
    if (!item || typeof item.type !== 'string' || !Number.isFinite(item.score)) {
      return false;
    }
    return item.score >= ANOMALY_ALERT_THRESHOLD && item.type.toLowerCase().includes('fracture');
  });
}

export function getAnomalyDisplayName(type: string): string {
  const normalized = type.toLowerCase();

  if (normalized === 'foreignbody') return '\u5f02\u7269';
  if (normalized === 'metal') return '\u91d1\u5c5e\u5f02\u7269';
  if (normalized === 'fracture') return '\u9aa8\u6298';
  if (normalized === 'boneanomaly') return '\u9aa8\u5f02\u5e38';
  if (normalized === 'bonelesion') return '\u9aa8\u75c5\u7076';
  if (normalized === 'periostealreaction') return '\u9aa8\u819c\u53cd\u5e94';
  if (normalized === 'pronatorsign') return '\u65cb\u524d\u808c\u5f81';
  if (normalized === 'softtissue') return '\u8f6f\u7ec4\u7ec7\u5f02\u5e38';
  if (normalized === 'text') return '\u6587\u5b57\u4f2a\u5f71';
  return type || '\u672a\u77e5\u5f02\u5e38';
}

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
  quickMode = false,
  minimalMode = false,
  useDpv3 = true,
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
  quickMode?: boolean;
  minimalMode?: boolean;
  useDpv3?: boolean;
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
  formData.append('quick_mode', String(quickMode));
  formData.append('minimal_mode', String(minimalMode));
  formData.append('use_dpv3', String(useDpv3));

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

  if (!result.foreign_object_detection && Array.isArray(result.anomalies)) {
    result.foreign_object_detection = buildForeignObjectDetection(result.anomalies);
  }

  return result as T;
}
