import { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE } from '../../../config';
import { buildAuthHeaders, readErrorMessage } from '../../../lib/api';
import { normalizePredictionResult } from '../../../lib/prediction';
import { useTimedMessage } from '../../../hooks/useTimedMessage';
import type { BoneAgePoint, BoneAgeTrend, PredictionResult, TrendDataPoint } from '../types';

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export interface UseBoneAgeHistoryReturn {
  history: PredictionResult[];
  boneAgePoints: BoneAgePoint[];
  trend: BoneAgeTrend | null;
  trendData: TrendDataPoint[];
  pointTime: string;
  pointBoneAge: string;
  pointChronAge: string;
  pointNote: string;
  pointLoading: boolean;
  historyMessage: { type: 'success' | 'error'; text: string } | null;
  editingPrediction: PredictionResult | null;
  editingPredictionValue: string;
  pendingDeletePointId: number | null;
  setPointTime: (value: string) => void;
  setPointBoneAge: (value: string) => void;
  setPointChronAge: (value: string) => void;
  setPointNote: (value: string) => void;
  setEditingPredictionValue: (value: string) => void;
  addPoint: () => Promise<void>;
  openUpdatePrediction: (item: PredictionResult) => void;
  confirmUpdatePrediction: () => Promise<void>;
  cancelUpdatePrediction: () => void;
  openDeletePoint: (pointId: number) => void;
  confirmDeletePoint: () => Promise<void>;
  cancelDeletePoint: () => void;
  refreshAll: () => Promise<void>;
}

export function useBoneAgeHistory(): UseBoneAgeHistoryReturn {
  const [history, setHistory] = useState<PredictionResult[]>([]);
  const [boneAgePoints, setBoneAgePoints] = useState<BoneAgePoint[]>([]);
  const [trend, setTrend] = useState<BoneAgeTrend | null>(null);
  const [pointTime, setPointTime] = useState('');
  const [pointBoneAge, setPointBoneAge] = useState('');
  const [pointChronAge, setPointChronAge] = useState('');
  const [pointNote, setPointNote] = useState('');
  const [pointLoading, setPointLoading] = useState(false);
  const [editingPrediction, setEditingPrediction] = useState<PredictionResult | null>(null);
  const [editingPredictionValue, setEditingPredictionValue] = useState('');
  const [pendingDeletePointId, setPendingDeletePointId] = useState<number | null>(null);
  const { message: historyMessage, showMessage } = useTimedMessage();

  const fetchPredictionHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/predictions`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = await response.json();
      const items = Array.isArray(data.items)
        ? data.items.map((item: Record<string, unknown>) =>
            normalizePredictionResult<PredictionResult>(item),
          )
        : [];
      setHistory(items);
    } catch (error) {
      showMessage('error', getErrorMessage(error, '获取历史记录失败'));
    }
  }, [showMessage]);

  const fetchBoneAgePoints = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/bone-age-points`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = await response.json();
      setBoneAgePoints(Array.isArray(data.items) ? (data.items as BoneAgePoint[]) : []);
    } catch (error) {
      showMessage('error', getErrorMessage(error, '获取散点数据失败'));
    }
  }, [showMessage]);

  const fetchBoneAgeTrend = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/bone-age-trend`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      const data = await response.json();
      setTrend(data as BoneAgeTrend);
    } catch (error) {
      showMessage('error', getErrorMessage(error, '获取回归趋势失败'));
    }
  }, [showMessage]);

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchPredictionHistory(), fetchBoneAgePoints(), fetchBoneAgeTrend()]);
  }, [fetchBoneAgePoints, fetchBoneAgeTrend, fetchPredictionHistory]);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const addPoint = async () => {
    const boneAge = Number(pointBoneAge);
    if (!Number.isFinite(boneAge) || boneAge <= 0) {
      showMessage('error', '请输入有效的骨龄散点值');
      return;
    }

    const pointTimestamp = pointTime ? new Date(pointTime).getTime() : Date.now();
    if (!Number.isFinite(pointTimestamp)) {
      showMessage('error', '日期格式无效');
      return;
    }

    setPointLoading(true);
    try {
      const response = await fetch(`${API_BASE}/bone-age-points`, {
        method: 'POST',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify({
          point_time: pointTimestamp,
          bone_age_years: boneAge,
          chronological_age_years: pointChronAge ? Number(pointChronAge) : undefined,
          note: pointNote,
        }),
      });

      const data = (await response.json().catch(() => ({}))) as { detail?: string };
      if (!response.ok) {
        throw new Error(data.detail || '新增散点失败');
      }

      setPointTime('');
      setPointBoneAge('');
      setPointChronAge('');
      setPointNote('');
      showMessage('success', '骨龄散点已新增');
      await Promise.all([fetchBoneAgePoints(), fetchBoneAgeTrend()]);
    } catch (error) {
      showMessage('error', getErrorMessage(error, '新增散点失败'));
    } finally {
      setPointLoading(false);
    }
  };

  const openUpdatePrediction = (item: PredictionResult) => {
    setEditingPrediction(item);
    setEditingPredictionValue(item.predicted_age_years.toString());
  };

  const cancelUpdatePrediction = () => {
    setEditingPrediction(null);
    setEditingPredictionValue('');
  };

  const confirmUpdatePrediction = async () => {
    if (!editingPrediction) {
      return;
    }

    const parsedAge = Number(editingPredictionValue);
    if (!Number.isFinite(parsedAge) || parsedAge <= 0) {
      showMessage('error', '请输入有效骨龄数值');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/predictions/${editingPrediction.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: buildAuthHeaders(true),
        body: JSON.stringify({ predicted_age_years: parsedAge }),
      });

      await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }

      cancelUpdatePrediction();
      showMessage('success', '预测骨龄已更新');
      await refreshAll();
    } catch (error) {
      showMessage('error', getErrorMessage(error, '修改失败'));
    }
  };

  const openDeletePoint = (pointId: number) => {
    setPendingDeletePointId(pointId);
  };

  const cancelDeletePoint = () => {
    setPendingDeletePointId(null);
  };

  const confirmDeletePoint = async () => {
    if (pendingDeletePointId === null) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/bone-age-points/${pendingDeletePointId}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: buildAuthHeaders(),
      });

      const data = (await response.json().catch(() => ({}))) as { detail?: string };
      if (!response.ok) {
        throw new Error(data.detail || '删除失败');
      }

      cancelDeletePoint();
      showMessage('success', '骨龄散点已删除');
      await Promise.all([fetchBoneAgePoints(), fetchBoneAgeTrend()]);
    } catch (error) {
      showMessage('error', getErrorMessage(error, '删除失败'));
    }
  };

  const trendData = useMemo<TrendDataPoint[]>(() => {
    return boneAgePoints.map((point) => {
      let trendY: number | undefined;
      if (trend?.enough && trend.coefficients) {
        const baseTime = boneAgePoints.length > 0 ? boneAgePoints[0].point_time : point.point_time;
        const timeYears = (point.point_time - baseTime) / (1000 * 60 * 60 * 24 * 365.25);
        const chronologicalAge = point.chronological_age_years ?? timeYears;
        trendY =
          trend.coefficients.intercept +
          trend.coefficients.time * timeYears +
          trend.coefficients.chronological_age * chronologicalAge;
      }

      return {
        ...point,
        trendY,
        dateLabel: new Date(point.point_time).toLocaleDateString(),
      };
    });
  }, [boneAgePoints, trend]);

  return {
    history,
    boneAgePoints,
    trend,
    trendData,
    pointTime,
    pointBoneAge,
    pointChronAge,
    pointNote,
    pointLoading,
    historyMessage,
    editingPrediction,
    editingPredictionValue,
    pendingDeletePointId,
    setPointTime,
    setPointBoneAge,
    setPointChronAge,
    setPointNote,
    setEditingPredictionValue,
    addPoint,
    openUpdatePrediction,
    confirmUpdatePrediction,
    cancelUpdatePrediction,
    openDeletePoint,
    confirmDeletePoint,
    cancelDeletePoint,
    refreshAll,
  };
}
