import React from 'react';
import { RefreshCw } from 'lucide-react';
import styles from '../DoctorDashboard.module.css';
import type { QaItem } from '../types';

interface QaTabProps {
    qaList: QaItem[];
    qaLoading: boolean;
    fetchDoctorQaList: () => void;
    expandedQid: number | null;
    setExpandedQid: (qid: number | null) => void;
    replyTexts: Record<number, string>;
    setReplyTexts: React.Dispatch<React.SetStateAction<Record<number, string>>>;
    replyToQuestion: (qid: number) => void;
    replySubmitting: Record<number, boolean>;
}

const QaTab: React.FC<QaTabProps> = ({
    qaList, qaLoading, fetchDoctorQaList, expandedQid, setExpandedQid,
    replyTexts, setReplyTexts, replyToQuestion, replySubmitting
}) => {
    return (
        <div style={{ padding: '0 0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>患者问答</h3>
                <button className={styles.refreshBtn} onClick={() => void fetchDoctorQaList()} disabled={qaLoading}>
                    <RefreshCw size={16} className={qaLoading ? 'spin' : ''} />刷新列表
                </button>
            </div>
            {qaList.length === 0 && !qaLoading && <p style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem 0' }}>暂无患者提问。</p>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {qaList.map((question) => (
                    <div key={question.qid} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', background: 'white', overflow: 'hidden' }}>
                        <div 
                            style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer', background: expandedQid === question.qid ? '#f0f7ff' : 'white' }} 
                            onClick={() => setExpandedQid(expandedQid === question.qid ? null : question.qid)}
                        >
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.25rem' }}>患者：<strong>{question.owner}</strong> · {new Date(question.createTime).toLocaleString()}</div>
                                <div style={{ fontSize: '0.92rem', color: '#1e293b', lineHeight: 1.4 }}>{question.text}</div>
                            </div>
                            <span className={question.reply ? styles.successPill : styles.pendingPill}>{question.reply ? '已回复' : '待回复'}</span>
                        </div>
                        {expandedQid === question.qid && (
                            <div style={{ borderTop: '1px solid #e2e8f0', padding: '1rem' }}>
                                {question.image && <img src={question.image} alt="患者附图" style={{ maxWidth: '280px', maxHeight: '200px', objectFit: 'contain', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '0.85rem' }} />}
                                {question.reply && <div className={styles.replyBox}><strong>已有回复：</strong>{question.reply}</div>}
                                <textarea 
                                    className={styles.textareaInput} 
                                    style={{ minHeight: '90px' }} 
                                    placeholder="请输入专业回复内容..." 
                                    value={replyTexts[question.qid] || ''} 
                                    onChange={(event) => setReplyTexts((previous) => ({ ...previous, [question.qid]: event.target.value }))} 
                                />
                                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.6rem' }}>
                                    <button 
                                        className={styles.primaryActionBtn} 
                                        onClick={() => void replyToQuestion(question.qid)} 
                                        disabled={replySubmitting[question.qid] || !replyTexts[question.qid]?.trim()}
                                    >
                                        {replySubmitting[question.qid] ? '提交中...' : question.reply ? '更新回复' : '提交回复'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default QaTab;
