import React from 'react';
import { Plus, Trash2, History } from 'lucide-react';
import { ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis, Tooltip, Scatter, Line } from 'recharts';
import katex from 'katex';
import styles from '../UserDashboard.module.css';
import type { BoneAgePoint, BoneAgeTrend, PredictionResult } from '../types';

interface HistoryTabProps {
    pointTime: string;
    setPointTime: (time: string) => void;
    pointBoneAge: string;
    setPointBoneAge: (age: string) => void;
    pointChronAge: string;
    setPointChronAge: (age: string) => void;
    pointNote: string;
    setPointNote: (note: string) => void;
    addPoint: () => void;
    pointLoading: boolean;
    trendData: any[];
    trend: BoneAgeTrend | null;
    boneAgePoints: BoneAgePoint[];
    deletePoint: (id: number) => void;
    history: PredictionResult[];
    restoreHistoryItem: (item: Partial<PredictionResult>) => void;
    setActiveTab: (tab: 'predict' | 'history' | 'community') => void;
    updatePrediction: (item: PredictionResult) => void;
}

const HistoryTab: React.FC<HistoryTabProps> = ({
    pointTime, setPointTime, pointBoneAge, setPointBoneAge,
    pointChronAge, setPointChronAge, pointNote, setPointNote,
    addPoint, pointLoading, trendData, trend, boneAgePoints, deletePoint,
    history, restoreHistoryItem, setActiveTab, updatePrediction
}) => {
    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.resultsCard} style={{ width: '100%', gridColumn: '1 / -1' }}>
                <h3 style={{ margin: '0 0 1rem 0' }}>骨龄散点趋势分析</h3>
                <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: '1rem', marginBottom: '1rem', background: '#fff' }}>
                    <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '2fr 1fr 1fr 2fr auto' }}>
                        <input type="datetime-local" value={pointTime} onChange={(e) => setPointTime(e.target.value)} />
                        <input type="number" placeholder="骨龄(岁)" value={pointBoneAge} onChange={(e) => setPointBoneAge(e.target.value)} step="0.1" />
                        <input type="number" placeholder="生活年龄(岁)" value={pointChronAge} onChange={(e) => setPointChronAge(e.target.value)} step="0.1" />
                        <input type="text" placeholder="备注(可选)" value={pointNote} onChange={(e) => setPointNote(e.target.value)} />
                        <button className={styles.btnPrimary} onClick={addPoint} disabled={pointLoading}>
                            <Plus size={14} /> 添加
                        </button>
                    </div>
                    <div style={{ height: 280, marginTop: '1rem' }}>
                        <ResponsiveContainer>
                            <ComposedChart data={trendData} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="point_time" type="number" tickFormatter={(v) => new Date(v).toLocaleDateString()} domain={['dataMin', 'dataMax']} />
                                <YAxis type="number" dataKey="bone_age_years" name="骨龄(岁)" />
                                <Tooltip labelFormatter={(v) => new Date(Number(v)).toLocaleString()} formatter={(value: any, name: any) => [Number(value).toFixed(2), name === 'bone_age_years' ? '骨龄' : '回归曲线']} />
                                <Scatter name="骨龄散点" dataKey="bone_age_years" fill="#3b82f6" />
                                <Line type="monotone" dataKey="trendY" stroke="#ef4444" dot={false} name="回归曲线" />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>
                    <div style={{ marginTop: '0.75rem', color: '#475569', fontSize: '0.9rem' }}>
                        <div>
                            回归方程（LaTeX）：
                            <span
                                dangerouslySetInnerHTML={{
                                    __html: (() => {
                                        const latex = trend?.latex || '\\hat{BA}=\\beta_0+\\beta_1 t+\\beta_2 a';
                                        try {
                                            return katex.renderToString(latex, { throwOnError: false });
                                        } catch (e) {
                                            return `<code>${latex}</code>`;
                                        }
                                    })(),
                                }}
                            />
                        </div>
                        {trend?.r2 !== undefined && <div>R² = {trend.r2.toFixed(4)}</div>}
                    </div>
                    <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
                        {boneAgePoints.map((p) => (
                            <div key={p.id} style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: '0.65rem', background: '#f8fafc' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                                    <strong>{p.bone_age_years.toFixed(1)} 岁</strong>
                                    <button onClick={() => deletePoint(p.id)} style={{ border: 'none', background: 'transparent', color: '#ef4444', cursor: 'pointer' }}>
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                                <div style={{ fontSize: '0.82rem', color: '#64748b' }}>{new Date(p.point_time).toLocaleString()}</div>
                                {p.note && <div style={{ fontSize: '0.82rem', color: '#64748b' }}>{p.note}</div>}
                            </div>
                        ))}
                    </div>
                </div>

                <h3 style={{ margin: '0 0 1rem 0' }}>全部过往预测记录（支持编辑）</h3>
                {history.length === 0 ? <p>暂无过往的评估历史。</p> : (
                    <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                        {history.map(item => (
                            <div key={item.id} style={{ padding: '1.5rem', border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                    <span style={{ color: '#64748b', fontSize: '0.9rem' }}>{new Date(item.timestamp).toLocaleDateString()}</span>
                                    <span className={item.gender === 'male' ? styles.tagMale : styles.tagFemale}>{item.gender === 'male' ? '男' : '女'}</span>
                                </div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '1rem' }}>
                                    {item.predicted_age_years.toFixed(1)} <span style={{ fontSize: '1rem', color: '#64748b', fontWeight: 500 }}>岁</span>
                                </div>
                                <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: '1fr 1fr' }}>
                                    <button className={styles.btnPrimary} onClick={() => { restoreHistoryItem(item); setActiveTab('predict'); }} style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #3b82f6', background: 'transparent', color: '#3b82f6', cursor: 'pointer' }}>查看详情</button>
                                    <button className={styles.btnPrimary} onClick={() => updatePrediction(item)} style={{ width: '100%', padding: '0.5rem', borderRadius: '6px' }}>编辑预测值</button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default HistoryTab;
