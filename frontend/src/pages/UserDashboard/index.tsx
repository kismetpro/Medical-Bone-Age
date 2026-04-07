import { useState, useRef, useEffect } from 'react';
import { History as HistoryIcon } from 'lucide-react';

import 'katex/dist/katex.min.css';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
    getHighConfidenceFractures,
    normalizePredictionResult,
    resolveForeignObjectDetection,
    submitPredictionRequest
} from '../../lib/prediction';
import { dataUrlToFile } from '../../lib/imagePreprocessing';
import { buildAuthHeaders, readErrorMessage } from '../../lib/api';
import { API_BASE } from '../../config';
import styles from './UserDashboard.module.css';

// --- Types ---
import type { 
    PredictionResult, BoneAgePoint, BoneAgeTrend, ImageSettings 
} from './types';
import { DEFAULT_SETTINGS } from './types';

// --- Components ---
import UserSidebar from './components/UserSidebar';
import PredictTab from './components/PredictTab';
import JointGradeTab from './components/JointGradeTab';
import HistoryTab from './components/HistoryTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';
import SettingsTab from './components/SettingsTab';
import ImagePreprocessingTab from './components/ImagePreprocessingTab';
import BoneAgeDevelopmentTab from './components/BoneAgeDevelopmentTab';

export default function UserDashboard() {
    const { username, logout } = useAuth();
    const navigate = useNavigate();

    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [gender, setGender] = useState<string>('male');
    const [realAge, setRealAge] = useState<string>('');
    const [currentHeight, setCurrentHeight] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<PredictionResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [imgSettings, setImgSettings] = useState<ImageSettings>(DEFAULT_SETTINGS);
    const [predictionImageSource, setPredictionImageSource] = useState<'upload' | 'preprocessing' | 'history' | null>(null);

    const [history, setHistory] = useState<PredictionResult[]>([]);
    const [showHistory, setShowHistory] = useState(false);
    const [activeTab, setActiveTab] = useState<'predict' | 'joint-grade' | 'history' | 'community' | 'consultation' | 'settings' | 'preprocessing' | 'bone-age-development'>('predict');
    const [boneAgePoints, setBoneAgePoints] = useState<BoneAgePoint[]>([]);
    const [jointResult, setJointResult] = useState<PredictionResult | null>(null);
    const [trend, setTrend] = useState<BoneAgeTrend | null>(null);
    const [pointTime, setPointTime] = useState('');
    const [pointBoneAge, setPointBoneAge] = useState('');
    const [pointChronAge, setPointChronAge] = useState('');
    const [pointNote, setPointNote] = useState('');
    const [pointLoading, setPointLoading] = useState(false);

    const fileInputRef = useRef<HTMLInputElement | null>(null);


    const fetchPredictionHistory = async () => {
        try {
            const resp = await fetch(`${API_BASE}/predictions`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setHistory(data.items);
            }
        } catch (e) {
            console.error('获取历史记录失败', e);
        }
    };

    const fetchBoneAgePoints = async () => {
        try {
            const resp = await fetch(`${API_BASE}/bone-age-points`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setBoneAgePoints(data.items || []);
            }
        } catch (e) {
            console.error('获取散点数据失败', e);
        }
    };

    const fetchBoneAgeTrend = async () => {
        try {
            const resp = await fetch(`${API_BASE}/bone-age-trend`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setTrend(data as BoneAgeTrend);
            }
        } catch (e) {
            console.error('获取回归趋势失败', e);
        }
    };

    useEffect(() => {
        fetchPredictionHistory();
        fetchBoneAgePoints();
        fetchBoneAgeTrend();
    }, []);

    useEffect(() => {
        return () => {
            if (preview?.startsWith('blob:')) {
                URL.revokeObjectURL(preview);
            }
        };
    }, [preview]);

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const getBoxStyle = (coord: number[]): React.CSSProperties => {
        const [xc, yc, w, h] = coord;
        return {
            left: `${(xc - w / 2) * 100}%`,
            top: `${(yc - h / 2) * 100}%`,
            width: `${w * 100}%`,
            height: `${h * 100}%`,
            position: 'absolute',
            border: '2px solid red',
            pointerEvents: 'none'
        };
    };

    const parseAnomalies = (data: PredictionResult | null) => {
        return {
            fractures: getHighConfidenceFractures(data?.anomalies),
            foreign_objects: resolveForeignObjectDetection(data).items,
        };
    };

    const generateMedicalReport = (data: PredictionResult | null) => {
        if (!data) return "分析中...";
        const { predicted_age_years, gender, rus_bone_age_years, joint_rus_total_score } = data;
        const parsed = parseAnomalies(data);

        let report = `【影像学分析报告】\n`;
        report += `1. 基本信息：受检者性别为${gender === 'male' ? '男' : '女'}，`;
        report += `测定骨龄约为 ${predicted_age_years.toFixed(1)} 岁`;
        if (rus_bone_age_years) {
            report += `（RUS-CHN法：${rus_bone_age_years.toFixed(1)} 岁`;
            if (joint_rus_total_score) {
                report += `，总分 ${joint_rus_total_score}`;
            }
            report += `）`;
        }
        report += `。\n\n`;
        report += `2. 影像发现：\n`;
        if (parsed.fractures.length > 0) {
            report += `   - [警告] 在影像中识别到 ${parsed.fractures.length} 处疑似骨折区域。建议临床结合压痛点进一步核实。\n`;
        } else {
            report += `   - 骨骼连续性尚好，未见明显骨折征象。\n`;
        }
        if (parsed.foreign_objects.length > 0) {
            report += `   - 注意：影像中存在 ${parsed.foreign_objects.length} 处高密度异物，可能影响骨龄判断。\n`;
        }
        report += `\n3. 结论建议：\n`;
        report += parsed.fractures.length > 0 ? `   结论：疑似存在外伤性改变。` : `   结论：骨龄发育符合当前生理阶段。`;
        return report;
    };

    const getEvaluation = (boneAge: number, chronoAge: number) => {
        const diff = boneAge - chronoAge;
        if (diff > 1) return { status: '早熟 (Advanced)', color: '#ef4444', desc: '骨龄显著大于生活年龄' };
        if (diff < -1) return { status: '晚熟 (Delayed)', color: '#3b82f6', desc: '骨龄显著小于生活年龄' };
        return { status: '正常 (Normal)', color: '#22c55e', desc: '骨龄与生活年龄基本一致' };
    };

    const loadFile = (selectedFile: File) => {
        setFile(selectedFile);
        setPreview(URL.createObjectURL(selectedFile));
        setResult(null);
        setError(null);
        setImgSettings(DEFAULT_SETTINGS);
        setPredictionImageSource('upload');
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) loadFile(e.target.files[0]);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault(); e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
    };

    const handleSubmit = async () => {
        if (!file) return;
        setLoading(true); setError(null);

        try {
            const data = await submitPredictionRequest({
                file,
                gender,
                currentHeight,
                realAge,
                preprocessingEnabled: imgSettings.usePreprocessing,
                brightness: imgSettings.brightness - 100,
                contrast: imgSettings.contrast,
                headers: buildAuthHeaders(),
            });
            const newResult = normalizePredictionResult<PredictionResult>(data, realAge);
            setResult(newResult);
            fetchPredictionHistory();
            fetchBoneAgePoints();
            fetchBoneAgeTrend();
        } catch (err: any) {
            setError(`预测失败: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const restoreHistoryItem = async (item: Partial<PredictionResult>) => {
        if (!item.id) return;
        try {
            const resp = await fetch(`${API_BASE}/predictions/${item.id}`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                const fullItem = normalizePredictionResult<PredictionResult>(data.data, data.data?.real_age_years);
                setResult(fullItem);
                setGender(fullItem.gender);
                if (fullItem.real_age_years) setRealAge(fullItem.real_age_years.toString());
                setPreview(null);
                setFile(null);
                setPredictionImageSource('history');
                setShowHistory(false);
            } else {
                setError('无法加载详细记录');
            }
        } catch (e) {
            setError('网络错误');
        }
    };

    const updatePrediction = async (item: PredictionResult) => {
        const newAge = window.prompt('请输入新的预测骨龄（岁）', item.predicted_age_years.toString());
        if (!newAge) return;
        const parsedAge = Number(newAge);
        if (!Number.isFinite(parsedAge) || parsedAge <= 0) {
            setError('请输入有效骨龄数值');
            return;
        }
        try {
            const resp = await fetch(`${API_BASE}/predictions/${item.id}`, {
                method: 'PUT',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ predicted_age_years: parsedAge })
            });
            await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(await readErrorMessage(resp));
            await fetchPredictionHistory();
            await fetchBoneAgePoints();
            await fetchBoneAgeTrend();
        } catch (e: any) {
            setError(e.message || '修改失败');
        }
    };

    const addPoint = async () => {
        const boneAge = Number(pointBoneAge);
        if (!Number.isFinite(boneAge) || boneAge <= 0) {
            setError('请输入有效的骨龄散点值');
            return;
        }
        const pointTs = pointTime ? new Date(pointTime).getTime() : Date.now();
        if (!Number.isFinite(pointTs)) {
            setError('日期格式无效');
            return;
        }
        setPointLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/bone-age-points`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({
                    point_time: pointTs,
                    bone_age_years: boneAge,
                    chronological_age_years: pointChronAge ? Number(pointChronAge) : undefined,
                    note: pointNote
                })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || '新增散点失败');
            setPointTime('');
            setPointBoneAge('');
            setPointChronAge('');
            setPointNote('');
            await fetchBoneAgePoints();
            await fetchBoneAgeTrend();
        } catch (e: any) {
            setError(e.message || '新增散点失败');
        } finally {
            setPointLoading(false);
        }
    };

    const deletePoint = async (pointId: number) => {
        if (!window.confirm('确认删除该散点吗？')) return;
        try {
            const resp = await fetch(`${API_BASE}/bone-age-points/${pointId}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || '删除失败');
            await fetchBoneAgePoints();
            await fetchBoneAgeTrend();
        } catch (e: any) {
            setError(e.message || '删除失败');
        }
    };

    const generateComparisonData = (res: PredictionResult) => {
        if (!res.real_age_years) return [];
        return [
            { name: '实际年龄', age: res.real_age_years, fill: '#94a3b8' },
            { name: '预测骨龄', age: res.predicted_age_years, fill: getEvaluation(res.predicted_age_years, res.real_age_years).color }
        ];
    };

    const handleUsePreprocessedImage = ({ dataUrl, fileName }: { dataUrl: string; fileName: string }) => {
        const processedFile = dataUrlToFile(dataUrl, fileName);
        setFile(processedFile);
        setPreview(dataUrl);
        setResult(null);
        setError(null);
        setImgSettings(DEFAULT_SETTINGS);
        setPredictionImageSource('preprocessing');
        setActiveTab('predict');
    };

    const imageStyle: React.CSSProperties = {
        filter: imgSettings.usePreprocessing 
            ? `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}) ${imgSettings.invert ? 'invert(1)' : ''}`
            : `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}) ${imgSettings.invert ? 'invert(1)' : ''}`,
        transform: `scale(${imgSettings.scale / 100})`,
        transition: 'filter 0.2s ease, transform 0.2s ease',
        maxWidth: '100%',
        borderRadius: '8px'
    };

    const trendData = boneAgePoints.map((p) => {
        let trendY: number | undefined = undefined;
        if (trend?.enough && trend.coefficients) {
            const base = boneAgePoints.length > 0 ? boneAgePoints[0].point_time : p.point_time;
            const t = (p.point_time - base) / (1000 * 60 * 60 * 24 * 365.25);
            const a = (p.chronological_age_years ?? t);
            trendY = trend.coefficients.intercept + trend.coefficients.time * t + trend.coefficients.chronological_age * a;
        }
        return {
            ...p,
            trendY,
            dateLabel: new Date(p.point_time).toLocaleDateString()
        };
    });

    const preprocessingSeedImage = preview
        ? {
            src: preview,
            fileName: file?.name || result?.filename || 'bone-age-image.png'
        }
        : null;



return (
    <div className={styles.dashboardLayout}>
        {/* 1. 侧边栏：状态清理门卫 */}
        <UserSidebar 
            activeTab={activeTab} 
            setActiveTab={(tab: 'predict' | 'joint-grade' | 'history' | 'community' | 'consultation' | 'settings' | 'preprocessing' | 'bone-age-development') => {
                if (tab !== activeTab) {
                    setError(null);    // 切换瞬间清空报错，防止残留报错锁死 UI
                    setLoading(false); // 强制停止加载动画
                    setActiveTab(tab);
                }
            }} 
            username={username} 
            handleLogout={handleLogout} 
        />

        <main className={styles.mainContent}>
            {/* 顶部标题栏 */}
            <header className={styles.topHeader}>
                <h2>骨龄与发育评估系统 <small className={styles.subVersion}>v2.1</small></h2>
                <button 
                    className={styles.historyBtn} 
                    onClick={() => setShowHistory(!showHistory)}
                >
                    <HistoryIcon size={16} /> 
                    {showHistory ? '收起历史' : '历史记录'}
                </button>
            </header>

            {/* 2. 历史面板：严格的类型保护 */}
            {showHistory && (
                <div className={styles.historyPanel}>
                    <h4>最近评估</h4>
                    <div className={styles.historyList}>
                        {history && history.length > 0 ? (
                            history.map(item => (
                                <div key={item?.id || Math.random()} className={styles.historyItem} onClick={() => restoreHistoryItem?.(item)}>
                                    <div className={styles.historyMeta}>
                                        <span>{item?.timestamp ? new Date(item.timestamp).toLocaleDateString() : '未知'}</span>
                                        <span className={item?.gender === 'male' ? styles.tagMale : styles.tagFemale}>
                                            {item?.gender === 'male' ? '男' : '女'}
                                        </span>
                                    </div>
                                    <div className={styles.historyScore}>
                                        {/* 关键：防止 item.predicted_age_years 为空时崩溃 */}
                                        {(Number(item?.predicted_age_years) || 0).toFixed(1)} 岁
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className={styles.emptyText}>暂无数据</p>
                        )}
                    </div>
                </div>
            )}

            {/* 3. 核心内容渲染区：使用 key 保证物理隔离，防止不同 Tab 间的 State 污染 */}
            <div key={activeTab} className={styles.viewPort}>
                
                {/* --- 骨龄预测 Tab --- */}
                {activeTab === 'predict' && (
                    <PredictTab 
                        {...{
                            file, preview, imageStyle, imgSettings, setImgSettings,
                            handleDrop, fileInputRef, handleFileChange, 
                            loading, gender, setGender, realAge, setRealAge,
                            currentHeight, setCurrentHeight, handleSubmit, error
                        }}
                        // 显式传入并保护 result
                        result={result} 
                        imageSource={predictionImageSource}
                        // 容错处理：确保 coord 必须是 4 位数组，否则不渲染框体
                        getBoxStyle={(coord) => {
                            if (Array.isArray(coord) && coord.length >= 4) {
                                return getBoxStyle(coord);
                            }
                            return { display: 'none' };
                        }}
                        // 容错处理：报告生成异常时不崩溃
                        generateMedicalReport={(data) => {
                            try { return generateMedicalReport(data); }
                            catch (err) { return "报告计算中或数据暂缺..."; }
                        }}
                        generateComparisonData={generateComparisonData}
                        getEvaluation={getEvaluation}
                    />
                )}

                {/* --- 系统设置 Tab --- */}
                {activeTab === 'settings' && (
                    <SettingsTab 
                        username={username} 
                        onUpdateSuccess={() => {
                            console.log('设置已更新');
                        }}
                    />
                )}

                {/* --- 图像预处理 Tab --- */}
                {activeTab === 'preprocessing' && (
                    <ImagePreprocessingTab 
                        username={username} 
                        seedImage={preprocessingSeedImage}
                        onUseInPredict={handleUsePreprocessedImage}
                    />
                )}

                {/* --- 其他页面逻辑 --- */}
                {activeTab === 'history' && (
                    <HistoryTab 
                        {...{
                            pointTime, setPointTime, pointBoneAge, setPointBoneAge,
                            pointChronAge, setPointChronAge, pointNote, setPointNote,
                            addPoint, pointLoading, trend, boneAgePoints, deletePoint,
                            history, restoreHistoryItem, setActiveTab, updatePrediction
                        }}
                        trendData={trendData || []}
                    />
                )}

                {activeTab === 'joint-grade' && (
                    <div className={styles.workspaceGrid}>
                        <div className={styles.resultsCard} style={{ width: '100%', gridColumn: '1 / -1' }}>
                            <h3 style={{ margin: '0 0 1rem 0' }}>小关节分级分析</h3>
                            <JointGradeTab result={jointResult} setResult={setJointResult} />
                        </div>
                    </div>
                )}

                {activeTab === 'consultation' && <ConsultationPage />}
                {activeTab === 'community' && <CommunityPage />}
                {activeTab === 'bone-age-development' && <BoneAgeDevelopmentTab />}
            </div>
        </main>
    </div>
);}
