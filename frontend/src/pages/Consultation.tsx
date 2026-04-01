import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Bot, Sparkles, Send, MessageSquare, Flame, Lightbulb, Stethoscope, Image as ImageIcon, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { buildAuthHeaders } from '../lib/api';
import { API_BASE } from '../config';
import styles from './Consultation.module.css';

const ConsultationPage: React.FC = () => {
    const { role } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string; image?: string }>>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);
    const [selectedImagePreview, setSelectedImagePreview] = useState<string | null>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const isDoctor = role === 'doctor' || role === 'super_admin';
    const isStandaloneRoute = location.pathname === '/consultation';

    const userSuggestions = [
        { icon: <MessageSquare size={16} />, text: "什么是骨龄？它和普通年龄有什么区别？" },
        { icon: <Flame size={16} />, text: "孩子个子矮小，大概率是什么原因？" },
        { icon: <Lightbulb size={16} />, text: "想长高，除了骨龄还需要注意什么饮食？" },
        { icon: <Sparkles size={16} />, text: "帮我解读一下骨龄报告的关键参数" }
    ];

    const doctorSuggestions = [
        { icon: <Stethoscope size={16} />, text: "如何更准确地识读 RUS-CHN 法的骨化点？" },
        { icon: <Sparkles size={16} />, text: "该系统如何评估生长激素治疗的效果？" },
        { icon: <MessageSquare size={16} />, text: "生成关于骨龄落后患儿的家属沟通建议" }
    ];

    const suggestions = isDoctor ? doctorSuggestions : userSuggestions;

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('请选择图片文件');
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert('图片大小不能超过5MB');
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            const base64 = event.target?.result as string;
            setSelectedImage(base64);
            setSelectedImagePreview(base64);
        };
        reader.readAsDataURL(file);
        
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const clearSelectedImage = () => {
        setSelectedImage(null);
        setSelectedImagePreview(null);
    };

    const handleBack = () => {
        if (window.history.length > 1) {
            navigate(-1);
            return;
        }
        navigate('/');
    };

    const handleSend = async (text?: string) => {
        const msg = (text || input).trim();
        if ((!msg && !selectedImage) || loading) return;

        setLoading(true);
        
        const userMessage: { role: 'user' | 'assistant'; text: string; image?: string } = {
            role: 'user',
            text: msg || '(上传了图片)',
        };
        if (selectedImagePreview) {
            userMessage.image = selectedImagePreview;
        }
        
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        const currentImage = selectedImage;
        clearSelectedImage();

        const assistantMessageIndex = messages.length + 1;
        setMessages(prev => [...prev, { role: 'assistant', text: '' }]);

        try {
            let resp: Response;
            
            if (currentImage) {
                resp = await fetch(`${API_BASE}/user/ai-consult-image`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: buildAuthHeaders(true),
                    body: JSON.stringify({ 
                        message: msg || '', 
                        image_base64: currentImage 
                    })
                });
            } else {
                const endpoint = isDoctor ? '/doctor/ai-assistant' : '/user/ai-consult';
                resp = await fetch(`${API_BASE}${endpoint}`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: buildAuthHeaders(true),
                    body: JSON.stringify({ message: msg })
                });
            }

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                throw new Error(errorData.detail || 'AI 调用失败');
            }

            const reader = resp.body?.getReader();
            if (!reader) {
                throw new Error('无法获取响应流');
            }

            const decoder = new TextDecoder();
            let accumulatedText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        if (dataStr === '[DONE]') {
                            continue;
                        }
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.error) {
                                throw new Error(data.error);
                            }
                            if (data.content) {
                                accumulatedText += data.content;
                                setMessages(prev => {
                                    const newMessages = [...prev];
                                    newMessages[assistantMessageIndex] = {
                                        role: 'assistant',
                                        text: accumulatedText
                                    };
                                    return newMessages;
                                });
                            }
                        } catch (parseError: any) {
                            if (parseError.message && !parseError.message.includes('JSON')) {
                                throw parseError;
                            }
                        }
                    }
                }
            }

            if (!accumulatedText) {
                setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[assistantMessageIndex] = {
                        role: 'assistant',
                        text: '抱歉，我现在无法回复，请稍后再试。'
                    };
                    return newMessages;
                });
            }
        } catch (e: any) {
            setMessages(prev => {
                const newMessages = [...prev];
                newMessages[assistantMessageIndex] = {
                    role: 'assistant',
                    text: `连接超时或发生错误：${e.message}`
                };
                return newMessages;
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`${styles.pageContainer} ${isStandaloneRoute ? styles.standalonePage : styles.embeddedPage}`}>
            {isStandaloneRoute && (
                <div className={styles.pageToolbar}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={18} />
                        返回首页
                    </button>
                    {/* 去除了智能健康问诊标题长栏，仅保留返回按钮以节省空间 */}
                </div>
            )}
            <div className={`${styles.consultationCard} ${isStandaloneRoute ? styles.standaloneCard : styles.embeddedCard}`}>
                {/* 去除了内部卡片标题栏 */}

                <div className={styles.chatDisplay}>
                    {messages.length === 0 && (
                        <div className={styles.welcomeSection}>
                            <div className={styles.welcomeInfo}>
                                <h3 className={styles.welcomeTitle}>您好！我是您的智能健康伙伴</h3>
                                <p className={styles.welcomeDesc}>
                                    您可以直接提问，上传X光片图片进行分析，或者尝试点击下方的预设问题：
                                </p>
                            </div>
                            <div className={styles.suggestionGrid}>
                                {suggestions.map((s, i) => (
                                    <div key={i} className={styles.suggestionChip} onClick={() => handleSend(s.text)}>
                                        <div style={{ color: '#3b82f6' }}>{s.icon}</div>
                                        <span>{s.text}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {messages.map((m, idx) => (
                        <div key={idx} className={`${styles.messageRow} ${m.role === 'user' ? styles.userRow : styles.aiRow}`}>
                            <div className={`${styles.bubble} ${m.role === 'user' ? styles.userBubble : styles.aiBubble}`}>
                                {m.image && (
                                    <div style={{ marginBottom: '0.5rem' }}>
                                        <img 
                                            src={m.image} 
                                            alt="上传的图片" 
                                            style={{ 
                                                maxWidth: '200px', 
                                                maxHeight: '150px', 
                                                borderRadius: '8px',
                                                display: 'block'
                                            }} 
                                        />
                                    </div>
                                )}
                                <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                                {m.role === 'assistant' && idx === messages.length - 1 && loading && (
                                    <span className={styles.cursor}>▌</span>
                                )}
                            </div>
                        </div>
                    ))}

                    {loading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
                        <div className={styles.aiRow}>
                            <div className={`${styles.bubble} ${styles.aiBubble}`}>
                                <div className={styles.typing}>
                                    <span></span><span></span><span></span>
                                    <small style={{ marginLeft: '10px', color: '#94a3b8' }}>AI 正在思考中...</small>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                <div className={styles.inputArea}>
                    {selectedImagePreview && (
                        <div className={styles.imagePreviewContainer}>
                            <img src={selectedImagePreview} alt="预览" className={styles.imagePreview} />
                            <button className={styles.removeImageBtn} onClick={clearSelectedImage}>
                                <X size={14} />
                            </button>
                        </div>
                    )}
                    <div className={styles.inputWrapper}>
                        <input
                            type="file"
                            ref={fileInputRef}
                            accept="image/*"
                            onChange={handleImageSelect}
                            style={{ display: 'none' }}
                        />
                        <button 
                            className={styles.imageBtn}
                            onClick={() => fileInputRef.current?.click()}
                            title="上传图片"
                        >
                            <ImageIcon size={20} />
                        </button>
                        <textarea
                            className={styles.textarea}
                            placeholder={isDoctor ? "描述病例细节或检索医学文献建议..." : "在此输入您关心的问题，可上传X光片进行分析..."}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                            rows={1}
                            style={{ height: input.split('\n').length > 1 ? 'auto' : '24px' }}
                        />
                        <button 
                            className={styles.sendBtn} 
                            onClick={() => handleSend()} 
                            disabled={loading || (!input.trim() && !selectedImage)}
                        >
                            <Send size={20} />
                        </button>
                    </div>
                    <div style={{ marginTop: '12px', textAlign: 'center' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
                             AI 的回答仅供参考，重大医疗决定请线下咨询专科医生
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConsultationPage;
