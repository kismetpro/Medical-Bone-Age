import { useEffect, useRef, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight,
  Contrast,
  Download,
  Image as ImageIcon,
  RotateCw,
  Sliders,
  Sun,
  Upload,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useTimedMessage } from '../../hooks/useTimedMessage';
import {
  createDefaultImageProcessingSettings,
  processImageDataUrl,
  readImageFileAsDataUrl,
  type ImageProcessingSettings,
} from '../../lib/imagePreprocessing';
import styles from './ImagePreprocessingWorkspace.module.css';

export interface PreprocessingSeedImage {
  src: string;
  fileName: string;
}

interface ImagePreprocessingWorkspaceProps {
  title: string;
  uploadLabel: string;
  enhancementTitle: string;
  placeholderTitle: string;
  placeholderHint: string;
  downloadLabel: string;
  useInPredictLabel?: string;
  seedImage?: PreprocessingSeedImage | null;
  onUseInPredict?: (payload: { dataUrl: string; fileName: string }) => void;
  showEdgeEnhance?: boolean;
  showBrightnessInfo?: boolean;
}

interface InfoItem {
  icon: LucideIcon;
  label: string;
  value: string;
}

function buildProcessedFileName(fileName: string) {
  const trimmed = fileName.trim();
  if (!trimmed) {
    return 'processed-image.png';
  }

  const extensionIndex = trimmed.lastIndexOf('.');
  if (extensionIndex <= 0) {
    return `${trimmed}-processed.png`;
  }

  return `${trimmed.slice(0, extensionIndex)}-processed.png`;
}

export default function ImagePreprocessingWorkspace({
  title,
  uploadLabel,
  enhancementTitle,
  placeholderTitle,
  placeholderHint,
  downloadLabel,
  useInPredictLabel,
  seedImage,
  onUseInPredict,
  showEdgeEnhance = false,
  showBrightnessInfo = false,
}: ImagePreprocessingWorkspaceProps) {
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [fileName, setFileName] = useState('');
  const [settings, setSettings] = useState<ImageProcessingSettings>(createDefaultImageProcessingSettings);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastAppliedSeedRef = useRef<string | null>(null);
  const { message, showMessage } = useTimedMessage();

  useEffect(() => {
    const signature = seedImage ? `${seedImage.fileName}:${seedImage.src.slice(0, 32)}:${seedImage.src.length}` : null;
    if (!seedImage?.src || signature === lastAppliedSeedRef.current) {
      return;
    }

    lastAppliedSeedRef.current = signature;
    setOriginalImage(seedImage.src);
    setProcessedImage(seedImage.src);
    setFileName(seedImage.fileName);
    setSettings(createDefaultImageProcessingSettings());
  }, [seedImage]);

  useEffect(() => {
    let cancelled = false;

    if (!originalImage) {
      setProcessedImage(null);
      return undefined;
    }

    processImageDataUrl(originalImage, settings)
      .then((nextImage) => {
        if (!cancelled) {
          setProcessedImage(nextImage);
        }
      })
      .catch(() => {
        if (!cancelled) {
          showMessage('error', '图像处理失败，请重新调整参数或重新上传。');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [originalImage, settings, showMessage]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0];
    if (!nextFile) {
      return;
    }

    if (!nextFile.type.startsWith('image/')) {
      showMessage('error', '请选择有效的图像文件');
      event.target.value = '';
      return;
    }

    try {
      const nextImage = await readImageFileAsDataUrl(nextFile);
      lastAppliedSeedRef.current = null;
      setFileName(nextFile.name);
      setOriginalImage(nextImage);
      setProcessedImage(nextImage);
      setSettings(createDefaultImageProcessingSettings());
    } catch {
      showMessage('error', '读取图像失败，请重试');
    } finally {
      event.target.value = '';
    }
  };

  const handleDownload = () => {
    if (!processedImage) {
      return;
    }

    const link = document.createElement('a');
    link.href = processedImage;
    link.download = buildProcessedFileName(fileName);
    link.click();
    showMessage('success', '图像已下载');
  };

  const handleReset = () => {
    setSettings(createDefaultImageProcessingSettings());
    showMessage('success', '参数已重置');
  };

  const handleRotateLeft = () => {
    setSettings((previous) => ({
      ...previous,
      rotation: (previous.rotation - 90 + 360) % 360,
    }));
  };

  const handleRotateRight = () => {
    setSettings((previous) => ({
      ...previous,
      rotation: (previous.rotation + 90) % 360,
    }));
  };

  const handleUseInPredict = () => {
    if (!processedImage) {
      return;
    }

    if (!onUseInPredict || !useInPredictLabel) {
      showMessage('error', '当前页面未启用发送到预测功能');
      return;
    }

    onUseInPredict({
      dataUrl: processedImage,
      fileName: buildProcessedFileName(fileName),
    });
    showMessage('success', '预处理结果已发送到预测评估');
  };

  const infoItems: InfoItem[] = [
    { icon: ImageIcon, label: '文件名', value: fileName || '未上传' },
    { icon: ZoomIn, label: '缩放', value: `${settings.scale}%` },
    { icon: RotateCw, label: '旋转', value: `${settings.rotation}°` },
    { icon: Contrast, label: '灰度', value: `${settings.grayscale}%` },
  ];

  if (showBrightnessInfo) {
    infoItems.splice(3, 0, {
      icon: Sun,
      label: '亮度',
      value: `${settings.brightness}%`,
    });
  }

  return (
    <div className={styles.preprocessingContainer}>
      <div className={styles.preprocessingLayout}>
        <aside className={styles.controlPanel}>
          <div className={styles.panelHeader}>
            <Sliders size={20} />
            <h3>{title}</h3>
          </div>

          <div className={styles.section}>
            <h4>图像文件</h4>
            <div className={styles.uploadArea}>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
              <button type="button" className={styles.uploadBtn} onClick={() => fileInputRef.current?.click()}>
                <Upload size={18} />
                {uploadLabel}
              </button>
              {fileName ? <span className={styles.fileName}>{fileName}</span> : null}
            </div>
          </div>

          <div className={styles.section}>
            <h4>基本调整</h4>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <Sun size={16} />
                <span>亮度</span>
                <span className={styles.value}>{settings.brightness}%</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="200"
                value={settings.brightness}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, brightness: Number(event.target.value) }))
                }
              />
            </div>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <Contrast size={16} />
                <span>对比度</span>
                <span className={styles.value}>{settings.contrast}%</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="200"
                value={settings.contrast}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, contrast: Number(event.target.value) }))
                }
              />
            </div>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <span>饱和度</span>
                <span className={styles.value}>{settings.saturation}%</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="200"
                value={settings.saturation}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, saturation: Number(event.target.value) }))
                }
              />
            </div>
          </div>

          <div className={styles.section}>
            <h4>图像变换</h4>

            <div className={styles.rotationControls}>
              <button type="button" className={styles.rotateBtn} onClick={handleRotateLeft}>
                <RotateCw size={18} style={{ transform: 'scaleX(-1)' }} />
              </button>
              <span className={styles.rotationValue}>{settings.rotation}°</span>
              <button type="button" className={styles.rotateBtn} onClick={handleRotateRight}>
                <RotateCw size={18} />
              </button>
            </div>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <ZoomOut size={16} />
                <span>缩放</span>
                <span className={styles.value}>{settings.scale}%</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="10"
                max="200"
                value={settings.scale}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, scale: Number(event.target.value) }))
                }
              />
            </div>
          </div>

          <div className={styles.section}>
            <h4>{enhancementTitle}</h4>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <span>模糊</span>
                <span className={styles.value}>{settings.blur}px</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="20"
                value={settings.blur}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, blur: Number(event.target.value) }))
                }
              />
            </div>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <span>锐化</span>
                <span className={styles.value}>{settings.sharpen.toFixed(1)}</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="10"
                step="0.1"
                value={settings.sharpen}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, sharpen: Number(event.target.value) }))
                }
              />
            </div>

            <div className={styles.controlGroup}>
              <div className={styles.controlLabel}>
                <span>灰度</span>
                <span className={styles.value}>{settings.grayscale}%</span>
              </div>
              <input
                className={styles.slider}
                type="range"
                min="0"
                max="100"
                value={settings.grayscale}
                onChange={(event) =>
                  setSettings((previous) => ({ ...previous, grayscale: Number(event.target.value) }))
                }
              />
            </div>

            {showEdgeEnhance ? (
              <div className={styles.controlGroup}>
                <div className={styles.controlLabel}>
                  <span>边缘增强</span>
                  <span className={styles.value}>{settings.edgeEnhance.toFixed(1)}</span>
                </div>
                <input
                  className={styles.slider}
                  type="range"
                  min="0"
                  max="10"
                  step="0.1"
                  value={settings.edgeEnhance}
                  onChange={(event) =>
                    setSettings((previous) => ({ ...previous, edgeEnhance: Number(event.target.value) }))
                  }
                />
              </div>
            ) : null}

            <div className={styles.toggleGroup}>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={settings.invert}
                  onChange={(event) =>
                    setSettings((previous) => ({ ...previous, invert: event.target.checked }))
                  }
                />
                <span />
                反色
              </label>
            </div>
          </div>

          <div className={styles.actionButtons}>
            <button type="button" className={styles.resetBtn} onClick={handleReset}>
              重置设置
            </button>
            <button type="button" className={styles.downloadBtn} onClick={handleDownload} disabled={!processedImage}>
              <Download size={18} />
              {downloadLabel}
            </button>
            {useInPredictLabel ? (
              <button type="button" className={styles.applyBtn} onClick={handleUseInPredict} disabled={!processedImage}>
                <ArrowRight size={18} />
                {useInPredictLabel}
              </button>
            ) : null}
          </div>
        </aside>

        <main className={styles.previewPanel}>
          {message ? (
            <div className={`${styles.message} ${message.type === 'success' ? styles.success : styles.error}`}>
              {message.text}
            </div>
          ) : null}

          <div className={styles.previewContent}>
            {processedImage ? (
              <>
                <div className={styles.imagePreview}>
                  <img src={processedImage} alt="Processed" />
                </div>
                <div className={styles.imageInfo}>
                  {infoItems.map(({ icon: Icon, label, value }) => (
                    <div className={styles.infoItem} key={label}>
                      <Icon size={16} />
                      <span>
                        {label}: {value}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className={styles.placeholder}>
                <ImageIcon size={48} />
                <p>{placeholderTitle}</p>
                <small>{placeholderHint}</small>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
