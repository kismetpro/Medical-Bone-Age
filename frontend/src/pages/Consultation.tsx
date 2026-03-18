import React, { useState, useRef, useEffect } from 'react';
import { Bot, Sparkles, Send, MessageSquare, Flame, Lightbulb, Stethoscope } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { buildAuthHeaders } from '../lib/api';
import { API_BASE } from '../config';
import styles from './Consultation.module.css';

const ConsultationPage: React.FC = () => {
    const { role } = useAuth();
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const isDoctor = role === 'doctor' || role === 'super_admin';

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

    const handleSend = async (text?: string) => {
        const msg = (text || input).trim();
        if (!msg || loading) return;

        setLoading(true);
        setMessages(prev => [...prev, { role: 'user', text: msg }]);
        setInput('');

        try {
            const endpoint = isDoctor ? '/doctor/ai-assistant' : '/user/ai-consult';
            const resp = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                credentials: 'include',
                headers: buildAuthHeaders(true),
                body: JSON.stringify({ message: msg })
            });

            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) throw new Error(data.detail || 'AI 调用失败');
            setMessages(prev => [...prev, { role: 'assistant', text: data.reply || '抱歉，我现在无法回复，请稍后再试。' }]);
        } catch (e: any) {
            setMessages(prev => [...prev, { role: 'assistant', text: `连接超时或发生错误：${e.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.pageContainer} style={{ padding: 0, maxWidth: 'none', margin: 0 }}>
            <div className={styles.consultationCard} style={{ height: 'calc(100vh - 120px)', borderRadius: 0, border: 'none' }}>
                {/* Header Section */}
                <header className={styles.header}>
                    <div className={styles.graphicBox}>
                        <Bot size={32} />
                    </div>
                    <div className={styles.titleGroup}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h2>智能健康问诊</h2>
                            <span className={styles.aiBadge}>V2.0 AI Turbo</span>
                        </div>
                        <p>{isDoctor ? '临床决策辅助助手' : '您的私人 AI 生长发育顾问'}</p>
                    </div>
                </header>

                {/* Chat Display Area */}
                <div className={styles.chatDisplay}>
                    {messages.length === 0 && (
                        <div className={styles.welcomeSection}>
                            <div className={styles.welcomeInfo}>
                                <h3 className={styles.welcomeTitle}>您好！我是您的智能健康伙伴</h3>
                                <p className={styles.welcomeDesc}>
                                    您可以直接提问，或者尝试点击下方的预设问题：
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
                                {m.text}
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className={styles.aiRow}>
                            <div className={`${styles.bubble} ${styles.aiBubble}`}>
                                <div className={styles.typing}>
                                    <span></span><span></span><span></span>
                                    <small style={{ marginLeft: '10px', color: '#94a3b8' }}>AI 正在深度思考中...</small>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                {/* Input Controls */}
                <div className={styles.inputArea}>
                    <div className={styles.inputWrapper}>
                        <textarea
                            className={styles.textarea}
                            placeholder={isDoctor ? "描述病例细节或检索医学文献建议..." : "在此输入您关心的问题..."}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                            rows={1}
                            style={{ height: input.split('\n').length > 1 ? 'auto' : '24px' }}
                        />
                        <button 
                            className={styles.sendBtn} 
                            onClick={() => handleSend()} 
                            disabled={loading || !input.trim()}
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
