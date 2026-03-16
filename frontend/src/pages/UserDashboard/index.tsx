import { useState, useRef, useEffect } from 'react';
import { History as HistoryIcon } from 'lucide-react';
import 'katex/dist/katex.min.css';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { normalizePredictionResult, submitPredictionRequest } from '../../lib/prediction';
import { buildAuthHeaders } from '../../lib/api';
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
import HistoryTab from './components/HistoryTab';
import ConsultationPage from '../Consultation';
import CommunityPage from '../Community';

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
    const [activeTab, setActiveTab] = useState<'predict' | 'history' | 'community' | 'consultation'>('predict');
    const [boneAgePoints, setBoneAgePoints] = useState<BoneAgePoint[]>([]);
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

    const imageStyle: React.CSSProperties = {
        filter: imgSettings.usePreprocessing 
            ? `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast * 100}%) invert(${imgSettings.invert ? 100 : 0}%)`
            : `brightness(100%) contrast(100%) invert(${imgSettings.invert ? 100 : 0}%)`,
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
            <UserSidebar 
                activeTab={activeTab} 
                setActiveTab={setActiveTab} 
                username={username} 
                handleLogout={handleLogout} 
            />

            {/* Main Content */}
            <main className={styles.mainContent}>
                <header className={styles.topHeader}>
                    <h2>骨龄与发育评估</h2>
                    <button className={styles.historyBtn} onClick={() => setShowHistory(!showHistory)}>
                        <HistoryIcon size={16} /> {showHistory ? '收起最近记录' : '查看最近记录'}
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
                    <PredictTab 
                        file={file}
                        preview={preview}
                        imageStyle={imageStyle}
                        imgSettings={imgSettings}
                        setImgSettings={setImgSettings}
                        handleDrop={handleDrop}
                        fileInputRef={fileInputRef}
                        handleFileChange={handleFileChange}
                        result={result}
                        loading={loading}
                        gender={gender}
                        setGender={setGender}
                        realAge={realAge}
                        setRealAge={setRealAge}
                        currentHeight={currentHeight}
                        setCurrentHeight={setCurrentHeight}
                        handleSubmit={handleSubmit}
                        error={error}
                        generateComparisonData={generateComparisonData}
                        getEvaluation={getEvaluation}
                        getBoxStyle={getBoxStyle}
                        generateMedicalReport={generateMedicalReport}
                    />
                )}

                {activeTab === 'history' && (
                    <HistoryTab 
                        pointTime={pointTime}
                        setPointTime={setPointTime}
                        pointBoneAge={pointBoneAge}
                        setPointBoneAge={setPointBoneAge}
                        pointChronAge={pointChronAge}
                        setPointChronAge={setPointChronAge}
                        pointNote={pointNote}
                        setPointNote={setPointNote}
                        addPoint={addPoint}
                        pointLoading={pointLoading}
                        trendData={trendData}
                        trend={trend}
                        boneAgePoints={boneAgePoints}
                        deletePoint={deletePoint}
                        history={history}
                        restoreHistoryItem={restoreHistoryItem}
                        setActiveTab={setActiveTab}
                        updatePrediction={updatePrediction}
                    />
                )}
                
                {activeTab === 'consultation' && <ConsultationPage />}
                {activeTab === 'community' && <CommunityPage />}
            </main>
        </div>
    );
}
