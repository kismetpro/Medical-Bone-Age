import React, { useState, useMemo } from 'react';
import { Calculator, Info, CheckCircle, AlertCircle } from 'lucide-react';
import { ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar, Cell } from 'recharts';
import styles from '../UserDashboard.module.css';
import { API_BASE } from '../../../config';
import { buildAuthHeaders, readErrorMessage } from '../../../lib/api';

const RUS_JOINTS = [
    { id: 'Radius', name: '桡骨骨骺', color: '#3b82f6', description: '前臂外侧骨远端骨骺' },
    { id: 'Ulna', name: '尺骨骨骺', color: '#8b5cf6', description: '前臂内侧骨远端骨骺' },
    { id: 'MCPFirst', name: '第一掌骨', color: '#ec4899', description: '拇指掌骨' },
    { id: 'MCPThird', name: '第三掌骨', color: '#f59e0b', description: '中指掌骨' },
    { id: 'MCPFifth', name: '第五掌骨', color: '#10b981', description: '小指掌骨' },
    { id: 'PIPFirst', name: '第一近节指骨', color: '#06b6d4', description: '拇指近节指骨' },
    { id: 'PIPThird', name: '第三近节指骨', color: '#f97316', description: '中指近节指骨' },
    { id: 'PIPFifth', name: '第五近节指骨', color: '#6366f1', description: '小指近节指骨' },
    { id: 'MIPThird', name: '第三中节指骨', color: '#14b8a6', description: '中指中节指骨' },
    { id: 'MIPFifth', name: '第五中节指骨', color: '#a855f7', description: '小指中节指骨' },
    { id: 'DIPFirst', name: '第一远节指骨', color: '#e11d48', description: '拇指远节指骨' },
    { id: 'DIPThird', name: '第三远节指骨', color: '#0891b2', description: '中指远节指骨' },
    { id: 'DIPFifth', name: '第五远节指骨', color: '#7c3aed', description: '小指远节指骨' }
];

const GRADE_OPTIONS = Array.from({ length: 15 }, (_, i) => ({ value: i, label: `${i}级` }));

interface ManualGradeTabProps {
    result: any;
    setResult?: (result: any) => void;
}

const ManualGradeTab: React.FC<ManualGradeTabProps> = ({ setResult }) => {
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [grades, setGrades] = useState<Record<string, number | null>>(() => {
        const initial: Record<string, number | null> = {};
        RUS_JOINTS.forEach(joint => {
            initial[joint.id] = null;
        });
        return initial;
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setLocalResult] = useState<any>(null);

    const handleGradeChange = (jointId: string, value: string) => {
        const gradeValue = value === '' ? null : parseInt(value, 10);
        setGrades(prev => ({
            ...prev,
            [jointId]: gradeValue
        }));
    };

    const filledCount = useMemo(() => {
        return Object.values(grades).filter(g => g !== null).length;
    }, [grades]);

    const handleSubmit = async () => {
        const filledGrades = Object.fromEntries(
            Object.entries(grades).filter(([_, v]) => v !== null) as [string, number][]
        );

        if (Object.keys(filledGrades).length === 0) {
            setError('请至少填写一个骨骼的分级');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE}/manual-grade-calculation`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...buildAuthHeaders()
                },
                body: JSON.stringify({
                    gender,
                    grades: filledGrades
                })
            });

            if (!response.ok) {
                throw new Error(await readErrorMessage(response));
            }

            const data = await response.json();
            setLocalResult(data);
            if (setResult) {
                setResult(data);
            }
        } catch (err: any) {
            setError(err.message || '计算失败，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = () => {
        const initial: Record<string, number | null> = {};
        RUS_JOINTS.forEach(joint => {
            initial[joint.id] = null;
        });
        setGrades(initial);
        setLocalResult(null);
        setError(null);
    };

    const chartData = useMemo(() => {
        if (!result?.joint_rus_details) return [];
        return result.joint_rus_details.map((item: any) => ({
            joint: item.joint,
            grade: item.grade_raw,
            score: item.score,
            color: RUS_JOINTS.find(j => j.id === item.joint)?.color || '#3b82f6'
        }));
    }, [result]);

    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.uploadCard}>
                <div className={styles.cardHeader}>
                    <h3>手动输入骨骼分级</h3>
                    <span style={{ color: '#64748b', fontSize: '0.85rem' }}>
                        已填写 {filledCount} / 13
                    </span>
                </div>

                <div className={styles.formGroup} style={{ marginTop: '1rem' }}>
                    <label>性别</label>
                    <div className={styles.radioGroup}>
                        <button 
                            className={gender === 'male' ? styles.btnActive : ''} 
                            onClick={() => setGender('male')}
                        >
                            ♂️ 男
                        </button>
                        <button 
                            className={gender === 'female' ? styles.btnActive : ''} 
                            onClick={() => setGender('female')}
                        >
                            ♀️ 女
                        </button>
                    </div>
                </div>

                <div className={styles.sectionBlock} style={{ marginTop: '1.5rem' }}>
                    <h4 style={{ marginBottom: '1rem' }}>骨骼成熟度分级输入</h4>
                    <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: '1rem' }}>
                        请根据X光片手动填写各骨骼的成熟度分级（0-14级），系统将自动计算RUS总分和骨龄。
                    </p>
                    
                    <div style={{ display: 'grid', gap: '0.75rem' }}>
                        {RUS_JOINTS.map(joint => (
                            <div 
                                key={joint.id} 
                                style={{ 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    gap: '1rem',
                                    padding: '0.75rem',
                                    background: grades[joint.id] !== null ? '#f0fdf4' : '#f8fafc',
                                    borderRadius: '8px',
                                    border: `1px solid ${grades[joint.id] !== null ? '#86efac' : '#e2e8f0'}`
                                }}
                            >
                                <div style={{ 
                                    width: '12px', 
                                    height: '12px', 
                                    borderRadius: '50%', 
                                    background: joint.color,
                                    flexShrink: 0
                                }} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{joint.name}</div>
                                    <div style={{ color: '#64748b', fontSize: '0.75rem' }}>{joint.description}</div>
                                </div>
                                <select
                                    value={grades[joint.id] ?? ''}
                                    onChange={(e) => handleGradeChange(joint.id, e.target.value)}
                                    style={{
                                        width: '80px',
                                        padding: '0.5rem',
                                        borderRadius: '6px',
                                        border: '1px solid #cbd5e1',
                                        background: '#fff',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem'
                                    }}
                                >
                                    <option value="">--</option>
                                    {GRADE_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                        ))}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
                    <button 
                        className={styles.btnAnalyze}
                        onClick={handleSubmit}
                        disabled={loading || filledCount === 0}
                        style={{ flex: 1 }}
                    >
                        {loading ? '计算中...' : (
                            <>
                                <Calculator size={18} /> 计算骨龄
                            </>
                        )}
                    </button>
                    <button 
                        className={styles.btnSecondary}
                        onClick={handleReset}
                        disabled={loading}
                    >
                        重置
                    </button>
                </div>

                {error && (
                    <div className={styles.errorBanner} style={{ marginTop: '1rem' }}>
                        {error}
                    </div>
                )}
            </div>

            <div className={styles.resultsCard}>
                {result ? (
                    <div className={styles.reportFadeIn}>
                        <div className={styles.reportHeader}>
                            <h3>骨龄计算结果</h3>
                            <span className={styles.reportId}>RUS-CHN 公式法</span>
                        </div>

                        <div className={styles.metricsGrid}>
                            <div className={`${styles.metricCard} ${styles.primaryMetric}`}>
                                <span>预测骨龄</span>
                                <strong>{result.bone_age?.toFixed(2) || '--'} 岁</strong>
                                <span className={styles.subtext}>基于RUS-CHN公式</span>
                            </div>
                            <div className={styles.metricCard}>
                                <span>RUS总分</span>
                                <strong>{result.total_score || 0}</strong>
                                <span className={styles.subtext}>13块骨骼累计</span>
                            </div>
                            <div className={styles.metricCard}>
                                <span>填写骨骼</span>
                                <strong>{result.joint_count || 0} / 13</strong>
                                <span className={styles.subtext}>已输入数量</span>
                            </div>
                            <div className={styles.metricCard}>
                                <span>置信度</span>
                                <strong>{result.confidence?.toFixed(1) || 0}%</strong>
                                <span className={styles.subtext}>基于完整度</span>
                            </div>
                        </div>

                        {chartData.length > 0 && (
                            <div className={styles.sectionBlock}>
                                <h4>骨骼分级分布</h4>
                                <div style={{ height: Math.max(260, chartData.length * 34), width: '100%', marginTop: '0.8rem' }}>
                                    <ResponsiveContainer>
                                        <BarChart
                                            data={chartData}
                                            layout="vertical"
                                            margin={{ top: 5, right: 26, left: 20, bottom: 5 }}
                                        >
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" domain={[0, 14]} />
                                            <YAxis dataKey="joint" type="category" width={86} />
                                            <Tooltip
                                                cursor={{ fill: 'transparent' }}
                                                formatter={(value: any, name: any, entry: any) => {
                                                    if (name === 'grade') {
                                                        return [`${value}级`, '分级'];
                                                    }
                                                    return [value, name];
                                                }}
                                            />
                                            <Bar dataKey="grade" barSize={18} radius={[0, 4, 4, 0]}>
                                                {chartData.map((entry: any, index: number) => (
                                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}

                        <div className={styles.sectionBlock}>
                            <h4>骨骼分级明细</h4>
                            <div style={{ marginTop: '0.8rem', overflowX: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 420 }}>
                                    <thead>
                                        <tr style={{ background: '#f8fafc' }}>
                                            <th style={{ textAlign: 'left', padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.82rem' }}>骨骼</th>
                                            <th style={{ textAlign: 'left', padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.82rem' }}>分级</th>
                                            <th style={{ textAlign: 'left', padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.82rem' }}>阶段</th>
                                            <th style={{ textAlign: 'left', padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.82rem' }}>得分</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.joint_rus_details?.map((item: any) => (
                                            <tr key={item.joint}>
                                                <td style={{ padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.86rem' }}>
                                                    {RUS_JOINTS.find(j => j.id === item.joint)?.name || item.joint}
                                                </td>
                                                <td style={{ padding: '8px 10px', border: '1px solid #e2e8f0', fontWeight: 700, fontSize: '0.86rem' }}>
                                                    {item.grade_raw}级
                                                </td>
                                                <td style={{ padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.86rem' }}>
                                                    阶段 {item.stage}
                                                </td>
                                                <td style={{ padding: '8px 10px', border: '1px solid #e2e8f0', fontSize: '0.86rem' }}>
                                                    {item.score}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className={styles.textReport}>
                            <pre style={{ whiteSpace: 'pre-wrap' }}>
{`RUS-CHN 骨龄评估报告
========================

性别: ${result.gender === 'male' ? '男' : '女'}
预测骨龄: ${result.bone_age?.toFixed(2) || '--'} 岁
RUS总分: ${result.total_score || 0}
评估骨骼: ${result.joint_count || 0} / 13
置信度: ${result.confidence?.toFixed(1) || 0}%

计算公式:
${result.formula_expression}

说明: RUS-CHN方法基于13块关键骨骼的成熟度评分，
通过多项式公式计算骨龄，是临床常用的骨龄评估方法之一。`}
                            </pre>
                        </div>
                    </div>
                ) : (
                    <div className={styles.emptyResults}>
                        <Calculator size={48} color="#cbd5e1" />
                        <p>在左侧输入各骨骼分级后</p>
                        <p>点击"计算骨龄"查看结果</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ManualGradeTab;
