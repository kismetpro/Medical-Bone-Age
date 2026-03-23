import React, { useEffect, useRef, useState } from 'react';
import {
    Contrast,
    Download,
    Image as ImageIcon,
    RotateCw,
    Sliders,
    Sun,
    Upload,
    ZoomIn,
    ZoomOut
} from 'lucide-react';
import styles from './DoctorImagePreprocessingTab.module.css';
import {
    createDefaultImageProcessingSettings,
    processImageDataUrl,
    readImageFileAsDataUrl,
    type ImageProcessingSettings
} from '../../../lib/imagePreprocessing';

interface DoctorImagePreprocessingTabProps {
    username: string | null;
}

const DoctorImagePreprocessingTab: React.FC<DoctorImagePreprocessingTabProps> = () => {
    const [originalImage, setOriginalImage] = useState<string | null>(null);
    const [processedImage, setProcessedImage] = useState<string | null>(null);
    const [fileName, setFileName] = useState<string>('');
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [settings, setSettings] = useState<ImageProcessingSettings>(createDefaultImageProcessingSettings);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const messageTimerRef = useRef<number | null>(null);

    const showMessage = (type: 'success' | 'error', text: string) => {
        if (messageTimerRef.current) {
            window.clearTimeout(messageTimerRef.current);
        }

        setMessage({ type, text });
        messageTimerRef.current = window.setTimeout(() => {
            setMessage(null);
            messageTimerRef.current = null;
        }, 3000);
    };

    useEffect(() => {
        return () => {
            if (messageTimerRef.current) {
                window.clearTimeout(messageTimerRef.current);
            }
        };
    }, []);

    useEffect(() => {
        let cancelled = false;

        if (!originalImage) {
            setProcessedImage(null);
            return;
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
    }, [originalImage, settings]);

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            showMessage('error', '请选择有效的图像文件');
            return;
        }

        try {
            const nextImage = await readImageFileAsDataUrl(file);
            setFileName(file.name);
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
        if (!processedImage) return;

        const link = document.createElement('a');
        link.href = processedImage;
        link.download = buildProcessedFileName(fileName);
        link.click();
        showMessage('success', '图像已下载');
    };

    const handleReset = () => {
        setSettings(createDefaultImageProcessingSettings());
        showMessage('success', '设置已重置');
    };

    const handleRotateLeft = () => {
        setSettings((prev) => ({ ...prev, rotation: (prev.rotation - 90 + 360) % 360 }));
    };

    const handleRotateRight = () => {
        setSettings((prev) => ({ ...prev, rotation: (prev.rotation + 90) % 360 }));
    };

    return (
        <div className={styles.preprocessingContainer}>
            <div className={styles.preprocessingLayout}>
                <aside className={styles.controlPanel}>
                    <div className={styles.panelHeader}>
                        <Sliders size={20} />
                        <h3>医学图像预处理</h3>
                    </div>

                    <div className={styles.section}>
                        <h4>图像文件</h4>
                        <div className={styles.uploadArea}>
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileUpload}
                                accept="image/*"
                                style={{ display: 'none' }}
                            />
                            <button
                                className={styles.uploadBtn}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <Upload size={18} />
                                选择医学图像
                            </button>
                            {fileName && <span className={styles.fileName}>{fileName}</span>}
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
                                type="range"
                                min="0"
                                max="200"
                                value={settings.brightness}
                                onChange={(e) => setSettings((prev) => ({ ...prev, brightness: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <Contrast size={16} />
                                <span>对比度</span>
                                <span className={styles.value}>{settings.contrast}%</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="200"
                                value={settings.contrast}
                                onChange={(e) => setSettings((prev) => ({ ...prev, contrast: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>饱和度</span>
                                <span className={styles.value}>{settings.saturation}%</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="200"
                                value={settings.saturation}
                                onChange={(e) => setSettings((prev) => ({ ...prev, saturation: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>
                    </div>

                    <div className={styles.section}>
                        <h4>图像变换</h4>

                        <div className={styles.rotationControls}>
                            <button className={styles.rotateBtn} onClick={handleRotateLeft}>
                                <RotateCw size={18} style={{ transform: 'scaleX(-1)' }} />
                            </button>
                            <span className={styles.rotationValue}>{settings.rotation}°</span>
                            <button className={styles.rotateBtn} onClick={handleRotateRight}>
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
                                type="range"
                                min="10"
                                max="200"
                                value={settings.scale}
                                onChange={(e) => setSettings((prev) => ({ ...prev, scale: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>
                    </div>

                    <div className={styles.section}>
                        <h4>医学图像增强</h4>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>模糊</span>
                                <span className={styles.value}>{settings.blur}px</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="20"
                                value={settings.blur}
                                onChange={(e) => setSettings((prev) => ({ ...prev, blur: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>锐化</span>
                                <span className={styles.value}>{settings.sharpen.toFixed(1)}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                step="0.1"
                                value={settings.sharpen}
                                onChange={(e) => setSettings((prev) => ({ ...prev, sharpen: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>灰度</span>
                                <span className={styles.value}>{settings.grayscale}%</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={settings.grayscale}
                                onChange={(e) => setSettings((prev) => ({ ...prev, grayscale: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>边缘增强</span>
                                <span className={styles.value}>{settings.edgeEnhance.toFixed(1)}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                step="0.1"
                                value={settings.edgeEnhance}
                                onChange={(e) => setSettings((prev) => ({ ...prev, edgeEnhance: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.toggleGroup}>
                            <label className={styles.toggle}>
                                <input
                                    type="checkbox"
                                    checked={settings.invert}
                                    onChange={(e) => setSettings((prev) => ({ ...prev, invert: e.target.checked }))}
                                />
                                <span></span>
                                反色
                            </label>
                        </div>
                    </div>

                    <div className={styles.actionButtons}>
                        <button className={styles.resetBtn} onClick={handleReset}>
                            重置设置
                        </button>
                        <button
                            className={styles.downloadBtn}
                            onClick={handleDownload}
                            disabled={!processedImage}
                        >
                            <Download size={18} />
                            下载处理图像
                        </button>
                    </div>
                </aside>

                <main className={styles.previewPanel}>
                    {message && (
                        <div className={`${styles.message} ${styles[message.type]}`}>
                            {message.text}
                        </div>
                    )}

                    <div className={styles.previewContent}>
                        {processedImage ? (
                            <>
                                <div className={styles.imagePreview}>
                                    <img src={processedImage} alt="Processed" />
                                </div>
                                <div className={styles.imageInfo}>
                                    <div className={styles.infoItem}>
                                        <ImageIcon size={16} />
                                        <span>文件名: {fileName}</span>
                                    </div>
                                    <div className={styles.infoItem}>
                                        <ZoomIn size={16} />
                                        <span>缩放: {settings.scale}%</span>
                                    </div>
                                    <div className={styles.infoItem}>
                                        <RotateCw size={16} />
                                        <span>旋转: {settings.rotation}°</span>
                                    </div>
                                    <div className={styles.infoItem}>
                                        <Sun size={16} />
                                        <span>亮度: {settings.brightness}%</span>
                                    </div>
                                    <div className={styles.infoItem}>
                                        <Contrast size={16} />
                                        <span>灰度: {settings.grayscale}%</span>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div className={styles.placeholder}>
                                <ImageIcon size={48} />
                                <p>请上传医学图像开始处理</p>
                                <small>支持 X 光片、CT、MRI 等医学图像格式</small>
                            </div>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
};

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

export default DoctorImagePreprocessingTab;
