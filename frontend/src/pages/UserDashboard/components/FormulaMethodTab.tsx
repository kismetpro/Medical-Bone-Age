import React, { useState, useRef, useMemo, useCallback } from 'react';
import { 
    Upload, Moon, Sun, Contrast, RotateCcw, Calculator, 
    CheckCircle, AlertCircle, Info, RefreshCw, MousePointer2, Edit3 
} from 'lucide-react';
import { 
    ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar, Cell 
} from 'recharts';
import styles from '../UserDashboard.module.css';
import type { PredictionResult, ImageSettings } from '../types';
import { DEFAULT_SETTINGS } from '../types';
import { detectJoints, predictBoneAgeByFormula } from '../../../lib/api';
import type { PatientUser } from '../../DoctorDashboard/types';

interface JointBox {
    id: string;
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
    bboxSpace?: 'original' | 'resized';
    grade?: number;
    score?: number;
    status?: 'ok' | 'pending' | 'error';
}

interface FormulaMethodTabProps {
    result: PredictionResult | null;
    setResult?: (result: PredictionResult | null) => void;
    patientUsers?: PatientUser[];
    patientsLoading?: boolean;
    targetUserId?: string;
    setTargetUserId?: (id: string) => void;
}

// RUS-CHN 小关节定义（13个关键关节，匹配后端命名）
const RUS_JOINTS = [
    { id: 'Radius', name: '桡骨 (Radius)', color: '#3b82f6' },
    { id: 'Ulna', name: '尺骨 (Ulna)', color: '#8b5cf6' },
    { id: 'MCPFirst', name: '第一掌骨 (MCP1)', color: '#ec4899' },
    { id: 'MCPThird', name: '第三掌骨 (MCP3)', color: '#f59e0b' },
    { id: 'MCPFifth', name: '第五掌骨 (MCP5)', color: '#10b981' },
    { id: 'PIPFirst', name: '第一近节 (PIP1)', color: '#06b6d4' },
    { id: 'PIPThird', name: '第三近节 (PIP3)', color: '#f97316' },
    { id: 'PIPFifth', name: '第五近节 (PIP5)', color: '#6366f1' },
    { id: 'MIPThird', name: '第三中节 (MIP3)', color: '#14b8a6' },
    { id: 'MIPFifth', name: '第五中节 (MIP5)', color: '#a855f7' },
    { id: 'DIPFirst', name: '第一远节 (DIP1)', color: '#e11d48' },
    { id: 'DIPThird', name: '第三远节 (DIP3)', color: '#0891b2' },
    { id: 'DIPFifth', name: '第五远节 (DIP5)', color: '#7c3aed' }
];

// RUS-CHN 骨龄计算公式（匹配后端实现）
const RUS_CHN_FORMULA = {
    name: 'RUS-CHN 骨龄评估公式',
    description: '基于13个关键小关节的成熟度评分计算骨龄，使用RUS-CHN标准',
    formula: '等待后端返回...',
    totalScore: 0,
    boneAge: 0,
    confidence: 0
};

// RUS-CHN 公式表达式（匹配后端 rus_chn.py）
const getRUSCHNFormula = (gender: 'male' | 'female') => {
    if (gender === 'male') {
        return '骨龄 = 2.018 + (-0.093)×S + 0.0033×S² + (-3.33×10⁻⁵)×S³ + 1.76×10⁻⁷×S⁴ + (-5.60×10⁻¹⁰)×S⁵ + 1.13×10⁻¹²×S⁶ + (-1.45×10⁻¹⁵)×S⁷ + 1.15×10⁻¹⁸×S⁸ + (-5.16×10⁻²²)×S⁹ + 9.94×10⁻²⁶×S¹⁰';
    } else {
        return '骨龄 = 5.812 + (-0.272)×S + 0.0053×S² + (-4.38×10⁻⁵)×S³ + 2.09×10⁻⁷×S⁴ + (-6.22×10⁻¹⁰)×S⁵ + 1.20×10⁻¹²×S⁶ + (-1.49×10⁻¹⁵)×S⁷ + 1.16×10⁻¹⁸×S⁸ + (-5.13×10⁻²²)×S⁹ + 9.79×10⁻²⁶×S¹⁰';
    }
};

const roundCoord = (value: number) => (
    Number.isFinite(value) ? Math.round(value) : 0
);

const FormulaMethodTab: React.FC<FormulaMethodTabProps> = ({ 
    setResult,
    patientUsers = [], patientsLoading = false,
    targetUserId = '', setTargetUserId
}) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [gender, setGender] = useState<'male' | 'female'>('male');
    const [realAge, setRealAge] = useState('');
    const [currentHeight, setCurrentHeight] = useState('');
    const [imgSettings, setImgSettings] = useState<ImageSettings>(DEFAULT_SETTINGS);
    const [jointBoxes, setJointBoxes] = useState<JointBox[]>([]);
    const [selectedJoint, setSelectedJoint] = useState<string | null>(null);
    const [showFormula, setShowFormula] = useState(true);
    const [formulaResult, setFormulaResult] = useState(RUS_CHN_FORMULA);
    const [detectionMode, setDetectionMode] = useState<'auto' | 'manual'>('auto');
    const [isDrawing, setIsDrawing] = useState(false);
    const [currentJointIndex, setCurrentJointIndex] = useState(0);
    const [drawingStart, setDrawingStart] = useState<{ x: number; y: number } | null>(null);
    const [drawingEnd, setDrawingEnd] = useState<{ x: number; y: number } | null>(null);
    const [autoPlotImage, setAutoPlotImage] = useState<string | null>(null);
    const [imageNaturalSize, setImageNaturalSize] = useState<{ width: number; height: number } | null>(null);
    
    const fileInputRef = useRef<HTMLInputElement>(null);
    const imageFrameRef = useRef<HTMLDivElement>(null);
    const previewImageRef = useRef<HTMLImageElement>(null);

    const imageStyle = useMemo(() => ({
        filter: `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}) ${imgSettings.invert ? 'invert(1)' : ''}`,
        display: 'block',
        maxWidth: '100%',
        borderRadius: '8px',
        transition: 'filter 0.2s ease'
    }), [imgSettings]);

    const imageFrameStyle = useMemo<React.CSSProperties>(() => ({
        position: 'relative',
        display: 'inline-block',
        lineHeight: 0,
        transform: `scale(${imgSettings.scale / 100})`,
        transformOrigin: 'center center',
        transition: 'transform 0.2s ease',
    }), [imgSettings.scale]);

    const resetDetectionState = useCallback(() => {
        setJointBoxes([]);
        setSelectedJoint(null);
        setAutoPlotImage(null);
        setFormulaResult(RUS_CHN_FORMULA);
        setCurrentJointIndex(0);
        setDrawingStart(null);
        setDrawingEnd(null);
        setIsDrawing(false);
        setImageNaturalSize(null);
    }, []);

    const handlePreviewImageLoad = useCallback((event: React.SyntheticEvent<HTMLImageElement>) => {
        const image = event.currentTarget;
        if (image.naturalWidth > 0 && image.naturalHeight > 0) {
            setImageNaturalSize({
                width: image.naturalWidth,
                height: image.naturalHeight,
            });
        }
    }, []);

    const getImageFrameMetrics = useCallback(() => {
        const imageFrame = imageFrameRef.current;
        const image = previewImageRef.current;
        if (!imageFrame || !image) return null;

        const rect = imageFrame.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return null;

        return {
            rect,
            naturalWidth: image.naturalWidth || rect.width,
            naturalHeight: image.naturalHeight || rect.height,
        };
    }, []);

    const getRelativePoint = useCallback((
        clientX: number,
        clientY: number,
        clampToImage = false,
    ) => {
        const metrics = getImageFrameMetrics();
        if (!metrics) return null;

        let x = clientX - metrics.rect.left;
        let y = clientY - metrics.rect.top;

        if (clampToImage) {
            x = Math.max(0, Math.min(metrics.rect.width, x));
            y = Math.max(0, Math.min(metrics.rect.height, y));
        } else if (x < 0 || y < 0 || x > metrics.rect.width || y > metrics.rect.height) {
            return null;
        }

        return {
            x,
            y,
            displayWidth: metrics.rect.width,
            displayHeight: metrics.rect.height,
            naturalWidth: metrics.naturalWidth,
            naturalHeight: metrics.naturalHeight,
        };
    }, [getImageFrameMetrics]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            resetDetectionState();
            const reader = new FileReader();
            reader.onload = (ev) => {
                setPreview(ev.target?.result as string);
            };
            reader.readAsDataURL(selectedFile);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            setFile(droppedFile);
            resetDetectionState();
            const reader = new FileReader();
            reader.onload = (ev) => {
                setPreview(ev.target?.result as string);
            };
            reader.readAsDataURL(droppedFile);
        }
    };

    // 手动绘制关节框
    const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (detectionMode !== 'manual') return;
        
        // 阻止事件冒泡，避免触发其他点击事件
        e.preventDefault();
        e.stopPropagation();

        const point = getRelativePoint(e.clientX, e.clientY);
        if (!point) return;
        
        setIsDrawing(true);
        setDrawingStart({ x: point.x, y: point.y });
        setDrawingEnd({ x: point.x, y: point.y });
    }, [detectionMode, getRelativePoint]);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (!isDrawing || !drawingStart) return;
        
        e.preventDefault();

        const point = getRelativePoint(e.clientX, e.clientY, true);
        if (!point) return;
        
        // 更新绘制终点，用于显示临时框
        setDrawingEnd({ x: point.x, y: point.y });
    }, [drawingStart, getRelativePoint, isDrawing]);

    const handleMouseUp = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (!isDrawing || !drawingStart) return;
        
        e.preventDefault();
        e.stopPropagation();

        const point = getRelativePoint(e.clientX, e.clientY, true);
        if (!point) {
            setIsDrawing(false);
            setDrawingStart(null);
            setDrawingEnd(null);
            return;
        }
        
        // 计算框的坐标和尺寸
        const boxX = Math.min(drawingStart.x, point.x);
        const boxY = Math.min(drawingStart.y, point.y);
        const boxWidth = Math.abs(point.x - drawingStart.x);
        const boxHeight = Math.abs(point.y - drawingStart.y);
        
        // 只有当框足够大时才添加
        if (boxWidth > 10 && boxHeight > 10 && currentJointIndex < RUS_JOINTS.length) {
            const jointInfo = RUS_JOINTS[currentJointIndex];
            const newJoint: JointBox = {
                id: jointInfo.id,
                name: jointInfo.name,
                x: roundCoord((boxX / point.displayWidth) * point.naturalWidth),
                y: roundCoord((boxY / point.displayHeight) * point.naturalHeight),
                width: roundCoord((boxWidth / point.displayWidth) * point.naturalWidth),
                height: roundCoord((boxHeight / point.displayHeight) * point.naturalHeight),
                bboxSpace: 'original',
                status: 'pending'
            };
            
            setJointBoxes(prev => [...prev, newJoint]);
            
            // 移动到下一个关节
            if (currentJointIndex < RUS_JOINTS.length - 1) {
                setCurrentJointIndex(prev => prev + 1);
            }
        }
        
        // 重置绘制状态
        setIsDrawing(false);
        setDrawingStart(null);
        setDrawingEnd(null);
    }, [currentJointIndex, drawingStart, getRelativePoint, isDrawing]);

    // 删除指定的关节框
    const deleteJointBox = (jointId: string) => {
        const deletedJoint = jointBoxes.find(j => j.id === jointId);
        if (deletedJoint) {
            // 找到被删除关节在RUS_JOINTS中的索引
            const deletedIndex = RUS_JOINTS.findIndex(j => j.id === jointId);
            // 重置当前关节索引到被删除的关节，以便重新绘制
            if (deletedIndex !== -1) {
                setCurrentJointIndex(deletedIndex);
            }
        }
        setJointBoxes(prev => prev.filter(j => j.id !== jointId));
    };

    // 清除所有手动绘制的关节框
    const clearManualJoints = () => {
        setJointBoxes([]);
        setAutoPlotImage(null);
        setSelectedJoint(null);
        setCurrentJointIndex(0);
        setFormulaResult(RUS_CHN_FORMULA);
    };

    const autoDetectJoints = async () => {
        if (!file || !preview) {
            setError('请先上传 X 光影像图片');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const data = await detectJoints(
                file, 
                gender, 
                realAge, 
                imgSettings.usePreprocessing,
                imgSettings.brightness - 100,
                imgSettings.contrast
            );
            
            const detectedJoints: JointBox[] = (data.joints || []).map((joint: any) => {
                const bbox = joint.bbox && Array.isArray(joint.bbox) ? joint.bbox : [0, 0, 0, 0];
                return {
                    id: joint.id,
                    name: joint.name,
                    x: bbox[0] || 0,
                    y: bbox[1] || 0,
                    width: (bbox[2] || 0) - (bbox[0] || 0),
                    height: (bbox[3] || 0) - (bbox[1] || 0),
                    bboxSpace: joint.bboxSpace || 'original',
                    grade: joint.grade,
                    score: joint.score,
                    status: joint.status || 'ok'
                };
            });

            setJointBoxes(detectedJoints);
            
            if (data.plot_image_base64) {
                setAutoPlotImage(data.plot_image_base64);
            }
            
            await calculateFormulaResult(detectedJoints);
            
        } catch (err: any) {
            setError(err.message || '小关节检测失败，请检查网络或影像质量');
        } finally {
            setLoading(false);
        }
    };

    // 调用后端小关节分级模型
    const gradeJoints = async () => {
        if (jointBoxes.length === 0) {
            setError('请先检测或手动划分小关节框');
            return;
        }

        // 直接调用公式计算，它会处理分级和计算
        await calculateFormulaResult(jointBoxes);
    };

    // 计算公式结果（调用后端API）
    const calculateFormulaResult = async (joints: JointBox[]) => {
        if (joints.length === 0) {
            setFormulaResult(RUS_CHN_FORMULA);
            return;
        }

        setLoading(true);
        try {
            const data = await predictBoneAgeByFormula(file!, gender, realAge || '0', joints);

            setFormulaResult({
                name: data.formula_name || 'RUS-CHN 骨龄评估公式',
                description: data.formula_description || '基于13个关键小关节的成熟度评分计算骨龄，使用RUS-CHN标准',
                formula: data.formula_expression || getRUSCHNFormula(gender),
                totalScore: data.total_score || 0,
                boneAge: data.bone_age || 0,
                confidence: data.confidence || 0
            });

            // 更新关节框的分级结果
            const gradedJoints: JointBox[] = joints.map((joint): JointBox => {
                // joint_grades 是一个对象，不是数组
                const graded = data.joint_grades && typeof data.joint_grades === 'object' 
                    ? data.joint_grades[joint.id] 
                    : null;
                return {
                    ...joint,
                    grade: graded?.grade_raw,
                    score: graded?.score || 1.0,
                    status: graded ? 'ok' : 'pending',
                };
            });

            setJointBoxes(gradedJoints);

            // 生成完整的预测结果
            const newResult: PredictionResult = {
                ...data,
                id: data.id || `formula-${Date.now()}`,
                timestamp: Date.now(),
                filename: file?.name || 'unknown',
                gender,
                predicted_age_years: data.bone_age || 0,
                predicted_age_months: (data.bone_age || 0) * 12,
                joint_grades: gradedJoints.reduce((acc, joint) => {
                    acc[joint.id] = {
                        model_joint: joint.id,
                        grade_idx: joint.grade,
                        grade_raw: joint.grade,
                        score: joint.score,
                        status: joint.status
                    };
                    return acc;
                }, {} as any)
            };
            
            if (setResult) setResult(newResult);

        } catch (err: any) {
            console.error('公式计算失败:', err);
            setError(err.message || '公式计算失败，请检查网络或关节框数据');
        } finally {
            setLoading(false);
        }
    };

    // 图表数据
    const chartData = useMemo(() => {
        if (jointBoxes.length === 0) return [];
        return jointBoxes
            .filter(j => j.status === 'ok' && j.grade !== undefined && j.grade !== null)
            .map(joint => {
                const jointInfo = RUS_JOINTS.find(rj => rj.id === joint.id);
                return {
                    joint: joint.name,
                    grade: joint.grade || 0,
                    score: Math.round((joint.score || 0) * 100),
                    color: jointInfo?.color || '#3b82f6'
                };
            })
            .sort((a, b) => (b.grade || 0) - (a.grade || 0));
    }, [jointBoxes]);

    const getBoxStyle = (joint: JointBox): React.CSSProperties => {
        if (!imageNaturalSize) {
            return { display: 'none' };
        }

        const jointInfo = RUS_JOINTS.find(rj => rj.id === joint.id);
        const isSelected = selectedJoint === joint.id;
        const baseWidth = joint.bboxSpace === 'resized' ? 1024 : imageNaturalSize.width;
        const baseHeight = joint.bboxSpace === 'resized' ? 1024 : imageNaturalSize.height;
        
        return {
            position: 'absolute',
            left: `${(joint.x / baseWidth) * 100}%`,
            top: `${(joint.y / baseHeight) * 100}%`,
            width: `${(joint.width / baseWidth) * 100}%`,
            height: `${(joint.height / baseHeight) * 100}%`,
            border: `3px solid ${jointInfo?.color || '#3b82f6'}`,
            backgroundColor: `${jointInfo?.color || '#3b82f6'}20`,
            borderRadius: '4px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: isSelected ? `0 0 0 4px ${jointInfo?.color || '#3b82f6'}40` : 'none',
            zIndex: isSelected ? 10 : 1
        };
    };

    return (
        <div className={styles.workspaceGrid}>
            {/* 左侧：操作面板 */}
            <div className={styles.uploadCard}>
                <div className={styles.cardHeader}>
                    <h3>公式法预测骨龄</h3>
                    {preview && (
                        <div className={styles.imageToolbar}>
                            <button title="降低亮度" onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness - 10 })}><Moon size={14} /></button>
                            <button title="增加亮度" onClick={() => setImgSettings({ ...imgSettings, brightness: imgSettings.brightness + 10 })}><Sun size={14} /></button>
                            <button title="反相模式" onClick={() => setImgSettings({ ...imgSettings, invert: !imgSettings.invert })} className={imgSettings.invert ? styles.activeTool : ''}><Contrast size={14} /></button>
                            <button title="重置" onClick={() => setImgSettings(DEFAULT_SETTINGS)}><RotateCcw size={14} /></button>
                        </div>
                    )}
                </div>

                {patientUsers.length > 0 && (
                    <div className={styles.formGroup} style={{ padding: '0.5rem 1rem', borderBottom: '1px solid #e2e8f0' }}>
                        <label style={{ marginBottom: '0.5rem', display: 'block' }}>选择患者</label>
                        <select 
                            className={styles.formInput}
                            value={targetUserId}
                            onChange={(e) => setTargetUserId?.(e.target.value)}
                            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}
                        >
                            <option value="">{patientsLoading ? '加载中...' : '请选择患者'}</option>
                            {patientUsers.map((patient) => (
                                <option key={patient.id} value={patient.id}>
                                    {patient.username} (UID: {patient.id})
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                <div
                    className={`${styles.uploadArea} ${!file && !preview ? styles.empty : ''}`}
                    onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={handleDrop}
                    onClick={() => {
                        // 只有在空状态下才触发文件选择
                        if (!file && !preview) {
                            fileInputRef.current?.click();
                        }
                    }}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={() => {
                        if (isDrawing) setIsDrawing(false);
                    }}
                >
                    {preview ? (
                        <div className={styles.previewContainer} style={{ position: 'relative' }}>
                            {/* 手动模式提示 */}
                            {detectionMode === 'manual' && (
                                <div style={{
                                    position: 'absolute',
                                    top: '10px',
                                    left: '10px',
                                    background: 'rgba(59, 130, 246, 0.9)',
                                    color: 'white',
                                    padding: '8px 12px',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    zIndex: 100,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}>
                                    <MousePointer2 size={16} />
                                    <span>当前绘制: {RUS_JOINTS[currentJointIndex]?.name || '完成'}</span>
                                    <span style={{ fontSize: '12px', opacity: 0.8 }}>
                                        ({currentJointIndex + 1}/{RUS_JOINTS.length})
                                    </span>
                                </div>
                            )}

                            <div ref={imageFrameRef} style={imageFrameStyle}>
                                <img 
                                    ref={previewImageRef}
                                    src={(detectionMode === 'auto' && autoPlotImage) ? autoPlotImage : preview} 
                                    alt="X-Ray" 
                                    className={styles.previewImage} 
                                    style={(detectionMode === 'auto' && autoPlotImage)
                                        ? { display: 'block', maxWidth: '100%', borderRadius: '8px' }
                                        : imageStyle}
                                    onLoad={handlePreviewImageLoad}
                                />
                                
                                {/* 临时绘制框 */}
                                {isDrawing && drawingStart && drawingEnd && (
                                    <div style={{
                                        position: 'absolute',
                                        left: `${Math.min(drawingStart.x, drawingEnd.x)}px`,
                                        top: `${Math.min(drawingStart.y, drawingEnd.y)}px`,
                                        width: `${Math.abs(drawingEnd.x - drawingStart.x)}px`,
                                        height: `${Math.abs(drawingEnd.y - drawingStart.y)}px`,
                                        border: '2px dashed #3b82f6',
                                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                        borderRadius: '4px',
                                        pointerEvents: 'none',
                                        zIndex: 50
                                    }} />
                                )}
                                
                                {/* 显示关节框 */}
                                {(!autoPlotImage || detectionMode === 'manual') && jointBoxes.map(joint => (
                                    <div
                                        key={joint.id}
                                        style={getBoxStyle(joint)}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            setSelectedJoint(joint.id === selectedJoint ? null : joint.id);
                                        }}
                                        title={`${joint.name} - 等级: ${joint.grade !== undefined && joint.grade !== null ? joint.grade : 'N/A'}`}
                                    >
                                        <span style={{
                                            position: 'absolute',
                                            top: '-24px',
                                            left: '0',
                                            background: joint.status === 'ok' ? '#22c55e' : joint.status === 'pending' ? '#f59e0b' : '#ef4444',
                                            color: 'white',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            fontSize: '12px',
                                            fontWeight: 'bold',
                                            whiteSpace: 'nowrap'
                                        }}>
                                            {joint.name}
                                        </span>
                                        {(joint.grade !== undefined && joint.grade !== null) && (
                                            <span style={{
                                                position: 'absolute',
                                                bottom: '-24px',
                                                right: '0',
                                                background: '#3b82f6',
                                                color: 'white',
                                                padding: '2px 6px',
                                                borderRadius: '4px',
                                                fontSize: '12px',
                                                fontWeight: 'bold'
                                            }}>
                                                等级: {joint.grade}
                                            </span>
                                        )}
                                        {/* 删除按钮 */}
                                        {detectionMode === 'manual' && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    deleteJointBox(joint.id);
                                                }}
                                                style={{
                                                    position: 'absolute',
                                                    top: '-10px',
                                                    right: '-10px',
                                                    background: '#ef4444',
                                                    color: 'white',
                                                    border: 'none',
                                                    borderRadius: '50%',
                                                    width: '20px',
                                                    height: '20px',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    fontSize: '12px',
                                                    fontWeight: 'bold'
                                                }}
                                            >
                                                ×
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>
                            
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
                                <p>提升低对比度影像的识别率</p>
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

                    <div className={styles.modeSwitchCard}>
                        <label>关节检测模式</label>
                        <div className={styles.radioGroup}>
                            <button 
                                className={detectionMode === 'auto' ? styles.btnActive : ''} 
                                onClick={() => {
                                    setDetectionMode('auto');
                                    setCurrentJointIndex(0);
                                }}
                            >
                                <RefreshCw size={16} style={{ marginRight: '4px' }} />
                                自动检测
                            </button>
                            <button 
                                className={detectionMode === 'manual' ? styles.btnActive : ''} 
                                onClick={() => {
                                    setDetectionMode('manual');
                                    setCurrentJointIndex(0);
                                }}
                            >
                                <Edit3 size={16} style={{ marginRight: '4px' }} />
                                手动绘制
                            </button>
                        </div>
                    </div>

                    <div className={styles.actionButtons}>
                        {detectionMode === 'auto' ? (
                            <button 
                                className={styles.btnPrimary}
                                onClick={autoDetectJoints}
                                disabled={loading || !file}
                            >
                                {loading ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                                自动检测小关节
                            </button>
                        ) : (
                            <>
                                <button 
                                    className={styles.btnPrimary}
                                    onClick={gradeJoints}
                                    disabled={loading || jointBoxes.length === 0}
                                >
                                    {loading ? <RefreshCw size={16} className="animate-spin" /> : <Calculator size={16} />}
                                    计算骨龄
                                </button>
                                <button 
                                    className={styles.btnSecondary}
                                    onClick={clearManualJoints}
                                    disabled={jointBoxes.length === 0}
                                >
                                    清除关节框
                                </button>
                            </>
                        )}
                    </div>

                    {error && (
                        <div className={styles.errorMessage} style={{ marginTop: '1rem', padding: '0.75rem', background: '#fee2e2', border: '1px solid #fecaca', borderRadius: '8px', color: '#991b1b' }}>
                            <AlertCircle size={16} style={{ marginRight: '0.5rem' }} />
                            {error}
                        </div>
                    )}
                </div>
            </div>

            {/* 右侧：结果展示 */}
            <div className={styles.resultsCard}>
                <div className={styles.cardHeader}>
                    <h3>预测结果</h3>
                    <button 
                        onClick={() => setShowFormula(!showFormula)}
                        className={styles.iconButton}
                        title={showFormula ? '隐藏公式' : '显示公式'}
                    >
                        <Info size={18} />
                    </button>
                </div>

                {/* 公式显示区域 */}
                {showFormula && (
                    <div className={styles.formulaCard}>
                        <div className={styles.formulaHeader}>
                            <Calculator size={20} />
                            <h4>RUS-CHN 骨龄评估公式</h4>
                        </div>
                        <div className={styles.formulaContent}>
                            <div className={styles.formulaItem}>
                                <label>公式名称：</label>
                                <span className={styles.formulaValue}>{formulaResult.name}</span>
                            </div>
                            <div className={styles.formulaItem}>
                                <label>计算公式：</label>
                                <div className={styles.formulaMath}>
                                    <code>{formulaResult.formula}</code>
                                </div>
                            </div>
                            <div className={styles.formulaItem}>
                                <label>总成熟度评分：</label>
                                <span className={styles.formulaValue}>{formulaResult.totalScore.toFixed(2)}</span>
                            </div>
                            <div className={styles.formulaItem}>
                                <label>实际年龄：</label>
                                <span className={styles.formulaValue}>{realAge || '未提供'} 岁</span>
                            </div>
                            <div className={styles.formulaItem}>
                                <label>计算骨龄：</label>
                                <span className={styles.formulaValue} style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>
                                    {formulaResult.boneAge.toFixed(2)} 岁
                                </span>
                            </div>
                        </div>
                        <div className={styles.formulaDescription}>
                            <Info size={16} style={{ marginRight: '0.5rem', color: '#3b82f6' }} />
                            <span>
                                {formulaResult.description}
                                S表示总成熟度评分，基于13个关键小关节的分级结果计算。
                            </span>
                        </div>
                    </div>
                )}

                {/* 小关节分级结果 */}
                {jointBoxes.length > 0 && (
                    <div className={styles.jointsCard}>
                        <div className={styles.cardHeader}>
                            <h4>小关节分级结果 ({jointBoxes.length})</h4>
                            <button 
                                onClick={() => setJointBoxes([])}
                                className={styles.iconButton}
                                title="清除关节框"
                            >
                                <RefreshCw size={16} />
                            </button>
                        </div>
                        
                        <div className={styles.jointsList}>
                            {jointBoxes.map(joint => {
                                const jointInfo = RUS_JOINTS.find(rj => rj.id === joint.id);
                                return (
                                    <div 
                                        key={joint.id}
                                        className={`${styles.jointItem} ${selectedJoint === joint.id ? styles.selected : ''}`}
                                        onClick={() => setSelectedJoint(joint.id === selectedJoint ? null : joint.id)}
                                    >
                                        <div className={styles.jointHeader}>
                                            <div className={styles.jointName}>
                                                <div 
                                                    className={styles.jointColor} 
                                                    style={{ background: jointInfo?.color || '#3b82f6' }}
                                                />
                                                <span>{joint.name}</span>
                                            </div>
                                            <div className={styles.jointStatus}>
                                                {joint.status === 'ok' ? (
                                                    <CheckCircle size={16} color="#22c55e" />
                                                ) : (
                                                    <AlertCircle size={16} color="#ef4444" />
                                                )}
                                            </div>
                                        </div>
                                        <div className={styles.jointDetails}>
                                            <div className={styles.jointDetail}>
                                                <span className={styles.detailLabel}>等级：</span>
                                                <span className={styles.detailValue}>{joint.grade !== undefined && joint.grade !== null ? joint.grade : 'N/A'}</span>
                                            </div>
                                            <div className={styles.jointDetail}>
                                                <span className={styles.detailLabel}>置信度：</span>
                                                <span className={styles.detailValue}>
                                                    {joint.score !== undefined && joint.score !== null ? `${(joint.score * 100).toFixed(1)}%` : 'N/A'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* 图表展示 */}
                {chartData.length > 0 && (
                    <div className={styles.chartCard}>
                        <h4>小关节分级分布</h4>
                        <div style={{ height: '300px' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="joint" angle={-45} textAnchor="end" height={100} />
                                    <YAxis />
                                    <Tooltip />
                                    <Bar dataKey="grade" name="等级">
                                        {chartData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* 加载状态 */}
                {loading && (
                    <div className={styles.loadingOverlay}>
                        <div className={styles.loadingSpinner} />
                        <p>正在分析中...</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default FormulaMethodTab;
