import type { CSSProperties, ChangeEvent, Dispatch, DragEvent, RefObject, SetStateAction } from 'react';
import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../../../config';
import { buildAuthHeaders } from '../../../lib/api';
import { dataUrlToFile } from '../../../lib/imagePreprocessing';
import {
  getHighConfidenceFractures,
  normalizePredictionResult,
  resolveForeignObjectDetection,
  submitPredictionRequest,
} from '../../../lib/prediction';
import { DEFAULT_SETTINGS } from '../types';
import type { ImageSettings, PredictionResult } from '../types';

type PredictionImageSource = 'upload' | 'preprocessing' | 'history' | null;

interface UsePredictionWorkspaceOptions {
  onPredictionSaved?: () => Promise<void> | void;
  onHistoryRestored?: () => void;
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export interface UsePredictionWorkspaceReturn {
  file: File | null;
  preview: string | null;
  gender: string;
  realAge: string;
  currentHeight: string;
  loading: boolean;
  result: PredictionResult | null;
  error: string | null;
  imgSettings: ImageSettings;
  imageStyle: CSSProperties;
  predictionImageSource: PredictionImageSource;
  fileInputRef: RefObject<HTMLInputElement | null>;
  preprocessingSeedImage: { src: string; fileName: string } | null;
  setGender: (value: string) => void;
  setRealAge: (value: string) => void;
  setCurrentHeight: (value: string) => void;
  setImgSettings: Dispatch<SetStateAction<ImageSettings>>;
  handleFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  handleDrop: (event: DragEvent<HTMLDivElement>) => void;
  handleSubmit: () => Promise<void>;
  restoreHistoryItem: (item: Partial<PredictionResult>) => Promise<void>;
  handleUsePreprocessedImage: (payload: { dataUrl: string; fileName: string }) => void;
  generateComparisonData: (res: PredictionResult) => Array<{ name: string; age: number; fill: string }>;
  getEvaluation: (boneAge: number, chronoAge: number) => { status: string; color: string; desc: string };
  getBoxStyle: (coord: number[]) => CSSProperties;
  generateMedicalReport: (data: PredictionResult | null) => string;
  clearTransientStatus: () => void;
}

export function usePredictionWorkspace({
  onPredictionSaved,
  onHistoryRestored,
}: UsePredictionWorkspaceOptions = {}): UsePredictionWorkspaceReturn {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [gender, setGender] = useState('male');
  const [realAge, setRealAge] = useState('');
  const [currentHeight, setCurrentHeight] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imgSettings, setImgSettings] = useState<ImageSettings>(DEFAULT_SETTINGS);
  const [predictionImageSource, setPredictionImageSource] = useState<PredictionImageSource>(null);

  const replacePreview = (nextPreview: string | null) => {
    if (previewUrlRef.current?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrlRef.current);
    }

    previewUrlRef.current = nextPreview;
    setPreview(nextPreview);
  };

  useEffect(() => () => {
    if (previewUrlRef.current?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrlRef.current);
    }
  }, []);

  const clearTransientStatus = () => {
    setError(null);
    setLoading(false);
  };

  const getBoxStyle = (coord: number[]): CSSProperties => {
    const [xc, yc, width, height] = coord;
    return {
      left: `${(xc - width / 2) * 100}%`,
      top: `${(yc - height / 2) * 100}%`,
      width: `${width * 100}%`,
      height: `${height * 100}%`,
      position: 'absolute',
      border: '2px solid red',
      pointerEvents: 'none',
    };
  };

  const getEvaluation = (boneAge: number, chronoAge: number) => {
    const diff = boneAge - chronoAge;
    if (diff > 1) {
      return { status: '早熟 (Advanced)', color: '#ef4444', desc: '骨龄显著大于生活年龄' };
    }
    if (diff < -1) {
      return { status: '晚熟 (Delayed)', color: '#3b82f6', desc: '骨龄显著小于生活年龄' };
    }
    return { status: '正常 (Normal)', color: '#22c55e', desc: '骨龄与生活年龄基本一致' };
  };

  const parseAnomalies = (data: PredictionResult | null) => ({
    fractures: getHighConfidenceFractures(data?.anomalies),
    foreignObjects: resolveForeignObjectDetection(data).items,
  });

  const generateMedicalReport = (data: PredictionResult | null) => {
    if (!data) {
      return '分析中...';
    }

    const { predicted_age_years, gender: patientGender } = data;
    const parsed = parseAnomalies(data);
    let report = '【影像学分析报告】\n';
    report += `1. 基本信息：受检者性别为${patientGender === 'male' ? '男' : '女'}，`;
    report += `测定骨龄约为 ${predicted_age_years.toFixed(1)} 岁。\n\n`;
    report += '2. 影像发现：\n';

    if (parsed.fractures.length > 0) {
      report += `   - [警告] 在影像中识别到 ${parsed.fractures.length} 处疑似骨折区域。建议临床结合压痛点进一步核实。\n`;
    } else {
      report += '   - 骨骼连续性尚好，未见明显骨折征象。\n';
    }

    if (parsed.foreignObjects.length > 0) {
      report += `   - 注意：影像中存在 ${parsed.foreignObjects.length} 处高密度异物，可能影响骨龄判断。\n`;
    }

    report += '\n3. 结论建议：\n';
    report += parsed.fractures.length > 0
      ? '   结论：疑似存在外伤性改变。'
      : '   结论：骨龄发育符合当前生理阶段。';
    return report;
  };

  const loadFile = (selectedFile: File, source: PredictionImageSource = 'upload') => {
    setFile(selectedFile);
    replacePreview(URL.createObjectURL(selectedFile));
    setResult(null);
    setError(null);
    setImgSettings(DEFAULT_SETTINGS);
    setPredictionImageSource(source);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      loadFile(selectedFile, 'upload');
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const droppedFile = event.dataTransfer.files?.[0];
    if (droppedFile) {
      loadFile(droppedFile, 'upload');
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      return;
    }

    setLoading(true);
    setError(null);

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

      const nextResult = normalizePredictionResult<PredictionResult>(data as Record<string, unknown>, realAge);
      setResult(nextResult);
      await onPredictionSaved?.();
    } catch (errorValue) {
      setError(`预测失败: ${getErrorMessage(errorValue, '请求未成功完成')}`);
    } finally {
      setLoading(false);
    }
  };

  const restoreHistoryItem = async (item: Partial<PredictionResult>) => {
    if (!item.id) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/predictions/${item.id}`, {
        credentials: 'include',
        headers: buildAuthHeaders(),
      });

      if (!response.ok) {
        setError('无法加载详细记录');
        return;
      }

      const data = await response.json();
      const fullItem = normalizePredictionResult<PredictionResult>(
        data.data as Record<string, unknown>,
        data.data?.real_age_years as string | number | undefined,
      );
      setResult(fullItem);
      setGender(fullItem.gender);
      setRealAge(fullItem.real_age_years ? String(fullItem.real_age_years) : '');
      setCurrentHeight('');
      setFile(null);
      replacePreview(null);
      setPredictionImageSource('history');
      onHistoryRestored?.();
    } catch {
      setError('网络错误');
    }
  };

  const handleUsePreprocessedImage = ({ dataUrl, fileName }: { dataUrl: string; fileName: string }) => {
    const processedFile = dataUrlToFile(dataUrl, fileName);
    setFile(processedFile);
    replacePreview(dataUrl);
    setResult(null);
    setError(null);
    setImgSettings(DEFAULT_SETTINGS);
    setPredictionImageSource('preprocessing');
  };

  const generateComparisonData = (res: PredictionResult) => {
    if (!res.real_age_years) {
      return [];
    }

    return [
      { name: '实际年龄', age: res.real_age_years, fill: '#94a3b8' },
      {
        name: '预测骨龄',
        age: res.predicted_age_years,
        fill: getEvaluation(res.predicted_age_years, res.real_age_years).color,
      },
    ];
  };

  const imageStyle: CSSProperties = {
    filter: `brightness(${imgSettings.brightness}%) contrast(${imgSettings.contrast}) ${imgSettings.invert ? 'invert(1)' : ''}`,
    transform: `scale(${imgSettings.scale / 100})`,
    transition: 'filter 0.2s ease, transform 0.2s ease',
    maxWidth: '100%',
    borderRadius: '8px',
  };

  const preprocessingSeedImage = preview
    ? {
        src: preview,
        fileName: file?.name || result?.filename || 'bone-age-image.png',
      }
    : null;

  return {
    file,
    preview,
    gender,
    realAge,
    currentHeight,
    loading,
    result,
    error,
    imgSettings,
    imageStyle,
    predictionImageSource,
    fileInputRef,
    preprocessingSeedImage,
    setGender,
    setRealAge,
    setCurrentHeight,
    setImgSettings,
    handleFileChange,
    handleDrop,
    handleSubmit,
    restoreHistoryItem,
    handleUsePreprocessedImage,
    generateComparisonData,
    getEvaluation,
    getBoxStyle,
    generateMedicalReport,
    clearTransientStatus,
  };
}
