import React from 'react';
import type { RefObject } from 'react';
import { Upload, Moon, Sun, Contrast, RotateCcw, Activity, BarChart2 } from 'lucide-react';
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
    getEvaluation: (boneAge: number, chronoAge: number) => { status: string, color: string, desc: string };
    getBoxStyle: (coord: number[]) => React.CSSProperties;
    generateMedicalReport: (data: PredictionResult | null) => string;
    imageSource?: 'upload' | 'preprocessing' | 'history' | null;
}

const PredictTab: React.FC<PredictTabProps> = ({
    file, preview, imageStyle, imgSettings, setImgSettings, handleDrop,
    fileInputRef, handleFileChange, result, loading, gender, setGender,
    realAge, setRealAge, currentHeight, setCurrentHeight, handleSubmit, error,
    getEvaluation, getBoxStyle, generateMedicalReport,
    imageSource
}) => {
    // 计算年龄差并返回对应表情
    const getAgeDiffEmoji = (diff: number) => {
        if (diff <= -1.5) return "😔"; // 严重发育迟缓
        if (diff < 0) return "🙁";    // 轻度发育迟缓
        if (diff === 0) return "😊";  // 正常
        if (diff <= 1.5) return "😯"; // 轻度提早发育
        return "😡";                  // 严重提早发育
    };

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
                            {imageSource && (
                                <div className={styles.sourceBadge}>
                                    {imageSource === 'upload' && '本地上传'}
                                    {imageSource === 'preprocessing' && '预处理'}
                                    {imageSource === 'history' && '历史记录'}
                                </div>
                            )}
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

                <div className={styles.preprocessingCard}>
                    <div className={styles.flexBetween}>
                        <div className={styles.preText}>
                            <strong>高级图像预处理</strong>
                            <p>提升低对比度影像的 AI 识别率</p>
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
                        <div className={styles.preContent}>
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
                                        value={imgSettings.contrast} 
                                        onChange={(e) => setImgSettings({ ...imgSettings, contrast: Number(e.target.value) })} 
                                    />
                                    <small>建议值: 13.24</small>
                                </div>
                            </div>
                        </div>
                    )}
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

                        {/* 修正后的评估对照分析模块（全部添加 styles. 前缀） */}
                        {result.real_age_years && (
                            <div className={styles.sectionBlock}>
                                <h4>评估对照分析</h4>
                                <div className={styles.ageProgressContainer}>
                                    {/* 分段色带 */}
                                    <div className={styles.ageProgressBar}>
                                        <div className={styles.progressSegmentAbnormalLeft}></div>
                                        <div className={styles.progressSegmentDelayed}></div>
                                        <div className={styles.progressSegmentNormal}></div>
                                        <div className={styles.progressSegmentAdvanced}></div>
                                        <div className={styles.progressSegmentAbnormalRight}></div>
                                    </div>
                                    
                                    {/* 刻度标签 */}
                                    <div className={styles.progressTicks}>
                                        <span>-2岁</span>
                                        <span>-1岁</span>
                                        <span>0岁</span>
                                        <span>1岁</span>
                                        <span>2岁</span>
                                    </div>
                                    
                                    {/* 年龄差标记点 */}
                                    {(() => {
                                        const ageDiff = result.predicted_age_years - result.real_age_years;
                                        // 计算标记位置（映射-3~+3岁到0~100%）
                                        const pos = Math.max(0, Math.min(100, ((ageDiff + 3) / 6) * 100));
                                        return (
                                            <div 
                                                className={styles.ageDiffMarker}
                                                style={{ left: `${pos}%` }}
                                                title={`骨龄差: ${ageDiff.toFixed(1)}岁`}
                                            >
                                                {getAgeDiffEmoji(ageDiff)}
                                            </div>
                                        );
                                    })()}
                                </div>

                                {/* 结论文字 */}
                                <div className={styles.progressConclusion}>
                                    <span className={styles.conclusionLabel}>结论：</span>
                                    <span className={styles.conclusionValue}>
                                        骨龄年龄差：{(result.predicted_age_years - result.real_age_years).toFixed(1)} 岁
                                    </span>
                                </div>

                                {/* 图例 */}
                                <div className={styles.progressLegend}>
                                    <div className={styles.legendItem}>
                                        <span className={styles.legendDotAbnormal}></span>
                                        <span>异常</span>
                                    </div>
                                    <div className={styles.legendItem}>
                                        <span className={styles.legendDotDelayed}></span>
                                        <span>发育迟缓</span>
                                    </div>
                                    <div className={styles.legendItem}>
                                        <span className={styles.legendDotNormal}></span>
                                        <span>发育正常</span>
                                    </div>
                                    <div className={styles.legendItem}>
                                        <span className={styles.legendDotAdvanced}></span>
                                        <span>提早发育</span>
                                    </div>
                                    <div className={styles.legendItem}>
                                        <span className={styles.legendDotAbnormal}></span>
                                        <span>异常</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {result.heatmap_base64 && (
                            <div className={styles.sectionBlock}>
                                <h4>AI 特征焦点分析度与异常（GradCAM）</h4>
                                <div className={styles.heatmapWrapper}>
                                    <img src={result.heatmap_base64} alt="GradCAM" className={styles.heatmapImg}/>
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