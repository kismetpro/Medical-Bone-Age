import React from 'react';
import type { RefObject } from 'react';
import { Upload, Moon, Sun, Contrast, RotateCcw, Activity, BarChart2 } from 'lucide-react';
import { ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar } from 'recharts';
import styles from '../UserDashboard.module.css';
import type { PredictionResult, ImageSettings } from '../types';
import { DEFAULT_SETTINGS } from '../types';

interface PredictTabProps {
    file: File | null;
    preview: string | null;
    imageStyle: React.CSSProperties;
    imgSettings: ImageSettings;
    setImgSettings: (settings: ImageSettings) => void;
    handleDrop: (e: React.DragEvent<HTMLDivElement>) => void;
    fileInputRef: RefObject<HTMLInputElement | null>;
    handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    result: PredictionResult | null;
    loading: boolean;
    gender: string;
    setGender: (gender: string) => void;
    realAge: string;
    setRealAge: (age: string) => void;
    currentHeight: string;
    setCurrentHeight: (height: string) => void;
    handleSubmit: () => void;
    error: string | null;
    generateComparisonData: (res: PredictionResult) => any[];
    getEvaluation: (boneAge: number, chronoAge: number) => { status: string, color: string, desc: string };
    getBoxStyle: (coord: number[]) => React.CSSProperties;
    generateMedicalReport: (data: PredictionResult | null) => string;
}

const PredictTab: React.FC<PredictTabProps> = ({
    file, preview, imageStyle, imgSettings, setImgSettings, handleDrop,
    fileInputRef, handleFileChange, result, loading, gender, setGender,
    realAge, setRealAge, currentHeight, setCurrentHeight, handleSubmit, error,
    generateComparisonData, getEvaluation, getBoxStyle, generateMedicalReport
}) => {
    return (
        <div className={styles.workspaceGrid}>
            {/* Work Area Left */}
            <div className={styles.uploadCard}>
                <div className={styles.cardHeader}>
                    <h3>上传 X 光影像</h3>
                    {preview && (
                        <div className={styles.imageToolbar}>
                            <button onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness - 10 })}><Moon size={14} /></button>
                            <button onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness + 10 })}><Sun size={14} /></button>
                            <button onClick={() => setImgSettings({ ...imgSettings, invert: !imgSettings.invert })} className={imgSettings.invert ? styles.activeTool : ''}><Contrast size={14} /></button>
                            <button onClick={() => setImgSettings(DEFAULT_SETTINGS)}><RotateCcw size={14} /></button>
                        </div>
                    )}
                </div>

                <div
                    className={`${styles.uploadArea} ${!file && !preview ? styles.empty : ''}`}
                    onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={handleDrop}
                    onClick={() => !file && fileInputRef.current?.click()}
                >
                    {preview ? (
                        <div className={styles.previewContainer}>
                            <img src={preview} alt="X-Ray" className={styles.previewImage} style={imageStyle} />
                            <button className={styles.reuploadBtn} onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}><Upload size={14} /> 更换影像</button>
                        </div>
                    ) : (
                        result && !file ? (
                            <div className={styles.placeholder}><p>已加载过往检测记录</p><button className={styles.btnPrimary} onClick={() => fileInputRef.current?.click()}>上传新影像以预测</button></div>
                        ) : (
                            <div className={styles.placeholder}>
                                <Upload size={48} color="#94a3b8" />
                                <p>点击或将 X 光图片拖拽至此处</p>
                            </div>
                        )
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
                        <label>参考数据（选填项）</label>
                        <div className={styles.inputRow}>
                            <input type="number" placeholder="实际年龄 (岁)" value={realAge} onChange={(e) => setRealAge(e.target.value)} step="0.1" title="实际年龄用于提供超前/落后分析" />
                            <input type="number" placeholder="当前身高 (cm)" value={currentHeight} onChange={(e) => setCurrentHeight(e.target.value)} step="0.5" title="提供身高用于预测成年身高" />
                        </div>
                    </div>
                </div>

                <button className={styles.btnAnalyze} onClick={handleSubmit} disabled={(!file && !preview) || loading}>
                    {loading ? '系统推断中...' : <><Activity size={18} /> 开始分析与出具报告</>}
                </button>
                {error && <div className={styles.errorBanner}>{error}</div>}
            </div>

            {/* Results Area Right */}
            <div className={styles.resultsCard}>
                {result ? (
                    <div className={styles.reportFadeIn}>
                        <div className={styles.reportHeader}>
                            <h3>预测医学报告</h3>
                            <span className={styles.reportId}>#{result.id.slice(-6)}</span>
                        </div>

                        <div className={styles.metricsGrid}>
                            <div className={`${styles.metricCard} ${styles.primaryMetric}`}>
                                <span>评估骨龄为</span>
                                <strong>{result.predicted_age_years.toFixed(1)} <small>岁</small></strong>
                                <div className={styles.subtext}>{result.predicted_age_months.toFixed(1)} 个月</div>
                            </div>

                            <div className={styles.metricCard}>
                                <span>实际年龄</span>
                                {result.real_age_years ? (
                                    <strong style={{ color: '#0f172a' }}>{result.real_age_years.toFixed(1)} <small>岁</small></strong>
                                ) : (
                                    <strong style={{ color: '#94a3b8', fontSize: '0.95rem' }}>未填写</strong>
                                )}
                            </div>

                            {result.predicted_adult_height ? (
                                <div className={styles.metricCard}>
                                    <span>预测成年体高 (PAH)</span>
                                    <strong>{result.predicted_adult_height} <small>cm</small></strong>
                                </div>
                            ) : (
                                <div className={styles.metricCard}>
                                    <span>预测应用性别</span>
                                    <strong>{result.gender === 'male' ? '男' : '女'}</strong>
                                </div>
                            )}

                            {result.real_age_years ? (
                                <div className={styles.metricCard}>
                                    <span>整体发育状态</span>
                                    <strong style={{ color: getEvaluation(result.predicted_age_years, result.real_age_years).color }}>
                                        {getEvaluation(result.predicted_age_years, result.real_age_years).status.split(' ')[0]}
                                    </strong>
                                </div>
                            ) : (
                                <div className={styles.metricCard}>
                                    <span>整体发育状态</span>
                                    <strong style={{ color: '#94a3b8', fontSize: '1rem' }}>无实际年龄</strong>
                                </div>
                            )}
                        </div>

                        {result.real_age_years && (
                            <div className={styles.sectionBlock}>
                                <h4>评估对照分析</h4>
                                <div style={{ height: 180, width: '100%', marginTop: '1rem' }}>
                                    <ResponsiveContainer>
                                        <BarChart data={generateComparisonData(result)} layout="vertical" margin={{ top: 5, right: 30, left: 30, bottom: 5 }}>
                                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                            <XAxis type="number" domain={[0, Math.max(result.predicted_age_years, result.real_age_years || 0) + 2]} />
                                            <YAxis dataKey="name" type="category" width={80} />
                                            <Tooltip cursor={{ fill: 'transparent' }} />
                                            <Bar dataKey="age" barSize={20} radius={[0, 4, 4, 0]} label={{ position: 'right', fill: '#666' }} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        )}

                        {result.heatmap_base64 && (
                            <div className={styles.sectionBlock}>
                                <h4>AI 特征焦点分析度与异常（GradCAM）</h4>
                                <div className={styles.heatmapWrapper}>
                                    <img src={result.heatmap_base64} alt="GradCAM" className={styles.heatmapImg} />
                                    {result.anomalies?.map((item, idx) => (
                                        item.score > 0.45 && (
                                            <div key={idx} style={getBoxStyle(item.coord)}>
                                                <span className={styles.anomalyTag}>
                                                    {item.type} {Math.round(item.score * 100)}%
                                                </span>
                                            </div>
                                        )
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className={styles.textReport}>
                            <pre>{generateMedicalReport(result)}</pre>
                        </div>

                    </div>
                ) : (
                    <div className={styles.emptyResults}>
                        <BarChart2 size={48} color="#cbd5e1" />
                        <p>上传手部后前位 X 光影像以在此浏览为您生成的诊断报告。</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PredictTab;
