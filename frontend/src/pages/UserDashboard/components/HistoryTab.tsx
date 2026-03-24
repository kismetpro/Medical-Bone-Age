import { Plus, Trash2 } from 'lucide-react';
import katex from 'katex';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import OverlayDialog from '../../../components/dialog/OverlayDialog';
import styles from '../UserDashboard.module.css';
import type { UserDashboardTab } from '../tabsConfig';
import type { BoneAgePoint, BoneAgeTrend, PredictionResult, TrendDataPoint } from '../types';

interface HistoryTabProps {
  pointTime: string;
  setPointTime: (time: string) => void;
  pointBoneAge: string;
  setPointBoneAge: (age: string) => void;
  pointChronAge: string;
  setPointChronAge: (age: string) => void;
  pointNote: string;
  setPointNote: (note: string) => void;
  addPoint: () => Promise<void>;
  pointLoading: boolean;
  trendData: TrendDataPoint[];
  trend: BoneAgeTrend | null;
  boneAgePoints: BoneAgePoint[];
  history: PredictionResult[];
  restoreHistoryItem: (item: Partial<PredictionResult>) => Promise<void>;
  setActiveTab: (tab: UserDashboardTab) => void;
  openUpdatePrediction: (item: PredictionResult) => void;
  historyMessage: { type: 'success' | 'error'; text: string } | null;
  editingPrediction: PredictionResult | null;
  editingPredictionValue: string;
  setEditingPredictionValue: (value: string) => void;
  confirmUpdatePrediction: () => Promise<void>;
  cancelUpdatePrediction: () => void;
  openDeletePoint: (id: number) => void;
  pendingDeletePointId: number | null;
  confirmDeletePoint: () => Promise<void>;
  cancelDeletePoint: () => void;
}

export default function HistoryTab({
  pointTime,
  setPointTime,
  pointBoneAge,
  setPointBoneAge,
  pointChronAge,
  setPointChronAge,
  pointNote,
  setPointNote,
  addPoint,
  pointLoading,
  trendData,
  trend,
  boneAgePoints,
  history,
  restoreHistoryItem,
  setActiveTab,
  openUpdatePrediction,
  historyMessage,
  editingPrediction,
  editingPredictionValue,
  setEditingPredictionValue,
  confirmUpdatePrediction,
  cancelUpdatePrediction,
  openDeletePoint,
  pendingDeletePointId,
  confirmDeletePoint,
  cancelDeletePoint,
}: HistoryTabProps) {
  const pendingDeletePoint = boneAgePoints.find((point) => point.id === pendingDeletePointId) ?? null;

  return (
    <div className={styles.workspaceGrid}>
      <div className={styles.resultsCard} style={{ width: '100%', gridColumn: '1 / -1' }}>
        {historyMessage ? (
          <div
            className={`${styles.historyNotice} ${
              historyMessage.type === 'success' ? styles.historyNoticeSuccess : styles.historyNoticeError
            }`}
          >
            {historyMessage.text}
          </div>
        ) : null}

        <h3 style={{ margin: '0 0 1rem 0' }}>骨龄散点趋势分析</h3>
        <div className={styles.historyFormCard}>
          <div className={styles.historyFormGrid}>
            <input
              className={styles.historyInput}
              type="datetime-local"
              value={pointTime}
              onChange={(event) => setPointTime(event.target.value)}
            />
            <input
              className={styles.historyInput}
              type="number"
              placeholder="骨龄(岁)"
              value={pointBoneAge}
              onChange={(event) => setPointBoneAge(event.target.value)}
              step="0.1"
            />
            <input
              className={styles.historyInput}
              type="number"
              placeholder="生活年龄(岁)"
              value={pointChronAge}
              onChange={(event) => setPointChronAge(event.target.value)}
              step="0.1"
            />
            <input
              className={styles.historyInput}
              type="text"
              placeholder="备注(可选)"
              value={pointNote}
              onChange={(event) => setPointNote(event.target.value)}
            />
            <button type="button" className={styles.btnPrimary} onClick={() => void addPoint()} disabled={pointLoading}>
              <Plus size={14} />
              添加
            </button>
          </div>

          <div className={styles.historyChartShell}>
            <ResponsiveContainer>
              <ComposedChart data={trendData} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="point_time"
                  type="number"
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  domain={['dataMin', 'dataMax']}
                />
                <YAxis type="number" dataKey="bone_age_years" name="骨龄(岁)" />
                <Tooltip
                  labelFormatter={(value) => new Date(Number(value)).toLocaleString()}
                  formatter={(value: number | string, name: string) => [
                    Number(value).toFixed(2),
                    name === 'bone_age_years' ? '骨龄' : '回归曲线',
                  ]}
                />
                <Scatter name="骨龄散点" dataKey="bone_age_years" fill="#3b82f6" />
                <Line type="monotone" dataKey="trendY" stroke="#ef4444" dot={false} name="回归曲线" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.historyLatex}>
            <div>
              回归方程（LaTeX）：
              <span
                dangerouslySetInnerHTML={{
                  __html: (() => {
                    const latex = trend?.latex || '\\hat{BA}=\\beta_0+\\beta_1 t+\\beta_2 a';
                    try {
                      return katex.renderToString(latex, { throwOnError: false });
                    } catch {
                      return `<code>${latex}</code>`;
                    }
                  })(),
                }}
              />
            </div>
            {trend?.r2 !== undefined ? <div>R² = {trend.r2.toFixed(4)}</div> : null}
          </div>

          <div className={styles.historyCardsGrid}>
            {boneAgePoints.length > 0 ? (
              boneAgePoints.map((point) => (
                <div key={point.id} className={styles.historyPointCard}>
                  <div className={styles.historyCardHeader}>
                    <strong>{point.bone_age_years.toFixed(1)} 岁</strong>
                    <button
                      type="button"
                      className={styles.historyDeleteBtn}
                      onClick={() => openDeletePoint(point.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div>{new Date(point.point_time).toLocaleString()}</div>
                  {point.note ? <div>{point.note}</div> : null}
                </div>
              ))
            ) : (
              <div className={styles.historyEmptyState}>还没有骨龄散点，先添加一条观察点吧。</div>
            )}
          </div>
        </div>

        <h3 style={{ margin: '1.4rem 0 1rem 0' }}>全部过往预测记录</h3>
        {history.length > 0 ? (
          <div className={styles.historyCardsGrid}>
            {history.map((item) => (
              <div key={item.id} className={styles.historyRecordCard}>
                <div className={styles.historyCardHeader}>
                  <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                  <span className={item.gender === 'male' ? styles.tagMale : styles.tagFemale}>
                    {item.gender === 'male' ? '男' : '女'}
                  </span>
                </div>
                <div className={styles.historyRecordScore}>
                  {item.predicted_age_years.toFixed(1)} <span>岁</span>
                </div>
                <div className={styles.historyRecordActions}>
                  <button
                    type="button"
                    className={styles.historySecondaryAction}
                    onClick={() => {
                      void restoreHistoryItem(item);
                      setActiveTab('predict');
                    }}
                  >
                    查看详情
                  </button>
                  <button type="button" className={styles.btnPrimary} onClick={() => openUpdatePrediction(item)}>
                    编辑预测值
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.historyEmptyState}>暂无过往的评估历史。</div>
        )}
      </div>

      <OverlayDialog
        open={editingPrediction !== null}
        title="编辑预测骨龄"
        description="请输入新的预测骨龄（单位：岁），更新后会同步刷新历史记录和趋势图。"
        confirmText="保存修改"
        cancelText="取消"
        onCancel={cancelUpdatePrediction}
        onConfirm={() => void confirmUpdatePrediction()}
      >
        <input
          className={styles.historyInput}
          type="number"
          step="0.1"
          value={editingPredictionValue}
          onChange={(event) => setEditingPredictionValue(event.target.value)}
        />
      </OverlayDialog>

      <OverlayDialog
        open={pendingDeletePoint !== null}
        title="删除骨龄散点"
        description={
          pendingDeletePoint
            ? `确认删除 ${new Date(pendingDeletePoint.point_time).toLocaleDateString()} 的骨龄点位吗？`
            : '确认删除该骨龄点位吗？'
        }
        confirmText="确认删除"
        cancelText="取消"
        tone="danger"
        onCancel={cancelDeletePoint}
        onConfirm={() => void confirmDeletePoint()}
      />
    </div>
  );
}
