import { useState, useRef, useEffect } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import {
    Upload, History, Sun, Moon, Contrast,
    Activity, RotateCcw, BarChart2, FileSpreadsheet, LogOut, User as UserIcon, Trash2, Plus,
    MessageCircle, Send, Bot, HelpCircle
} from 'lucide-react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Scatter, Line
} from 'recharts';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import styles from './UserDashboard.module.css';

// --- Interfaces (Copied from previous App.tsx) ---
interface RusChnDetail {
    name: string;
    stage: number;
    score: number;
}

interface RusChnReport {
    total_score: number;
    details: RusChnDetail[];
    target_score_lookup: number;
}

interface PredictionResult {
    id: string;
    timestamp: number;
    filename: string;
    predicted_age_months: number;
    predicted_age_years: number;
    gender: string;
    real_age_years?: number;
    rus_chn_details?: RusChnReport;
    heatmap_base64?: string;
    detection_image_base64?: string;
    predicted_adult_height?: number;
    joint_detect_13?: {
        hand_side: string;
        detected_count: number;
        plot_image_base64?: string | null;
    };
    anomalies?: Array<{
        type: string;
        score: number;
        coord: number[];
    }>;
}

interface BoneAgePoint {
    id: number;
    user_id: number;
    point_time: number;
    bone_age_years: number;
    chronological_age_years?: number | null;
    source: string;
    prediction_id?: string | null;
    note?: string;
}

interface BoneAgeTrend {
    points: number;
    enough: boolean;
    latex: string;
    r2?: number;
    coefficients?: {
        intercept: number;
        time: number;
        chronological_age: number;
    };
}

interface ImageSettings {
    brightness: number;
    contrast: number;
    invert: boolean;
    scale: number;
}

const DEFAULT_SETTINGS: ImageSettings = {
    brightness: 100,
    contrast: 100,
    invert: false,
    scale: 1
};

import { API_BASE } from '../config';


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

    const [history, setHistory] = useState<PredictionResult[]>([]);
    const [showHistory, setShowHistory] = useState(false);
    const [activeTab, setActiveTab] = useState<'predict' | 'history' | 'community'>('predict');
    const [articles, setArticles] = useState<any[]>([]);
    const [boneAgePoints, setBoneAgePoints] = useState<BoneAgePoint[]>([]);
    const [trend, setTrend] = useState<BoneAgeTrend | null>(null);
    const [pointTime, setPointTime] = useState('');
    const [pointBoneAge, setPointBoneAge] = useState('');
    const [pointChronAge, setPointChronAge] = useState('');
    const [pointNote, setPointNote] = useState('');
    const [pointLoading, setPointLoading] = useState(false);

    // --- Forum (QA) state ---
    const [qaList, setQaList] = useState<any[]>([]);
    const [qaText, setQaText] = useState('');
    const [qaLoading, setQaLoading] = useState(false);
    const [qaSubmitting, setQaSubmitting] = useState(false);
    const [qaImageBase64, setQaImageBase64] = useState<string | null>(null);
    const qaImageInputRef = useRef<HTMLInputElement>(null);

    // --- Smart consultation (AI chat) state ---
    const [consultMessages, setConsultMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
    const [consultInput, setConsultInput] = useState('');
    const [consultLoading, setConsultLoading] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const buildAuthHeaders = (json = false) => {
        const token = localStorage.getItem('boneage_token');
        const headers: Record<string, string> = {};
        if (json) headers['Content-Type'] = 'application/json';
        if (token && !['null', 'undefined', 'none', ''].includes(token.toLowerCase())) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    };

    const fetchArticles = async () => {
        try {
            const resp = await fetch(`${API_BASE}/articles`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setArticles(data.items);
            }
        } catch (e) { console.error('获取文章失败'); }
    };

    const fetchQaList = async () => {
        setQaLoading(true);
        try {
            const resp = await fetch(`${API_BASE}/qa/questions`, {
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                setQaList(data.items || []);
            }
        } catch (e) { console.error('获取问答列表失败', e); }
        finally { setQaLoading(false); }
    };

    const submitQuestion = async () => {
        if (!qaText.trim()) { setError('请输入问题内容'); return; }
        if (!qaImageBase64) { setError('请选择一张影像图片附件'); return; }
        setQaSubmitting(true);
        try {
            const resp = await fetch(`${API_BASE}/qa/questions`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ text: qaText.trim(), image: qaImageBase64 })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || '提问失败');
            setQaText('');
            setQaImageBase64(null);
            await fetchQaList();
        } catch (e: any) { setError(e.message || '提问失败'); }
        finally { setQaSubmitting(false); }
    };

    const deleteQuestion = async (qid: number) => {
        if (!window.confirm('确认删除该提问吗？')) return;
        try {
            const resp = await fetch(`${API_BASE}/qa/questions/${qid}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: buildAuthHeaders()
            });
            if (resp.ok) await fetchQaList();
        } catch (e) { setError('删除失败'); }
    };

    const handleQaImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = (ev) => setQaImageBase64(ev.target?.result as string);
        reader.readAsDataURL(f);
    };

    const sendConsult = async () => {
        const msg = consultInput.trim();
        if (!msg) return;
        setConsultLoading(true);
        setConsultMessages(prev => [...prev, { role: 'user', text: msg }]);
        setConsultInput('');
        try {
            const resp = await fetch(`${API_BASE}/user/ai-consult`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ message: msg })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || 'AI 问诊调用失败');
            setConsultMessages(prev => [...prev, { role: 'assistant', text: data.reply || '未返回内容' }]);
        } catch (e: any) {
            setConsultMessages(prev => [...prev, { role: 'assistant', text: `调用失败：${e.message}` }]);
        } finally { setConsultLoading(false); }
    };

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
        fetchArticles();
        fetchBoneAgePoints();
        fetchBoneAgeTrend();
        fetchQaList();
    }, []);

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const getBoxStyle = (coord: number[]) => {
        const [xc, yc, w, h] = coord;
        return {
            left: `${(xc - w / 2) * 100}%`,
            top: `${(yc - h / 2) * 100}%`,
            width: `${w * 100}%`,
            height: `${h * 100}%`,
            position: 'absolute' as const,
            border: '2px solid red',
            pointerEvents: 'none' as const
        };
    };

    const parseAnomalies = (anomalies: any[] | undefined, threshold = 0.45) => {
        const results = { fractures: [] as any[], foreign_objects: [] as any[] };
        if (!anomalies) return results;
        anomalies.forEach(item => {
            if (item.score < threshold) return;
            if (item.type.includes('fracture')) results.fractures.push(item);
            else if (item.type === 'metal') results.foreign_objects.push(item);
        });
        return results;
    };

    const generateMedicalReport = (data: PredictionResult | null) => {
        if (!data) return "分析中...";
        const { predicted_age_years, gender, anomalies } = data;
        const parsed = parseAnomalies(anomalies, 0.45);

        let report = `【影像学分析报告】\n`;
        report += `1. 基本信息：受检者性别为${gender === 'male' ? '男' : '女'}，`;
        report += `测定骨龄约为 ${predicted_age_years.toFixed(1)} 岁。\n\n`;
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
        const formData = new FormData();
        formData.append('file', file);
        formData.append('gender', gender);
        if (currentHeight) formData.append('height', currentHeight);
        if (realAge) formData.append('real_age_years', realAge);

        try {
            const response = await fetch(`${API_BASE}/predict`, {
                method: 'POST',
                credentials: 'include',
                body: formData,
                headers: buildAuthHeaders()
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.detail || `Prediction failed`);
            }
            const newResult: PredictionResult = {
                ...data,
                id: data.id || Date.now().toString(),
                timestamp: data.timestamp || Date.now(),
                real_age_years: realAge ? parseFloat(realAge) : undefined
            };
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
                const fullItem = data.data as PredictionResult;
                setResult(fullItem);
                setGender(fullItem.gender);
                if (fullItem.real_age_years) setRealAge(fullItem.real_age_years.toString());
                setPreview(null);
                setFile(null);
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
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || '修改失败');
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

    const imageStyle = {
        filter: `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}%) invert(${imgSettings.invert ? 100 : 0}%)`,
        transform: `scale(${imgSettings.scale})`,
        transition: 'filter 0.2s ease, transform 0.2s ease'
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

    return (
        <div className={styles.dashboardLayout}>
            {/* Sidebar Navigation */}
            <aside className={styles.sidebar}>
                <div className={styles.brand}>
                    <Activity size={24} color="#3b82f6" />
                    <span>患者控制台</span>
                </div>

                <nav className={styles.sideNav}>
                    <button className={`${styles.navItem} ${activeTab === 'predict' ? styles.active : ''}`} onClick={() => setActiveTab('predict')}><Activity size={18} /> 预测评估</button>
                    <button className={`${styles.navItem} ${activeTab === 'history' ? styles.active : ''}`} onClick={() => setActiveTab('history')}><History size={18} /> 预测记录</button>
                    <button className={`${styles.navItem} ${activeTab === 'community' ? styles.active : ''}`} onClick={() => setActiveTab('community')}><FileSpreadsheet size={18} /> 社区与科普</button>
                </nav>

                <div className={styles.userProfile}>
                    <div className={styles.userInfo}>
                        <UserIcon size={20} color="#64748b" />
                        <span className={styles.username}>{username}</span>
                    </div>
                    <button onClick={handleLogout} className={styles.logoutBtn} title="退出登录">
                        <LogOut size={16} />
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className={styles.mainContent}>
                <header className={styles.topHeader}>
                    <h2>骨龄与发育评估</h2>
                    <button className={styles.historyBtn} onClick={() => setShowHistory(!showHistory)}>
                        <History size={16} /> {showHistory ? '收起最近记录' : '查看最近记录'}
                    </button>
                </header>

                {showHistory && (
                    <div className={styles.historyPanel}>
                        <h4>最近的评估</h4>
                        <div className={styles.historyList}>
                            {history.length === 0 && <p className={styles.emptyText}>未发现历史记录。</p>}
                            {history.map(item => (
                                <div key={item.id} className={styles.historyItem} onClick={() => restoreHistoryItem(item)}>
                                    <div className={styles.historyMeta}>
                                        <span>{new Date(item.timestamp).toLocaleDateString()}</span>
                                        <span className={item.gender === 'male' ? styles.tagMale : styles.tagFemale}>
                                            {item.gender === 'male' ? '男' : '女'}
                                        </span>
                                    </div>
                                    <div className={styles.historyScore}>
                                        {item.predicted_age_years.toFixed(1)} 岁
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === 'predict' && (
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
                )}

                {activeTab === 'history' && (
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
                )}

                {activeTab === 'community' && (
                    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>

                        {/* ─── 智能问诊区 ─── */}
                        <div className={styles.communityPanel}>
                            <div className={styles.communityPanelHeader}>
                                <Bot size={18} color="#3b82f6" />
                                <h3>智能健康问诊</h3>
                                <span className={styles.aiTag}>AI 驱动</span>
                            </div>
                            <p className={styles.communityDesc}>向 AI 健康顾问咨询骨龄发育、生长规律等问题。AI 提供科普参考，不替代医生诊断。</p>
                            <div className={styles.chatWindow}>
                                {consultMessages.length === 0 && (
                                    <div className={styles.chatEmpty}>
                                        <HelpCircle size={32} color="#cbd5e1" />
                                        <p>输入您的问题，AI 将为您解答骨龄发育相关健康知识。</p>
                                    </div>
                                )}
                                {consultMessages.map((m, idx) => (
                                    <div key={idx} className={`${styles.chatMsg} ${m.role === 'user' ? styles.chatMsgUser : styles.chatMsgAi}`}>
                                        <div className={styles.chatMsgRole}>{m.role === 'user' ? '您' : 'AI 顾问'}</div>
                                        <div className={styles.chatMsgText}>{m.text}</div>
                                    </div>
                                ))}
                            </div>
                            <div className={styles.chatInputRow}>
                                <textarea
                                    className={styles.chatTextarea}
                                    placeholder="例如：孩子骨龄超前一岁需要担心吗？"
                                    value={consultInput}
                                    onChange={e => setConsultInput(e.target.value)}
                                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendConsult(); } }}
                                    rows={2}
                                />
                                <button className={styles.chatSendBtn} onClick={sendConsult} disabled={consultLoading}>
                                    <Send size={16} />{consultLoading ? ' 思考中...' : ' 发送'}
                                </button>
                            </div>
                        </div>

                        {/* ─── 专家科普文章区 ─── */}
                        <div className={styles.communityPanel}>
                            <div className={styles.communityPanelHeader}>
                                <FileSpreadsheet size={18} color="#3b82f6" />
                                <h3>专家健康科普文章</h3>
                            </div>
                            {articles.length === 0 ? (
                                <p className={styles.communityEmpty}>目前平台上医生还未发布相关科普文章。</p>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    {articles.map(article => (
                                        <div key={article.id} className={styles.articleCard}>
                                            <h4 className={styles.articleTitle}>{article.title}</h4>
                                            <p className={styles.articleMeta}>发布者：{article.author_name} 医生 • {new Date(article.created_at).toLocaleDateString()}</p>
                                            <p className={styles.articleContent}>{article.content}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* ─── 问答论坛区 ─── */}
                        <div className={styles.communityPanel}>
                            <div className={styles.communityPanelHeader}>
                                <MessageCircle size={18} color="#3b82f6" />
                                <h3>问答论坛</h3>
                                <button className={styles.refreshSmallBtn} onClick={fetchQaList} disabled={qaLoading}>
                                    刷新
                                </button>
                            </div>
                            <p className={styles.communityDesc}>在此向医生提出专业问题，附上影像以便医生参考，医生将在此页面回复您。</p>

                            {/* 发帖表单 */}
                            <div className={styles.qaForm}>
                                <textarea
                                    className={styles.qaTextarea}
                                    placeholder="描述您的问题，例如：孩子7岁，骨龄测定为8.5岁，是否需要就医？"
                                    value={qaText}
                                    onChange={e => setQaText(e.target.value)}
                                    rows={3}
                                />
                                <div className={styles.qaFormActions}>
                                    <div className={styles.qaImageSelect}>
                                        <input
                                            type="file" accept="image/*" style={{ display: 'none' }}
                                            ref={qaImageInputRef}
                                            onChange={handleQaImageSelect}
                                        />
                                        <button className={styles.qaImageBtn} onClick={() => qaImageInputRef.current?.click()}>
                                            <Upload size={14} /> {qaImageBase64 ? '✅ 已选择图片' : '附上影像'}
                                        </button>
                                        {qaImageBase64 && (
                                            <img src={qaImageBase64} alt="附件预览" className={styles.qaImageThumb} />
                                        )}
                                    </div>
                                    <button
                                        className={styles.qaSubmitBtn}
                                        onClick={submitQuestion}
                                        disabled={qaSubmitting || !qaText.trim() || !qaImageBase64}
                                    >
                                        <Plus size={14} /> {qaSubmitting ? '提交中...' : '提交问题'}
                                    </button>
                                </div>
                            </div>

                            {/* 问题列表 */}
                            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                                {qaLoading && <p className={styles.communityEmpty}>加载中...</p>}
                                {!qaLoading && qaList.length === 0 && (
                                    <p className={styles.communityEmpty}>您还没有提交任何问题。</p>
                                )}
                                {qaList.map(q => (
                                    <div key={q.qid} className={styles.qaCard}>
                                        <div className={styles.qaCardHeader}>
                                            <span className={styles.qaTime}>{new Date(q.createTime).toLocaleString()}</span>
                                            {q.reply ? (
                                                <span className={styles.qaRepliedBadge}>已回复</span>
                                            ) : (
                                                <span className={styles.qaPendingBadge}>待回复</span>
                                            )}
                                            <button className={styles.qaDeleteBtn} onClick={() => deleteQuestion(q.qid)} title="删除">
                                                <Trash2 size={13} />
                                            </button>
                                        </div>
                                        <div className={styles.qaQuestion}>
                                            <strong>我的问题：</strong>{q.text}
                                        </div>
                                        {q.image && (
                                            <img src={q.image} alt="附件" className={styles.qaCardImage} />
                                        )}
                                        {q.reply && (
                                            <div className={styles.qaReply}>
                                                <strong>医生回复：</strong>{q.reply}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>

                    </div>
                )}
            </main>
        </div>
    );
}
