import React, { useState } from 'react';
import { Bot, HelpCircle, Send } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { buildAuthHeaders } from '../lib/api';
import { API_BASE } from '../config';
import userStyles from './UserDashboard/UserDashboard.module.css';

const ConsultationPage: React.FC = () => {
    const { role } = useAuth();
    const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    // 根据角色选择逻辑
    const isDoctor = role === 'doctor' || role === 'super_admin';

    const handleSend = async () => {
        const msg = input.trim();
        if (!msg) return;

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
            setMessages(prev => [...prev, { role: 'assistant', text: data.reply || '未返回内容' }]);
        } catch (e: any) {
            setMessages(prev => [...prev, { role: 'assistant', text: `调用失败：${e.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div className={userStyles.communityPanel}>
                <div className={userStyles.communityPanelHeader}>
                    <Bot size={20} color="#3b82f6" />
                    <h3 style={{ margin: '0 0 0 0.5rem' }}>智能健康问诊</h3>
                    <span className={userStyles.aiTag}>AI 驱动</span>
                </div>
                <p className={userStyles.communityDesc}>
                    {isDoctor 
                        ? '作为临床助手，AI 可以辅助您分析病例、提供阅片建议或后续检查参考。' 
                        : '向 AI 健康顾问咨询骨龄发育、生长规律等问题。AI 提供科普参考，不替代医生诊断。'}
                </p>
                
                <div className={userStyles.chatWindow} style={{ minHeight: '450px', maxHeight: '600px' }}>
                    {messages.length === 0 && (
                        <div className={userStyles.chatEmpty}>
                            <HelpCircle size={48} color="#cbd5e1" />
                            <p>输入您的问题，AI 将为您解答相关医学健康知识。</p>
                        </div>
                    )}
                    {messages.map((m, idx) => (
                        <div key={idx} className={`${userStyles.chatMsg} ${m.role === 'user' ? userStyles.chatMsgUser : userStyles.chatMsgAi}`}>
                            <div className={userStyles.chatMsgRole}>{m.role === 'user' ? '您' : (isDoctor ? 'AI 助手' : 'AI 顾问')}</div>
                            <div className={userStyles.chatMsgText}>{m.text}</div>
                        </div>
                    ))}
                </div>

                <div className={userStyles.chatInputRow}>
                    <textarea
                        className={userStyles.chatTextarea}
                        placeholder={isDoctor ? "输入病例分析需求或咨询建议..." : "例如：孩子骨龄超前一岁需要担心吗？"}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                        rows={3}
                    />
                    <button className={userStyles.chatSendBtn} onClick={handleSend} disabled={loading} style={{ height: 'auto', minHeight: '42px' }}>
                        <Send size={18} />{loading ? ' 思考中...' : ' 发送咨询'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConsultationPage;
