import React, { useState, useRef, useMemo } from 'react';
import { 
    Upload, Moon, Sun, Contrast, RotateCcw, Activity, BarChart2 
} from 'lucide-react';
import { 
    ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar, Cell 
} from 'recharts';
import styles from '../UserDashboard.module.css';
import type { PredictionResult, ImageSettings } from '../types';
import { DEFAULT_SETTINGS } from '../types';
import { API_BASE } from '../../../config';

interface JointGradeTabProps {
    result: PredictionResult | null;
    setResult?: (result: PredictionResult | null) => void;
}

const JointGradeTab: React.FC<JointGradeTabProps> = ({ result, setResult }) => {
    // --- 1. 核心状态管理 ---
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [realAge, setRealAge] = useState('');
    const [currentHeight, setCurrentHeight] = useState('');
    const [imgSettings, setImgSettings] = useState<ImageSettings>(DEFAULT_SETTINGS);
    
    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- 2. 图像样式计算 ---
    const imageStyle = useMemo(() => ({
        filter: `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}) ${imgSettings.invert ? 'invert(1)' : ''}`,
        transform: `scale(${imgSettings.scale / 100})`,
        maxWidth: '100%',
        borderRadius: '8px',
        transition: 'filter 0.2s ease, transform 0.2s ease'
    }), [imgSettings]);

    // --- 3. 交互逻辑 ---
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            const reader = new FileReader();
            reader.onload = (ev) => setPreview(ev.target?.result as string);
            reader.readAsDataURL(selectedFile);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            setFile(droppedFile);
            const reader = new FileReader();
            reader.onload = (ev) => setPreview(ev.target?.result as string);
            reader.readAsDataURL(droppedFile);
        }
    };

    const handleSubmit = async () => {
        if (!file &&!preview) {
            setError('请先上传 X 光影像图片');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            if (file) formData.append('file', file);
            formData.append('gender', gender);
            formData.append('real_age', realAge);
            formData.append('preprocessing_enabled', String(imgSettings.usePreprocessing));
            formData.append('brightness', String(imgSettings.brightness - 100));
            formData.append('contrast', String(imgSettings.contrast));

            const token = localStorage.getItem('boneage_token');
            const headers: Record<string, string> = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const resp = await fetch(`${API_BASE}/joint-grading`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!resp.ok) throw new Error('小关节分级预测请求失败');

            const data = await resp.json();
            const newResult: PredictionResult = {
                ...data,
                id: data.id || `joint-${Date.now()}`,
                timestamp: Date.now(),
                filename: file?.name || 'unknown',
                gender
            };
            
            if (setResult) setResult(newResult);
        } catch (err: any) {
            setError(err.message || '分析失败，请检查网络或影像质量');
        } finally {
            setLoading(false);
        }
    };

    // --- 4. 数据转换逻辑 (用于图表和表格) ---
    const chartData = useMemo(() => {
        if (!result?.joint_grades) return [];
        return Object.entries(result.joint_grades)
            .filter(([_, g]) => g.status === 'ok' && g.grade_raw !== undefined)
            .map(([name, g]) => {
                let color = '#22c55e'; // 默认绿色
                if (g.grade_raw! > 10) color = '#ef4444';
                else if (g.grade_raw! > 7) color = '#f97316';
                else if (g.grade_raw! > 4) color = '#eab308';
                
                return { 
                    joint: name, 
                    grade: g.grade_raw ?? 0, 
                    confidence: Math.round((g.score || 0) * 100), 
                    color 
                };
            })
            .sort((a, b) => b.grade - a.grade);
    }, [result]);

    const pendingJoints = useMemo(() => {
        if (!result?.joint_grades) return [];
        return Object.entries(result.joint_grades)
            .filter(([_, g]) => g.status !== 'ok')
            .map(([name]) => name);
    }, [result]);

    const recognizedRows = useMemo(() => {
        return chartData.map(item => ({
            ...item,
            status: '正常识别'
        }));
    }, [chartData]);

    // --- 5. 渲染视图 ---
   return (
    <div className={styles.workspaceGrid}>
        {/* --- 左侧：操作面板 --- */}
        <div className={styles.uploadCard}>
            <div className={styles.cardHeader}>
                <h3>上传 X 光影像</h3>
                {preview && (
                    <div className={styles.imageToolbar}>
                        <button title="降低亮度" onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness - 10 })}><Moon size={14} /></button>
                        <button title="增加亮度" onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness + 10 })}><Sun size={14} /></button>
                        <button title="反相模式" onClick={() => setImgSettings({ ...imgSettings, invert: !imgSettings.invert })} className={imgSettings.invert ? styles.activeTool : ''}><Contrast size={14} /></button>
                        <button title="重置" onClick={() => setImgSettings(DEFAULT_SETTINGS)}><RotateCcw size={14} /></button>
                    </div>
                )}
            </div>

            <div
                className={`${styles.uploadArea} ${!file && !preview ? styles.empty : ''}`}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={handleDrop}
                onClick={() => !file && !preview && fileInputRef.current?.click()}
            >
                {preview ? (
                    <div className={styles.previewContainer}>
                        <img src={preview} alt="X-Ray" className={styles.previewImage} style={imageStyle} />
                        <button className={styles.reuploadBtn} onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                            <Upload size={14} /> 更换影像
                        </button>
                    </div>
                ) : (
                    <div className={styles.placeholder}>
                        <Upload size={48} color="#94a3b8" />
                        <p>点击或将 X 光图片拖拽至此处</p>
                    </div>
                )}
                <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="image/*" style={{ display: 'none' }} />
            </div>

            <div className={styles.controlsForm}>
                <div className={styles.formGroup}>
                    <label>性别</label>
                    <div className={styles.radioGroup}>
                        <button className={gender === 'male' ? styles.btnActive : ''} onClick={() => setGender('male')}>‍♂️ 男</button>
                        <button className={gender === 'female' ? styles.btnActive : ''} onClick={() => setGender('female')}>‍♀️ 女</button>
                    </div>
                </div>
                <div className={styles.formGroup}>
                    <label>参考数据（选填）</label>
                    <div className={styles.inputRow}>
                        <input type="number" placeholder="实际年龄" value={realAge} onChange={(e) => setRealAge(e.target.value)} step="0.1" />
                        <input type="number" placeholder="身高 (cm)" value={currentHeight} onChange={(e) => setCurrentHeight(e.target.value)} step="0.5" />
                    </div>
                </div>

                <div className={styles.preprocessingCard}>
                    <div className={styles.flexBetween}>
                        <div className={styles.preText}>
                            <strong>高级图像预处理</strong>
                            <p>增强对比度以提升小关节识别率</p>
                        </div>
                        <label className={styles.switch}>
                            <input 
                                type="checkbox" 
                                checked={imgSettings.usePreprocessing} 
                                onChange={(e) => setImgSettings({ ...imgSettings, usePreprocessing: e.target.checked })} 
                            />
                            <span className={styles.slider}></span>
                        </label>
                    </div>

                    {imgSettings.usePreprocessing && (
                        <div className={styles.preContent} style={{ marginTop: '1rem', borderTop: '1px ridge #eee', paddingTop: '1rem' }}>
                            <div className={styles.preRow}>
                                <label>曝光度偏移 (Beta)</label>
                                <div className={styles.rangeWrapper}>
                                    <input 
                                        type="range" min="-100" max="100" step="1" 
                                        value={imgSettings.brightness - 100} 
                                        onChange={(e) => setImgSettings({ ...imgSettings, brightness: Number(e.target.value) + 100 })} 
                                    />
                                    <span>{imgSettings.brightness - 100}</span>
                                </div>
                            </div>
                            <div className={styles.preRow}>
                                <label>对比度系数 (Alpha)</label>
                                <div className={styles.inputWrapper}>
                                    <input 
                                        type="number" step="0.01" 
                                        style={{ width: '80px', padding: '4px' }}
                                        value={imgSettings.contrast} 
                                        onChange={(e) => setImgSettings({ ...imgSettings, contrast: Number(e.target.value) })} 
                                    />

                                </div>
                            </div>
                            <div className={styles.preRow}>
                                <label>缩放比例 (%)</label>
                                <div className={styles.rangeWrapper}>
                                    <input 
                                        type="range" min="50" max="150" step="1" 
                                        value={imgSettings.scale} 
                                        onChange={(e) => setImgSettings({ ...imgSettings, scale: Number(e.target.value) })} 
                                    />
                                    <span>{imgSettings.scale}%</span>
                                </div>
                            </div>
                            <div className={styles.preRow}>
                                <label>反相模式</label>
                                <label className={styles.switch} style={{ margin: 0 }}>
                                    <input 
                                        type="checkbox" 
                                        checked={imgSettings.invert} 
                                        onChange={(e) => setImgSettings({ ...imgSettings, invert: e.target.checked })} 
                                    />
                                    <span className={styles.slider}></span>
                                </label>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <button className={styles.btnAnalyze} onClick={handleSubmit} disabled={loading || (!file && !preview)}>
                {loading ? 'AI 分析中...' : <><Activity size={18} /> 开始小关节评估</>}
            </button>
            {error && <div className={styles.errorBanner}>{error}</div>}
        </div>

        {/* --- 右侧：结果展示面板 --- */}
        <div className={styles.resultsCard}>
            {result ? (
                <div className={styles.reportFadeIn}>
                    <div className={styles.reportHeader}>
                        <h3>小关节分级报告</h3>
                        <span className={styles.reportId}>#{result?.id?.slice(-6) || '000000'}</span>
                    </div>

                    {/* 1. 检测可视化 */}
                    {result.joint_detect_13?.plot_image_base64 && (
                        <div className={styles.sectionBlock}>
                            <h4>AI 检测可视化</h4>
                            <div className={styles.visualInfo}>
                                <img 
                                    src={result.joint_detect_13.plot_image_base64} 
                                    alt="检测结果" 
                                    className={styles.heatmapImg} 
                                    style={{ maxWidth: '300px' }} 
                                />
                                <div className={styles.metaInfo}>
                                    <p><strong>识别数量：</strong>{result.joint_detect_13.detected_count} / 13</p>
                                    <p><strong>判定方位：</strong>{result.joint_detect_13.hand_side === 'left' ? '左手' : '右手'}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 2. 分级分布趋势 */}
                    <div className={styles.sectionBlock}>
                        <h4>分级分布趋势</h4>
                        {chartData && chartData.length > 0 ? (
                            <div style={{ height: Math.max(260, chartData.length * 35), width: '100%', marginTop: '1rem' }}>
                                <ResponsiveContainer>
                                    <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                        <XAxis type="number" domain={[0, 14]} ticks={[0, 2, 4, 6, 8, 10, 12, 14]} />
                                        <YAxis dataKey="joint" type="category" width={90} />
                                        <Tooltip 
                                            cursor={{ fill: '#f1f5f9' }}
                                            formatter={(val, _name, props: any) => [`等级: ${val}`, `置信度: ${props.payload.confidence}%`]}
                                        />
                                        <Bar dataKey="grade" barSize={20} radius={[0, 4, 4, 0]}>
                                            {chartData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <p className={styles.emptyNote}>暂无有效分级数据</p>
                        )}
                    </div>

                    {/* 3. 数据明细表 */}
                    <div className={styles.sectionBlock}>
                        <h4>分级明细表</h4>
                        <div className={styles.tableWrapper}>
                            <table className={styles.detailTable} style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ background: '#f8fafc' }}>
                                        <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>关节名称</th>
                                        <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>分级(Grade)</th>
                                        <th style={{ padding: '10px', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>置信度</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recognizedRows?.map((row) => (
                                        <tr key={row.joint}>
                                            <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{row.joint}</td>
                                            <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0', fontWeight: 'bold' }}>{row.grade}</td>
                                            <td style={{ padding: '10px', borderBottom: '1px solid #e2e8f0' }}>{row.confidence}%</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {pendingJoints?.length > 0 && (
                            <p className={styles.warningText} style={{ color: '#b45309', marginTop: '10px', fontSize: '0.9rem' }}>
                                待定关节（未识别）：{pendingJoints.join('、')}
                            </p>
                        )}
                    </div>
                </div>
            ) : (
                <div className={styles.emptyResults}>
                    <BarChart2 size={64} color="#cbd5e1" />
                    <p>请在左侧上传 X 光片以生成小关节评估报告</p>
                </div>
            )}
        </div>
    </div>
);
};
export default JointGradeTab;
