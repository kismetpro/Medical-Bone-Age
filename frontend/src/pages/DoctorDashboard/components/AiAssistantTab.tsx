import React from 'react';
import { Send } from 'lucide-react';
import styles from '../DoctorDashboard.module.css';
import type { ChatMessage } from '../types';

interface AiAssistantTabProps {
    aiMessages: ChatMessage[];
    aiInput: string;
    setAiInput: (text: string) => void;
    askAiAssistant: () => void;
    aiLoading: boolean;
}

const AiAssistantTab: React.FC<AiAssistantTabProps> = ({
    aiMessages, aiInput, setAiInput, askAiAssistant, aiLoading
}) => {
    return (
        <div className={styles.workspaceGrid}>
            <div className={styles.tableCard} style={{ padding: '1rem' }}>
                <h3 style={{ margin: '0 0 1rem 0' }}>AI 临床助手</h3>
                <p style={{ margin: '0 0 1rem 0', color: '#64748b' }}>可输入病例分析需求、阅片疑问或后续检查建议，由 AI 提供结构化辅助意见。</p>
                <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, minHeight: 280, maxHeight: 380, overflow: 'auto', padding: '0.75rem', background: '#f8fafc' }}>
                    {aiMessages.length === 0 && <p style={{ color: '#64748b', margin: 0 }}>暂无对话，请先输入问题。</p>}
                    {aiMessages.map((message, index) => (
                        <div key={`${message.role}-${index}`} style={{ marginBottom: '0.6rem', padding: '0.6rem 0.7rem', borderRadius: 10, background: message.role === 'user' ? '#dbeafe' : 'white', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.2rem' }}>{message.role === 'user' ? '你' : 'AI 助手'}</div>
                            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{message.text}</div>
                        </div>
                    ))}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.6rem', marginTop: '0.8rem' }}>
                    <textarea 
                        className={styles.textareaInput} 
                        style={{ minHeight: 90 }} 
                        placeholder="例如：请根据当前预测结果给出鉴别诊断建议。" 
                        value={aiInput} 
                        onChange={(event) => setAiInput(event.target.value)} 
                    />
                    <button 
                        className={styles.primaryActionBtn} 
                        style={{ alignSelf: 'end', minHeight: 42 }} 
                        onClick={() => void askAiAssistant()} 
                        disabled={aiLoading}
                    >
                        <Send size={14} />{aiLoading ? '运行中...' : '发送'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AiAssistantTab;
