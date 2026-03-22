import React, { useState, useRef, useEffect } from 'react';
import { Download, RotateCw, ZoomIn, ZoomOut, Sun, Contrast, Sliders, Image as ImageIcon, Upload } from 'lucide-react';
import styles from './ImagePreprocessingTab.module.css';

interface ImagePreprocessingTabProps {
    username: string | null;
}

const ImagePreprocessingTab: React.FC<ImagePreprocessingTabProps> = ({ }) => {
    const [originalImage, setOriginalImage] = useState<string | null>(null);
    const [processedImage, setProcessedImage] = useState<string | null>(null);
    const [fileName, setFileName] = useState<string>('');
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    
    // 图像处理参数
    const [settings, setSettings] = useState({
        brightness: 100,        // 亮度 (0-200)
        contrast: 100,         // 对比度 (0-200)
        saturation: 100,        // 饱和度 (0-200)
        rotation: 0,            // 旋转角度 (0-360)
        scale: 100,             // 缩放 (10-200)
        blur: 0,               // 模糊 (0-20)
        sharpen: 0,            // 锐化 (0-10)
        invert: false,          // 反色
        grayscale: false        // 灰度
    });

    const fileInputRef = useRef<HTMLInputElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const showMessage = (type: 'success' | 'error', text: string) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 3000);
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            showMessage('error', '请选择有效的图像文件');
            return;
        }

        setFileName(file.name);
        const reader = new FileReader();
        reader.onload = (event) => {
            const img = new Image();
            img.onload = () => {
                setOriginalImage(event.target?.result as string);
                setProcessedImage(event.target?.result as string);
                // 重置所有设置
                setSettings({
                    brightness: 100,
                    contrast: 100,
                    saturation: 100,
                    rotation: 0,
                    scale: 100,
                    blur: 0,
                    sharpen: 0,
                    invert: false,
                    grayscale: false
                });
            };
            img.src = event.target?.result as string;
        };
        reader.readAsDataURL(file);
    };

    const processImage = () => {
        if (!originalImage || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const img = new Image();
        img.onload = () => {
            // 计算缩放后的尺寸
            const scaledWidth = Math.round(img.width * (settings.scale / 100));
            const scaledHeight = Math.round(img.height * (settings.scale / 100));

            canvas.width = scaledWidth;
            canvas.height = scaledHeight;

            // 应用旋转
            ctx.save();
            ctx.translate(canvas.width / 2, canvas.height / 2);
            ctx.rotate((settings.rotation * Math.PI) / 180);
            ctx.translate(-scaledWidth / 2, -scaledHeight / 2);

            // 应用滤镜
            ctx.filter = `
                brightness(${settings.brightness}%) 
                contrast(${settings.contrast}%) 
                saturate(${settings.saturation}%) 
                blur(${settings.blur}px)
            `;

            // 绘制图像
            ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight);
            ctx.restore();

            // 应用反色和灰度
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;

            for (let i = 0; i < data.length; i += 4) {
                let r = data[i];
                let g = data[i + 1];
                let b = data[i + 2];

                // 灰度
                if (settings.grayscale) {
                    const gray = 0.299 * r + 0.587 * g + 0.114 * b;
                    r = g = b = gray;
                }

                // 反色
                if (settings.invert) {
                    r = 255 - r;
                    g = 255 - g;
                    b = 255 - b;
                }

                data[i] = r;
                data[i + 1] = g;
                data[i + 2] = b;
            }

            ctx.putImageData(imageData, 0, 0);

            // 应用锐化
            if (settings.sharpen > 0) {
                applySharpen(ctx, canvas.width, canvas.height, settings.sharpen);
            }

            // 导出处理后的图像
            setProcessedImage(canvas.toDataURL('image/png'));
        };
        img.src = originalImage;
    };

    const applySharpen = (ctx: CanvasRenderingContext2D, width: number, height: number, amount: number) => {
        const imageData = ctx.getImageData(0, 0, width, height);
        const data = imageData.data;
        const copy = new Uint8ClampedArray(data);
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];
        const weight = 1 + amount * 4;

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let r = 0, g = 0, b = 0;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        const k = kernel[(ky + 1) * 3 + (kx + 1)];
                        r += copy[idx] * k;
                        g += copy[idx + 1] * k;
                        b += copy[idx + 2] * k;
                    }
                }

                const idx = (y * width + x) * 4;
                data[idx] = Math.min(255, Math.max(0, r / weight));
                data[idx + 1] = Math.min(255, Math.max(0, g / weight));
                data[idx + 2] = Math.min(255, Math.max(0, b / weight));
            }
        }

        ctx.putImageData(imageData, 0, 0);
    };

    const handleDownload = () => {
        if (!processedImage) return;

        const link = document.createElement('a');
        link.href = processedImage;
        link.download = `processed_${fileName}`;
        link.click();
        showMessage('success', '图像已下载');
    };

    const handleReset = () => {
        setSettings({
            brightness: 100,
            contrast: 100,
            saturation: 100,
            rotation: 0,
            scale: 100,
            blur: 0,
            sharpen: 0,
            invert: false,
            grayscale: false
        });
        if (originalImage) {
            setProcessedImage(originalImage);
        }
        showMessage('success', '设置已重置');
    };

    const handleRotateLeft = () => {
        setSettings(prev => ({ ...prev, rotation: (prev.rotation - 90 + 360) % 360 }));
    };

    const handleRotateRight = () => {
        setSettings(prev => ({ ...prev, rotation: (prev.rotation + 90) % 360 }));
    };

    // 当设置改变时自动处理图像
    useEffect(() => {
        if (originalImage) {
            processImage();
        }
    }, [settings]);

    return (
        <div className={styles.preprocessingContainer}>
            <div className={styles.preprocessingLayout}>
                {/* 左侧控制面板 */}
                <aside className={styles.controlPanel}>
                    <div className={styles.panelHeader}>
                        <Sliders size={20} />
                        <h3>图像预处理</h3>
                    </div>

                    {/* 文件上传 */}
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
                                选择图像
                            </button>
                            {fileName && <span className={styles.fileName}>{fileName}</span>}
                        </div>
                    </div>

                    {/* 基本调整 */}
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
                                onChange={(e) => setSettings(prev => ({ ...prev, brightness: Number(e.target.value) }))}
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
                                onChange={(e) => setSettings(prev => ({ ...prev, contrast: Number(e.target.value) }))}
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
                                onChange={(e) => setSettings(prev => ({ ...prev, saturation: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>
                    </div>

                    {/* 变换 */}
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
                                onChange={(e) => setSettings(prev => ({ ...prev, scale: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>
                    </div>

                    {/* 高级效果 */}
                    <div className={styles.section}>
                        <h4>高级效果</h4>
                        
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
                                onChange={(e) => setSettings(prev => ({ ...prev, blur: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.controlGroup}>
                            <div className={styles.controlLabel}>
                                <span>锐化</span>
                                <span className={styles.value}>{settings.sharpen}</span>
                            </div>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                value={settings.sharpen}
                                onChange={(e) => setSettings(prev => ({ ...prev, sharpen: Number(e.target.value) }))}
                                className={styles.slider}
                            />
                        </div>

                        <div className={styles.toggleGroup}>
                            <label className={styles.toggle}>
                                <input
                                    type="checkbox"
                                    checked={settings.invert}
                                    onChange={(e) => setSettings(prev => ({ ...prev, invert: e.target.checked }))}
                                />
                                <span></span>
                                反色
                            </label>
                            <label className={styles.toggle}>
                                <input
                                    type="checkbox"
                                    checked={settings.grayscale}
                                    onChange={(e) => setSettings(prev => ({ ...prev, grayscale: e.target.checked }))}
                                />
                                <span></span>
                                灰度
                            </label>
                        </div>
                    </div>

                    {/* 操作按钮 */}
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
                            下载图像
                        </button>
                    </div>
                </aside>

                {/* 右侧预览区域 */}
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
                                </div>
                            </>
                        ) : (
                            <div className={styles.placeholder}>
                                <ImageIcon size={48} />
                                <p>请上传图像开始处理</p>
                                <small>支持 JPG、PNG、GIF 等常见图像格式</small>
                            </div>
                        )}
                    </div>

                    {/* 隐藏的Canvas用于图像处理 */}
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                </main>
            </div>
        </div>
    );
};

export default ImagePreprocessingTab;